"""Speech-to-text service using Faster-Whisper with OpenAI fallback."""

import asyncio
import io
import os
import time
import wave
from typing import Any

import numpy as np
import openai
import torch
from faster_whisper import WhisperModel
from imageio_ffmpeg import get_ffmpeg_exe

from src.constants import LATENCY_WINDOW_SIZE, ModelName, STREAMING_BATCH_SIZE
from src.exceptions import AudioProcessingError, STTError
from src.utils import get_logger, get_settings, log_error_with_context, log_performance
from src.utils.audio import audio_processor, audio_stream_processor


logger = get_logger(__name__)
settings = get_settings()
WHISPER_ERRORS = (
    STTError,
    AudioProcessingError,
    OSError,
    RuntimeError,
    ValueError,
    wave.Error,
)
OPENAI_STT_ERRORS = (STTError, AudioProcessingError, openai.OpenAIError, AttributeError)


class STTService:
    """Speech-to-text service with streaming support."""

    def __init__(self) -> None:
        self.fw_model = None
        self.openai_client = None
        self.fallback_stt_model = self._normalize_openai_stt_model(
            settings.FALLBACK_STT_MODEL
        )
        self.models_warmed_up = False
        self.performance_stats = self._new_performance_stats()
        self._ensure_ffmpeg_on_path()

    @staticmethod
    def _new_performance_stats() -> dict[str, Any]:
        """Create a fresh performance stats dictionary."""
        return {
            "total_transcriptions": 0,
            "successful_transcriptions": 0,
            "failed_transcriptions": 0,
            "avg_latency": 0.0,
            "latencies": [],
        }

    def _ensure_ffmpeg_on_path(self) -> None:
        """Expose bundled ffmpeg to libraries that shell out to ffmpeg."""
        try:
            ffmpeg_path = get_ffmpeg_exe()
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            self._prepend_path_once(ffmpeg_dir)
            logger.info("FFmpeg available at: %s", ffmpeg_path)
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning("Could not initialize ffmpeg from imageio-ffmpeg: %s", exc)

    @staticmethod
    def _prepend_path_once(directory: str) -> None:
        """Prepend a directory to PATH when it is not already present."""
        path_value = os.environ.get("PATH", "")
        if directory in path_value.split(os.pathsep):
            return
        os.environ["PATH"] = directory + os.pathsep + path_value

    async def warm_up_models(self) -> None:
        """Warm up STT models for lower first-request latency."""
        logger.info("Warming up STT models...")
        await self._load_faster_whisper_model()
        self._warm_up_openai_client()
        self.models_warmed_up = True
        logger.info("STT models warmed up successfully")

    async def _load_faster_whisper_model(self) -> None:
        """Load the local Faster-Whisper model off the event loop."""
        model_size, device, compute_type = self._whisper_runtime_config()
        try:
            self.fw_model = await asyncio.to_thread(
                WhisperModel,
                model_size,
                device=device,
                compute_type=compute_type,
            )
            logger.info(
                "Faster-Whisper model loaded (%s, %s, %s)",
                model_size,
                device,
                compute_type,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning("Failed to load Faster-Whisper model: %s", exc)

    @staticmethod
    def _whisper_runtime_config() -> tuple[str, str, str]:
        """Choose Faster-Whisper runtime settings from available hardware."""
        if torch.cuda.is_available():
            logger.info("CUDA detected; using GPU with float16 and medium model")
            return "medium", "cuda", "float16"
        logger.info("No GPU detected; using CPU with int8 and small model")
        return "small", "cpu", "int8"

    def _warm_up_openai_client(self) -> None:
        """Initialise the OpenAI fallback client."""
        if not settings.OPENAI_API_KEY:
            return
        try:
            self.openai_client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.STT_TIMEOUT,
            )
            logger.info("OpenAI client initialized")
        except (openai.OpenAIError, TypeError, ValueError) as exc:
            logger.warning("Failed to initialize OpenAI client: %s", exc)

    async def _transcribe_with_whisper(self, audio_data: bytes) -> dict[str, Any]:
        """Transcribe audio using Faster-Whisper."""
        start_time = time.time()
        try:
            if not self.fw_model:
                raise STTError("Faster-Whisper model not loaded")
            processed_audio = await self._processed_wav(audio_data)
            waveform = self._decode_wav_pcm16(processed_audio)
            segments, info = self.fw_model.transcribe(waveform, beam_size=5)
            return self._whisper_result(segments, info, start_time)
        except WHISPER_ERRORS as exc:
            self._raise_stt_error("_transcribe_with_whisper", start_time, exc)

    async def _processed_wav(self, audio_data: bytes) -> bytes:
        """Convert incoming audio to standard mono 16 kHz WAV."""
        return await audio_processor.process_audio_for_stt(audio_data, "wav")

    @staticmethod
    def _decode_wav_pcm16(processed_audio: bytes) -> np.ndarray:
        """Decode mono or stereo 16-bit WAV into float32 samples."""
        with wave.open(io.BytesIO(processed_audio), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frames = wav_file.readframes(wav_file.getnframes())
        if sample_width != 2:
            raise ValueError(f"Expected 16-bit WAV, got {sample_width * 8}-bit")
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        return samples.reshape(-1, channels).mean(axis=1) if channels > 1 else samples

    def _whisper_result(
        self, segments: Any, info: Any, start_time: float
    ) -> dict[str, Any]:
        """Build a public result payload from Faster-Whisper output."""
        latency = time.time() - start_time
        text = " ".join(segment.text for segment in segments).strip()
        detected_lang = info.language or "en"
        lang_prob = info.language_probability or 0.0
        logger.debug(
            "Faster-Whisper transcription completed in %.3fs (lang=%s, prob=%.2f)",
            latency,
            detected_lang,
            lang_prob,
        )
        return self._transcription_payload(
            text, ModelName.FASTER_WHISPER_SMALL, detected_lang, lang_prob, latency
        )

    async def _transcribe_with_openai(self, audio_data: bytes) -> dict[str, Any]:
        """Transcribe audio using OpenAI Whisper."""
        start_time = time.time()
        try:
            if not self.openai_client:
                raise STTError("OpenAI client not initialized")
            response = await self._create_openai_transcription(audio_data)
            text = (response.text or "").strip()
            return self._openai_result(text, start_time)
        except OPENAI_STT_ERRORS as exc:
            self._raise_stt_error("_transcribe_with_openai", start_time, exc)

    async def _create_openai_transcription(self, audio_data: bytes) -> Any:
        """Call the OpenAI audio transcription API."""
        file_obj = io.BytesIO(await self._processed_wav(audio_data))
        file_obj.name = "audio.wav"
        return await self.openai_client.audio.transcriptions.create(
            model=self.fallback_stt_model,
            file=file_obj,
            response_format="json",
            timeout=settings.STT_TIMEOUT,
        )

    def _openai_result(self, text: str, start_time: float) -> dict[str, Any]:
        """Build a public result payload from OpenAI output."""
        latency = time.time() - start_time
        logger.debug("OpenAI transcription completed in %.3fs", latency)
        return self._transcription_payload(
            text, ModelName.OPENAI_WHISPER, "en", 0.0, latency
        )

    @staticmethod
    def _transcription_payload(
        text: str,
        model: ModelName,
        detected_language: str,
        language_probability: float,
        latency: float,
    ) -> dict[str, Any]:
        """Build a transcription result payload."""
        return {
            "text": text,
            "model": model,
            "detected_language": detected_language,
            "language_probability": language_probability,
            "latency": latency,
            "confidence": 1.0,
        }

    @staticmethod
    def _normalize_openai_stt_model(model: str) -> str:
        """Accept provider-qualified env values like openai/whisper-1."""
        openai_prefix = "openai/"
        return model[len(openai_prefix) :] if model.startswith(openai_prefix) else model

    @log_performance
    async def transcribe_audio(
        self, audio_data: bytes, *, use_fallback: bool = False
    ) -> dict[str, Any]:
        """Transcribe audio using the primary or fallback STT service."""
        start_time = time.time()
        self.performance_stats["total_transcriptions"] += 1
        if not use_fallback:
            result = await self._try_primary_stt(audio_data)
            if "error" not in result:
                return result
        if self.openai_client:
            return await self._try_fallback_stt(audio_data, start_time)
        self._update_stats(time.time() - start_time, success=False)
        return {"error": "No STT services available"}

    async def _try_primary_stt(self, audio_data: bytes) -> dict[str, Any]:
        """Try Faster-Whisper and return an error marker on failure."""
        try:
            result = await self._transcribe_with_whisper(audio_data)
            self._update_stats(result["latency"], success=True)
            return result
        except STTError as exc:
            logger.warning("Primary STT failed, trying fallback: %s", exc)
            return {"error": str(exc)}

    async def _try_fallback_stt(
        self, audio_data: bytes, start_time: float
    ) -> dict[str, Any]:
        """Try OpenAI Whisper and convert failure into an error payload."""
        try:
            result = await self._transcribe_with_openai(audio_data)
            self._update_stats(result["latency"], success=True)
            return result
        except STTError as exc:
            self._update_stats(time.time() - start_time, success=False)
            logger.error("Fallback STT failed: %s", exc)
            return {"error": f"STT failed: {exc}"}

    async def transcribe_chunked_audio(self, audio_chunks: list[bytes]) -> str:
        """Transcribe audio from multiple chunks for streaming support."""
        if not audio_chunks:
            return ""
        try:
            final_audio = self._combine_chunks(audio_chunks)
            result = await self.transcribe_audio(final_audio)
            return self._text_or_empty(result, "Chunked transcription failed")
        except (RuntimeError, ValueError) as exc:
            log_error_with_context(logger, exc, {"method": "transcribe_chunked_audio"})
            return ""

    @staticmethod
    def _combine_chunks(audio_chunks: list[bytes]) -> bytes:
        """Optimise and combine chunk bytes."""
        if len(audio_chunks) == 1:
            return audio_chunks[0]
        optimized_chunks = []
        for chunk in audio_chunks:
            chunk_generator = audio_stream_processor.create_audio_chunks(
                chunk, chunk_size=1024
            )
            optimized_chunks.append(b"".join(chunk_generator))
        return b"".join(optimized_chunks)

    @staticmethod
    def _text_or_empty(result: dict[str, Any], error_message: str) -> str:
        """Return text from a result payload or log and return empty text."""
        if "error" in result:
            logger.error("%s: %s", error_message, result["error"])
            return ""
        transcription = result["text"]
        logger.debug("Chunked transcription completed: '%s...'", transcription[:50])
        return transcription

    async def transcribe_streaming_audio(
        self, audio_stream: asyncio.StreamReader
    ) -> str:
        """Transcribe a real-time audio stream."""
        try:
            audio_chunks = await self._streaming_batch(audio_stream)
            return await self.transcribe_chunked_audio(audio_chunks)
        except (RuntimeError, ValueError) as exc:
            log_error_with_context(
                logger, exc, {"method": "transcribe_streaming_audio"}
            )
            return ""

    @staticmethod
    async def _streaming_batch(audio_stream: asyncio.StreamReader) -> list[bytes]:
        """Collect one streaming STT batch."""
        audio_chunks = []
        async for chunk in audio_stream_processor.process_audio_stream(audio_stream):
            audio_chunks.append(chunk)
            if len(audio_chunks) >= STREAMING_BATCH_SIZE:
                break
        return audio_chunks

    def _raise_stt_error(self, method: str, start_time: float, exc: Exception) -> None:
        """Log and re-raise a domain STT error with context."""
        log_error_with_context(
            logger,
            exc,
            {"method": method, "latency": time.time() - start_time},
        )
        raise STTError(f"{method} failed") from exc

    def _update_stats(self, latency: float, *, success: bool) -> None:
        """Update performance statistics."""
        self.performance_stats["latencies"].append(latency)
        key = "successful_transcriptions" if success else "failed_transcriptions"
        self.performance_stats[key] += 1
        self._trim_latency_window()
        self._refresh_average_latency()

    def _trim_latency_window(self) -> None:
        """Keep only the recent latency window."""
        if len(self.performance_stats["latencies"]) <= LATENCY_WINDOW_SIZE:
            return
        self.performance_stats["latencies"] = self.performance_stats["latencies"][
            -LATENCY_WINDOW_SIZE:
        ]

    def _refresh_average_latency(self) -> None:
        """Refresh the rolling average latency."""
        latencies = self.performance_stats["latencies"]
        if latencies:
            self.performance_stats["avg_latency"] = sum(latencies) / len(latencies)

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        return {
            "total_transcriptions": self.performance_stats["total_transcriptions"],
            "successful_transcriptions": self.performance_stats[
                "successful_transcriptions"
            ],
            "failed_transcriptions": self.performance_stats["failed_transcriptions"],
            "avg_latency": self.performance_stats["avg_latency"],
            "models_warmed_up": self.models_warmed_up,
            "primary_model": self._primary_model_name(),
            "fallback_model": self._fallback_model_name(),
        }

    def _primary_model_name(self) -> ModelName:
        """Return the active primary model identifier."""
        return ModelName.FASTER_WHISPER_SMALL if self.fw_model else ModelName.NONE

    def _fallback_model_name(self) -> ModelName:
        """Return the active fallback model identifier."""
        return ModelName.OPENAI_WHISPER if self.openai_client else ModelName.NONE


stt_service = STTService()
