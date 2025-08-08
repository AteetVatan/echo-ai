"""
Unit tests for STT (Speech-to-Text) service.

Tests Hugging Face Whisper and OpenAI Whisper fallback functionality,
including audio processing, transcription accuracy, and latency monitoring.
"""

import pytest
import asyncio
import io
import wave
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from src.services.stt_service import STTService
from src.utils import get_settings


@pytest.fixture
def stt_service():
    """Create STT service instance for testing."""
    return STTService()


@pytest.fixture
def sample_audio():
    """Create sample audio data for testing."""
    # Generate 1 second of test audio (sine wave)
    sample_rate = 16000
    duration = 1.0
    frequency = 440  # A4 note
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # Create WAV file in memory
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    buffer.seek(0)
    return buffer.getvalue()


class TestSTTService:
    """Test cases for STT service functionality."""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, stt_service):
        """Test STT service initialization."""
        assert stt_service.hf_api_key is not None
        assert stt_service.openai_api_key is not None
        assert stt_service.default_model is not None
        assert stt_service.fallback_model is not None
        assert stt_service.timeout > 0
    
    @pytest.mark.asyncio
    async def test_warm_up_models(self, stt_service):
        """Test model warm-up functionality."""
        with patch.object(stt_service, '_warm_up_hf_model', new_callable=AsyncMock) as mock_hf:
            with patch.object(stt_service, '_warm_up_openai_model', new_callable=AsyncMock) as mock_openai:
                await stt_service.warm_up_models()
                
                mock_hf.assert_called_once()
                mock_openai.assert_called_once()
                assert stt_service._models_warmed_up is True
    
    @pytest.mark.asyncio
    async def test_create_test_audio(self, stt_service):
        """Test test audio creation."""
        audio_data = stt_service._create_test_audio()
        
        assert isinstance(audio_data, bytes)
        assert len(audio_data) > 0
        
        # Verify it's valid WAV format
        with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
            assert wav_file.getnchannels() == 1
            assert wav_file.getsampwidth() == 2
            assert wav_file.getframerate() == 16000
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_hf_success(self, stt_service, sample_audio):
        """Test successful Hugging Face transcription."""
        mock_response = {
            "text": "Hello world",
            "confidence": 0.95,
            "language": "en"
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await stt_service.transcribe_audio(sample_audio, use_fallback=False)
            
            assert result["text"] == "Hello world"
            assert result["model"] == stt_service.default_model
            assert result["latency"] > 0
            assert result["confidence"] == 0.95
            assert result["language"] == "en"
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_openai_success(self, stt_service, sample_audio):
        """Test successful OpenAI transcription."""
        mock_response = Mock()
        mock_response.text = "Hello world"
        mock_response.confidence = 0.92
        mock_response.language = "en"
        
        with patch.object(stt_service.openai_client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await stt_service.transcribe_audio(sample_audio, use_fallback=True)
            
            assert result["text"] == "Hello world"
            assert result["model"] == stt_service.fallback_model
            assert result["latency"] > 0
            assert result["fallback_used"] is True
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_hf_failure_fallback(self, stt_service, sample_audio):
        """Test fallback to OpenAI when HF fails."""
        mock_openai_response = Mock()
        mock_openai_response.text = "Fallback response"
        
        with patch('aiohttp.ClientSession') as mock_session:
            # HF fails
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 500
            
            with patch.object(stt_service.openai_client.audio.transcriptions, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_openai_response
                
                result = await stt_service.transcribe_audio(sample_audio, use_fallback=False)
                
                assert result["text"] == "Fallback response"
                assert result["model"] == stt_service.fallback_model
                assert result["fallback_used"] is True
    
    @pytest.mark.asyncio
    async def test_transcribe_chunked_audio(self, stt_service):
        """Test chunked audio transcription."""
        # Create multiple audio chunks
        chunks = [stt_service._create_test_audio() for _ in range(3)]
        
        with patch.object(stt_service, 'transcribe_audio', new_callable=AsyncMock) as mock_transcribe:
            mock_transcribe.side_effect = [
                {"text": "Hello", "latency": 0.5},
                {"text": "world", "latency": 0.6},
                {"text": "test", "latency": 0.4}
            ]
            
            result = await stt_service.transcribe_chunked_audio(chunks)
            
            assert result == "Hello world test"
            assert mock_transcribe.call_count == 3
    
    @pytest.mark.asyncio
    async def test_transcribe_chunked_audio_with_failures(self, stt_service):
        """Test chunked audio transcription with some failures."""
        chunks = [stt_service._create_test_audio() for _ in range(3)]
        
        with patch.object(stt_service, 'transcribe_audio', new_callable=AsyncMock) as mock_transcribe:
            mock_transcribe.side_effect = [
                {"text": "Hello", "latency": 0.5},
                Exception("Transcription failed"),
                {"text": "test", "latency": 0.4}
            ]
            
            result = await stt_service.transcribe_chunked_audio(chunks)
            
            assert result == "Hello  test"  # Empty string for failed chunk
            assert mock_transcribe.call_count == 3
    
    def test_get_performance_stats(self, stt_service):
        """Test performance statistics retrieval."""
        # Add some mock latency data
        stt_service.hf_latency = [1.0, 1.5, 2.0]
        stt_service.openai_latency = [0.8, 1.2]
        stt_service.fallback_count = 2
        
        stats = stt_service.get_performance_stats()
        
        assert stats["hf_average_latency"] == 1.5
        assert stats["openai_average_latency"] == 1.0
        assert stats["fallback_count"] == 2
        assert stats["total_transcriptions"] == 5
    
    def test_get_performance_stats_empty(self, stt_service):
        """Test performance statistics with no data."""
        stats = stt_service.get_performance_stats()
        
        assert stats["hf_average_latency"] == 0
        assert stats["openai_average_latency"] == 0
        assert stats["fallback_count"] == 0
        assert stats["total_transcriptions"] == 0
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_invalid_audio(self, stt_service):
        """Test transcription with invalid audio data."""
        invalid_audio = b"not audio data"
        
        with pytest.raises(Exception):
            await stt_service.transcribe_audio(invalid_audio)
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_empty_audio(self, stt_service):
        """Test transcription with empty audio data."""
        empty_audio = b""
        
        with pytest.raises(Exception):
            await stt_service.transcribe_audio(empty_audio)


class TestSTTIntegration:
    """Integration tests for STT service."""
    
    @pytest.mark.asyncio
    async def test_full_transcription_pipeline(self, stt_service, sample_audio):
        """Test complete transcription pipeline."""
        # Mock both HF and OpenAI responses
        mock_hf_response = {
            "text": "Integration test successful",
            "confidence": 0.98,
            "language": "en"
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_hf_response)
            
            result = await stt_service.transcribe_audio(sample_audio)
            
            assert "text" in result
            assert "model" in result
            assert "latency" in result
            assert result["latency"] > 0
    
    @pytest.mark.asyncio
    async def test_latency_monitoring(self, stt_service, sample_audio):
        """Test latency monitoring functionality."""
        mock_response = {"text": "Latency test", "confidence": 0.9}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            # Perform multiple transcriptions
            for _ in range(3):
                await stt_service.transcribe_audio(sample_audio)
            
            stats = stt_service.get_performance_stats()
            
            assert len(stt_service.hf_latency) == 3
            assert stats["total_transcriptions"] == 3
            assert stats["hf_average_latency"] > 0


if __name__ == "__main__":
    pytest.main([__file__]) 