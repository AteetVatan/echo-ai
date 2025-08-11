"""
Audio processing utilities for EchoAI voice chat system (FFmpeg + NumPy, in-memory).
No MoviePy, no pydub. Works on Windows via imageio-ffmpeg's bundled ffmpeg.
"""

import io
import os
import math
import wave
import tempfile
import subprocess
from typing import List, Optional, Tuple

import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

from src.utils import get_logger, get_settings

logger = get_logger(__name__)
settings = get_settings()


class AudioProcessor:
    """
    Handles audio processing and format conversion for STT compatibility.
    Uses FFmpeg (via imageio-ffmpeg) + NumPy + wave. In-memory pipes only.
    """

    def __init__(self):
        self.target_sample_rate: int = int(getattr(settings, "SAMPLE_RATE", 16000))
        self.target_channels: int = int(getattr(settings, "CHANNELS", 1))
        self.target_format: str = getattr(settings, "AUDIO_FORMAT", "wav")
        self.ffmpeg_path: str = get_ffmpeg_exe()
        if not self.ffmpeg_path or not os.path.exists(self.ffmpeg_path):
            raise RuntimeError("FFmpeg not available via imageio-ffmpeg.")

    # ---------- Core helpers ----------

    def _ffmpeg_convert_to_wav_pcm16(
        self, audio_bytes: bytes, input_format: Optional[str] = None
    ) -> bytes:
        """
        Convert arbitrary input (webm/mp3/wav/ogg...) to WAV (PCM s16le, mono, 16kHz) in memory.
        input_format is optional; FFmpeg will usually auto-detect by probing.
        """
        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel", "error",
            "-nostdin",
            "-y",
            "-i", "pipe:0",
            "-ac", str(self.target_channels),
            "-ar", str(self.target_sample_rate),
            "-acodec", "pcm_s16le",
            "-f", "wav",
            "pipe:1",
        ]
        try:
            proc = subprocess.run(
                cmd,
                input=audio_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return proc.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e.stderr.decode(errors='ignore')}")
            raise       
      
        
    def _pcm_chunks_to_wav_once(self,pcm_chunks, rate=16000, channels=1):
        try:
            pcm = b"".join(pcm_chunks)  # join raw PCM bytes
            cmd = [
                self.ffmpeg_path,
                "-f", "s16le",
                "-ar", str(rate),
                "-ac", str(channels),
                "-i", "pipe:0",
                "-acodec", "pcm_s16le",
                "-f", "wav",
                "-loglevel", "error", "-hide_banner",
                "pipe:1",
            ]
            p = subprocess.run(cmd, input=pcm, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return p.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e.stderr.decode(errors='ignore')}")
            raise  
    
    @staticmethod
    def _read_wav_to_np(wav_bytes: bytes) -> Tuple[np.ndarray, int, int]:
        """Read WAV bytes into (int16 numpy array [samples, channels], sample_rate, channels)."""
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, "rb") as w:
            sr = w.getframerate()
            ch = w.getnchannels()
            sw = w.getsampwidth()
            if sw != 2:
                raise ValueError(f"Expected 16-bit WAV, got sample width {sw*8} bits.")
            frames = w.readframes(w.getnframes())
        arr = np.frombuffer(frames, dtype=np.int16)
        if ch > 1:
            arr = arr.reshape(-1, ch)
        else:
            arr = arr.reshape(-1, 1)
        return arr, sr, ch

    @staticmethod
    def _write_np_to_wav(arr: np.ndarray, sample_rate: int, channels: int) -> bytes:
        """Write (int16 array [samples, channels]) to WAV bytes."""
        if arr.dtype != np.int16:
            raise ValueError("Array must be int16.")
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        if arr.shape[1] != channels:
            raise ValueError(f"Channel mismatch: arr has {arr.shape[1]}, expected {channels}")
        bio = io.BytesIO()
        with wave.open(bio, "wb") as w:
            w.setnchannels(channels)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(arr.tobytes())
        return bio.getvalue()

    # ---------- Public API ----------

    async def process_audio_for_stt(self, audio_data: bytes, input_format: str = "webm") -> bytes:
        """
        Convert input audio -> mono 16k WAV PCM16, normalize gently, and add tiny tail padding.
        """
        try:
            logger.debug(f"Processing audio: format={input_format}, size={len(audio_data)} bytes")

            # 1) Convert to canonical WAV PCM16 mono 16k
            wav = self._ffmpeg_convert_to_wav_pcm16(audio_data, input_format)

            # 2) Load into NumPy
            samples, sr, ch = self._read_wav_to_np(wav)

            # 3) Tail pad ~10 ms (to avoid ASR truncation at end)
            pad_len = max(1, int(0.01 * sr))  # ~10ms
            pad = np.zeros((pad_len, ch), dtype=np.int16)
            samples = np.vstack([samples, pad])

            # 4) Gentle normalization to target RMS ~ -20 dBFS (~0.1 in float)
            samples = self._normalize_rms(samples, target_rms=0.1, max_gain=10.0)

            # 5) Back to bytes
            out_wav = self._write_np_to_wav(samples, sr, ch)
            return out_wav

        except Exception as e:
            logger.error(f"Failed to process audio: {e}")
            raise        
    
    async def process_audio_chunks_for_stt(self, audio_chunks: List[bytes], input_format: str = "webm") -> bytes:
        """
        Convert input audio -> mono 16k WAV PCM16, normalize gently, and add tiny tail padding.
        """
        try:
            wav = self._pcm_chunks_to_wav_once(audio_chunks, rate=16000, channels=1)

            # 2) Load into NumPy
            samples, sr, ch = self._read_wav_to_np(wav)

            # 3) Tail pad ~10 ms (to avoid ASR truncation at end)
            pad_len = max(1, int(0.01 * sr))  # ~10ms
            pad = np.zeros((pad_len, ch), dtype=np.int16)
            samples = np.vstack([samples, pad])

            # 4) Gentle normalization to target RMS ~ -20 dBFS (~0.1 in float)
            samples = self._normalize_rms(samples, target_rms=0.1, max_gain=10.0)

            # 5) Back to bytes
            out_wav = self._write_np_to_wav(samples, sr, ch)
            return out_wav

        except Exception as e:
            logger.error(f"Failed to process audio: {e}")
            raise

    # ---------- Processing ops (NumPy) ----------

    @staticmethod
    def _normalize_rms(arr: np.ndarray, target_rms: float = 0.1, max_gain: float = 10.0) -> np.ndarray:
        """
        Normalize int16 signal to a desired RMS (approx -20 dBFS).
        Safely clamps and limits gain to avoid noise blowup.
        """
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)

        # Convert to float in [-1, 1]
        f = arr.astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(f**2)) + 1e-12
        gain = min(target_rms / rms, max_gain)

        f *= gain
        # Prevent clipping
        f = np.clip(f, -1.0, 1.0)

        return (f * 32767.0).astype(np.int16)

    def create_audio_chunks(self, audio_data: bytes, chunk_duration_ms: int = 1000) -> List[bytes]:
        """Split WAV PCM16 bytes into fixed-duration chunks."""
        samples, sr, ch = self._read_wav_to_np(audio_data)
        samples_per_chunk = max(1, int((chunk_duration_ms / 1000.0) * sr))
        chunks: List[bytes] = []

        for start in range(0, samples.shape[0], samples_per_chunk):
            end = min(start + samples_per_chunk, samples.shape[0])
            chunk_arr = samples[start:end]
            chunk_wav = self._write_np_to_wav(chunk_arr, sr, ch)
            chunks.append(chunk_wav)

        logger.debug(f"Created {len(chunks)} audio chunks of ~{chunk_duration_ms}ms each")
        return chunks

    def combine_audio_chunks(self, audio_chunks: List[bytes]) -> bytes:
        """Concatenate WAV chunks (same format) losslessly."""
        if not audio_chunks:
            return b""
        if len(audio_chunks) == 1:
            return audio_chunks[0]

        # Read first for format
        first_arr, sr, ch = self._read_wav_to_np(audio_chunks[0])
        all_arrs = [first_arr]

        for i, chunk in enumerate(audio_chunks[1:], start=2):
            arr, sr2, ch2 = self._read_wav_to_np(chunk)
            if sr2 != sr or ch2 != ch:
                raise ValueError(f"Chunk {i} format mismatch (sr/ch).")
            all_arrs.append(arr)

        merged = np.vstack(all_arrs)
        return self._write_np_to_wav(merged, sr, ch)

    def detect_silence(
        self,
        audio_data: bytes,
        silence_threshold: float = 0.01,
        min_silence_len: float = 1.0,
    ) -> bool:
        """
        Heuristic: true if ≥80% of 100ms frames are below threshold RMS.
        """
        frames_rms = self._frame_rms(audio_data, frame_sec=0.1)
        if not frames_rms:
            return True
        silent_frames = sum(1 for r in frames_rms if r < silence_threshold)
        ratio = silent_frames / len(frames_rms)
        return ratio >= 0.8

    def trim_silence(self, audio_data: bytes, silence_threshold: float = 0.01) -> bytes:
        """Trim leading/trailing silence based on 100ms RMS threshold."""
        frames_rms = self._frame_rms(audio_data, frame_sec=0.1)
        if not frames_rms:
            return audio_data

        # find first/last non-silent frames
        start_f = 0
        for i, r in enumerate(frames_rms):
            if r >= silence_threshold:
                start_f = i
                break

        end_f = len(frames_rms)
        for i in range(len(frames_rms) - 1, -1, -1):
            if frames_rms[i] >= silence_threshold:
                end_f = i + 1
                break

        # Convert frame indices to samples
        samples, sr, ch = self._read_wav_to_np(audio_data)
        frame_len = int(sr * 0.1)
        start_samp = max(0, min(len(samples), start_f * frame_len))
        end_samp = max(start_samp, min(len(samples), end_f * frame_len))

        trimmed = samples[start_samp:end_samp]
        return self._write_np_to_wav(trimmed, sr, ch)

    def get_audio_info(self, audio_data: bytes) -> dict:
        """Return duration_ms, sample_rate, channels, and RMS."""
        samples, sr, ch = self._read_wav_to_np(audio_data)
        dur_ms = int(len(samples) / sr * 1000)
        f = samples.astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(f**2))) if f.size else 0.0
        return {
            "duration_ms": dur_ms,
            "sample_rate": int(sr),
            "channels": int(ch),
            "rms": rms,
        }

    def create_test_audio(self, duration_ms: int = 1000, frequency: int = 440) -> bytes:
        """Generate a mono sine wave test tone as WAV PCM16."""
        sr = self.target_sample_rate
        n = int(sr * (duration_ms / 1000.0))
        t = np.arange(n) / sr
        # -12 dBFS (~0.25)
        f = 0.25 * np.sin(2 * math.pi * frequency * t)
        arr = (f * 32767.0).astype(np.int16).reshape(-1, 1)
        return self._write_np_to_wav(arr, sr, 1)

    # ---------- Internals ----------

    def _frame_rms(self, audio_data: bytes, frame_sec: float = 0.1) -> List[float]:
        samples, sr, ch = self._read_wav_to_np(audio_data)
        if samples.size == 0:
            return []
        # Mixdown if needed (already mono by design, but safe)
        if ch > 1:
            samples = samples.mean(axis=1, dtype=np.float32).astype(np.int16).reshape(-1, 1)

        frame_len = max(1, int(sr * frame_sec))
        f = samples.astype(np.float32) / 32768.0
        f = f.reshape(-1)  # mono now
        rms_vals = []
        for i in range(0, len(f), frame_len):
            seg = f[i : i + frame_len]
            if seg.size == 0:
                continue
            rms_vals.append(float(np.sqrt(np.mean(seg * seg))))
        return rms_vals


# Global instance (as before)
audio_processor = AudioProcessor()
