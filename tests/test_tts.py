"""
Unit tests for TTS (Text-to-Speech) service.

Tests ElevenLabs voice cloning functionality, including streaming synthesis,
caching mechanisms, and latency monitoring.
"""

import pytest
import asyncio
import hashlib
from unittest.mock import Mock, patch, AsyncMock
from src.services.tts_service import TTSService


@pytest.fixture
def tts_service():
    """Create TTS service instance for testing."""
    return TTSService()


class TestTTSService:
    """Test cases for TTS service functionality."""
    
    def test_service_initialization(self, tts_service):
        """Test TTS service initialization."""
        assert tts_service.elevenlabs_api_key is not None
        assert tts_service.voice_id is not None
        assert tts_service.streaming is True
        assert tts_service.cache_responses is True
        assert tts_service.timeout > 0
        assert len(tts_service.response_cache) > 0  # Common phrases cache
    
    def test_get_cache_key(self, tts_service):
        """Test cache key generation."""
        text = "Hello world"
        cache_key = tts_service._get_cache_key(text)
        
        assert isinstance(cache_key, str)
        assert len(cache_key) == 32  # MD5 hash length
        assert cache_key == hashlib.md5(f"{text.lower().strip()}:{tts_service.voice_id}".encode()).hexdigest()
    
    def test_is_cached(self, tts_service):
        """Test cache checking functionality."""
        text = "Hello world"
        cache_key = tts_service._get_cache_key(text)
        
        # Initially not cached
        assert not tts_service._is_cached(text)
        
        # Add to cache
        tts_service.response_cache[cache_key] = b"fake_audio_data"
        
        # Now should be cached
        assert tts_service._is_cached(text)
    
    def test_get_cached_audio(self, tts_service):
        """Test retrieving cached audio."""
        text = "Hello world"
        fake_audio = b"fake_audio_data"
        
        # Add to cache
        cache_key = tts_service._get_cache_key(text)
        tts_service.response_cache[cache_key] = fake_audio
        
        # Retrieve cached audio
        cached_audio = tts_service._get_cached_audio(text)
        assert cached_audio == fake_audio
    
    def test_get_cached_audio_not_found(self, tts_service):
        """Test retrieving non-cached audio."""
        text = "Not cached text"
        cached_audio = tts_service._get_cached_audio(text)
        assert cached_audio is None
    
    def test_cache_audio(self, tts_service):
        """Test caching audio data."""
        text = "Hello world"
        audio_data = b"test_audio_data"
        
        initial_cache_size = len(tts_service.response_cache)
        tts_service._cache_audio(text, audio_data)
        
        # Should be cached
        assert tts_service._is_cached(text)
        assert tts_service._get_cached_audio(text) == audio_data
        
        # Cache size should increase
        assert len(tts_service.response_cache) == initial_cache_size + 1
    
    def test_cache_size_limit(self, tts_service):
        """Test cache size limit enforcement."""
        # Fill cache beyond limit
        for i in range(tts_service.max_cache_size + 5):
            tts_service._cache_audio(f"text_{i}", f"audio_{i}".encode())
        
        # Should not exceed max size
        assert len(tts_service.response_cache) <= tts_service.max_cache_size
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_cached(self, tts_service):
        """Test speech synthesis with cached response."""
        text = "Hello world"
        fake_audio = b"cached_audio_data"
        
        # Add to cache
        cache_key = tts_service._get_cache_key(text)
        tts_service.response_cache[cache_key] = fake_audio
        
        result = await tts_service.synthesize_speech(text)
        
        assert result["audio_data"] == fake_audio
        assert result["model"] == "elevenlabs_cached"
        assert result["cached"] is True
        assert result["latency"] > 0
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_streaming(self, tts_service):
        """Test streaming speech synthesis."""
        text = "Hello world"
        fake_audio = b"streamed_audio_data"
        
        with patch.object(tts_service, '_synthesize_streaming', new_callable=AsyncMock) as mock_streaming:
            mock_streaming.return_value = fake_audio
            
            result = await tts_service.synthesize_speech(text, use_streaming=True)
            
            assert result["audio_data"] == fake_audio
            assert result["model"] == "elevenlabs"
            assert result["cached"] is False
            assert result["latency"] > 0
            mock_streaming.assert_called_once_with(text)
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_non_streaming(self, tts_service):
        """Test non-streaming speech synthesis."""
        text = "Hello world"
        fake_audio = b"non_streamed_audio_data"
        
        with patch.object(tts_service, '_synthesize_non_streaming', new_callable=AsyncMock) as mock_non_streaming:
            mock_non_streaming.return_value = fake_audio
            
            result = await tts_service.synthesize_speech(text, use_streaming=False)
            
            assert result["audio_data"] == fake_audio
            assert result["model"] == "elevenlabs"
            assert result["cached"] is False
            assert result["latency"] > 0
            mock_non_streaming.assert_called_once_with(text)
    
    @pytest.mark.asyncio
    async def test_synthesize_streaming_success(self, tts_service):
        """Test successful streaming synthesis."""
        text = "Hello world"
        fake_audio = b"streamed_audio"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.read = AsyncMock(return_value=fake_audio)
            
            result = await tts_service._synthesize_streaming(text)
            
            assert result == fake_audio
    
    @pytest.mark.asyncio
    async def test_synthesize_non_streaming_success(self, tts_service):
        """Test successful non-streaming synthesis."""
        text = "Hello world"
        fake_audio = b"non_streamed_audio"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.read = AsyncMock(return_value=fake_audio)
            
            result = await tts_service._synthesize_non_streaming(text)
            
            assert result == fake_audio
    
    @pytest.mark.asyncio
    async def test_synthesize_streaming_failure(self, tts_service):
        """Test streaming synthesis failure."""
        text = "Hello world"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 500
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.text = AsyncMock(return_value="API Error")
            
            with pytest.raises(Exception, match="ElevenLabs API error 500"):
                await tts_service._synthesize_streaming(text)
    
    @pytest.mark.asyncio
    async def test_synthesize_non_streaming_failure(self, tts_service):
        """Test non-streaming synthesis failure."""
        text = "Hello world"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 500
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.text = AsyncMock(return_value="API Error")
            
            with pytest.raises(Exception, match="ElevenLabs API error 500"):
                await tts_service._synthesize_non_streaming(text)
    
    @pytest.mark.asyncio
    async def test_synthesize_streaming_chunks(self, tts_service):
        """Test streaming synthesis in chunks."""
        text = "Hello world. This is a test. How are you?"
        
        with patch.object(tts_service, '_synthesize_streaming', new_callable=AsyncMock) as mock_streaming:
            mock_streaming.side_effect = [b"chunk1", b"chunk2", b"chunk3"]
            
            chunks = []
            async for chunk in tts_service.synthesize_streaming_chunks(text):
                chunks.append(chunk)
            
            assert len(chunks) == 3
            assert chunks == [b"chunk1", b"chunk2", b"chunk3"]
            assert mock_streaming.call_count == 3
    
    def test_split_into_sentences(self, tts_service):
        """Test sentence splitting functionality."""
        text = "Hello world. This is a test! How are you? I'm doing well."
        sentences = tts_service._split_into_sentences(text)
        
        expected = ["Hello world", "This is a test", "How are you", "I'm doing well"]
        assert sentences == expected
    
    def test_split_into_sentences_empty(self, tts_service):
        """Test sentence splitting with empty text."""
        text = ""
        sentences = tts_service._split_into_sentences(text)
        assert sentences == []
    
    def test_split_into_sentences_no_punctuation(self, tts_service):
        """Test sentence splitting with no punctuation."""
        text = "Hello world this is a test"
        sentences = tts_service._split_into_sentences(text)
        assert sentences == ["Hello world this is a test"]
    
    def test_warm_up_cache(self, tts_service):
        """Test cache warm-up functionality."""
        with patch.object(tts_service, 'synthesize_speech', new_callable=AsyncMock) as mock_synthesize:
            tts_service.warm_up_cache()
            
            # Should be called for each common phrase
            assert mock_synthesize.call_count == 8  # Number of common phrases
    
    def test_get_performance_stats(self, tts_service):
        """Test performance statistics retrieval."""
        # Add some mock latency data
        tts_service.latency = [1.0, 1.5, 2.0]
        tts_service.cache_hits = 5
        tts_service.cache_misses = 3
        
        stats = tts_service.get_performance_stats()
        
        assert stats["average_latency"] == 1.5
        assert stats["cache_hits"] == 5
        assert stats["cache_misses"] == 3
        assert stats["cache_hit_rate"] == 5 / 8
        assert stats["total_synthesis"] == 3
        assert stats["cache_size"] > 0
    
    def test_get_performance_stats_empty(self, tts_service):
        """Test performance statistics with no data."""
        stats = tts_service.get_performance_stats()
        
        assert stats["average_latency"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["cache_hit_rate"] == 0
        assert stats["total_synthesis"] == 0
        assert stats["cache_size"] > 0  # Common phrases cache
    
    def test_clear_cache(self, tts_service):
        """Test cache clearing functionality."""
        # Add some test data
        tts_service._cache_audio("test1", b"audio1")
        tts_service._cache_audio("test2", b"audio2")
        tts_service.cache_hits = 5
        tts_service.cache_misses = 3
        
        initial_cache_size = len(tts_service.response_cache)
        assert initial_cache_size > 0
        
        tts_service.clear_cache()
        
        # Should clear custom cache but keep common phrases
        assert len(tts_service.response_cache) > 0  # Common phrases remain
        assert tts_service.cache_hits == 0
        assert tts_service.cache_misses == 0
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_empty_text(self, tts_service):
        """Test speech synthesis with empty text."""
        with pytest.raises(Exception):
            await tts_service.synthesize_speech("")
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_whitespace_text(self, tts_service):
        """Test speech synthesis with whitespace-only text."""
        with pytest.raises(Exception):
            await tts_service.synthesize_speech("   ")


class TestTTSIntegration:
    """Integration tests for TTS service."""
    
    @pytest.mark.asyncio
    async def test_full_synthesis_pipeline(self, tts_service):
        """Test complete synthesis pipeline."""
        text = "Hello world"
        fake_audio = b"synthesized_audio_data"
        
        with patch.object(tts_service, '_synthesize_streaming', new_callable=AsyncMock) as mock_streaming:
            mock_streaming.return_value = fake_audio
            
            result = await tts_service.synthesize_speech(text)
            
            assert "audio_data" in result
            assert "model" in result
            assert "latency" in result
            assert result["latency"] > 0
            assert result["audio_data"] == fake_audio
    
    @pytest.mark.asyncio
    async def test_caching_integration(self, tts_service):
        """Test caching integration."""
        text = "Cached test message"
        fake_audio = b"cached_audio_data"
        
        with patch.object(tts_service, '_synthesize_streaming', new_callable=AsyncMock) as mock_streaming:
            mock_streaming.return_value = fake_audio
            
            # First call - should synthesize and cache
            result1 = await tts_service.synthesize_speech(text)
            assert result1["cached"] is False
            assert result1["audio_data"] == fake_audio
            
            # Second call - should use cache
            result2 = await tts_service.synthesize_speech(text)
            assert result2["cached"] is True
            assert result2["audio_data"] == fake_audio
            assert result2["model"] == "elevenlabs_cached"
    
    @pytest.mark.asyncio
    async def test_latency_monitoring_integration(self, tts_service):
        """Test latency monitoring integration."""
        text = "Latency test message"
        fake_audio = b"test_audio"
        
        with patch.object(tts_service, '_synthesize_streaming', new_callable=AsyncMock) as mock_streaming:
            mock_streaming.return_value = fake_audio
            
            # Perform multiple syntheses
            for _ in range(3):
                await tts_service.synthesize_speech(text)
            
            stats = tts_service.get_performance_stats()
            
            assert len(tts_service.latency) == 3
            assert stats["total_synthesis"] == 3
            assert stats["average_latency"] > 0


class TestTTSEdgeCases:
    """Test edge cases for TTS service."""
    
    @pytest.mark.asyncio
    async def test_synthesis_with_special_characters(self, tts_service):
        """Test synthesis with special characters."""
        text = "Hello! How are you? I'm doing well. This is a test with special chars: @#$%^&*()"
        fake_audio = b"special_chars_audio"
        
        with patch.object(tts_service, '_synthesize_streaming', new_callable=AsyncMock) as mock_streaming:
            mock_streaming.return_value = fake_audio
            
            result = await tts_service.synthesize_speech(text)
            
            assert result["audio_data"] == fake_audio
            assert result["latency"] > 0
    
    @pytest.mark.asyncio
    async def test_synthesis_with_unicode(self, tts_service):
        """Test synthesis with unicode characters."""
        text = "Hello! 🚀🌟🎉 How are you? I'm doing well! 😊"
        fake_audio = b"unicode_audio"
        
        with patch.object(tts_service, '_synthesize_streaming', new_callable=AsyncMock) as mock_streaming:
            mock_streaming.return_value = fake_audio
            
            result = await tts_service.synthesize_speech(text)
            
            assert result["audio_data"] == fake_audio
            assert result["latency"] > 0
    
    @pytest.mark.asyncio
    async def test_synthesis_with_very_long_text(self, tts_service):
        """Test synthesis with very long text."""
        text = "A" * 1000  # Very long text
        fake_audio = b"long_text_audio"
        
        with patch.object(tts_service, '_synthesize_streaming', new_callable=AsyncMock) as mock_streaming:
            mock_streaming.return_value = fake_audio
            
            result = await tts_service.synthesize_speech(text)
            
            assert result["audio_data"] == fake_audio
            assert result["latency"] > 0
    
    @pytest.mark.asyncio
    async def test_streaming_chunks_with_empty_sentences(self, tts_service):
        """Test streaming chunks with empty sentences."""
        text = "Hello world. . . This is a test. . . How are you?"
        
        with patch.object(tts_service, '_synthesize_streaming', new_callable=AsyncMock) as mock_streaming:
            mock_streaming.side_effect = [b"chunk1", b"chunk2"]
            
            chunks = []
            async for chunk in tts_service.synthesize_streaming_chunks(text):
                chunks.append(chunk)
            
            # Should only process non-empty sentences
            assert len(chunks) == 2
            assert mock_streaming.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__]) 