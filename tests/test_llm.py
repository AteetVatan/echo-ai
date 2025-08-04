"""
Unit tests for LLM (Language Model) service.

Tests Mistral 7B and GPT-4o-mini fallback functionality,
including response generation, conversation management, and latency monitoring.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.services.llm_service import LLMService


@pytest.fixture
def llm_service():
    """Create LLM service instance for testing."""
    return LLMService()


class TestLLMService:
    """Test cases for LLM service functionality."""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, llm_service):
        """Test LLM service initialization."""
        assert llm_service.hf_api_key is not None
        assert llm_service.openai_api_key is not None
        assert llm_service.default_model is not None
        assert llm_service.fallback_model is not None
        assert llm_service.temperature >= 0
        assert llm_service.timeout > 0
        assert len(llm_service.conversation_history) == 0
    
    @pytest.mark.asyncio
    async def test_warm_up_models(self, llm_service):
        """Test model warm-up functionality."""
        with patch.object(llm_service, '_warm_up_hf_model', new_callable=AsyncMock) as mock_hf:
            with patch.object(llm_service, '_warm_up_openai_model', new_callable=AsyncMock) as mock_openai:
                await llm_service.warm_up_models()
                
                mock_hf.assert_called_once()
                mock_openai.assert_called_once()
                assert llm_service._models_warmed_up is True
    
    def test_add_to_conversation(self, llm_service):
        """Test adding messages to conversation history."""
        llm_service.add_to_conversation("user", "Hello")
        llm_service.add_to_conversation("assistant", "Hi there!")
        
        assert len(llm_service.conversation_history) == 2
        assert llm_service.conversation_history[0]["role"] == "user"
        assert llm_service.conversation_history[0]["content"] == "Hello"
        assert llm_service.conversation_history[1]["role"] == "assistant"
        assert llm_service.conversation_history[1]["content"] == "Hi there!"
    
    def test_get_conversation_context(self, llm_service):
        """Test conversation context formatting."""
        llm_service.add_to_conversation("user", "Hello")
        llm_service.add_to_conversation("assistant", "Hi there!")
        llm_service.add_to_conversation("user", "How are you?")
        
        context = llm_service.get_conversation_context()
        
        assert "User: Hello" in context
        assert "Assistant: Hi there!" in context
        assert "User: How are you?" in context
    
    def test_get_conversation_context_empty(self, llm_service):
        """Test conversation context with no history."""
        context = llm_service.get_conversation_context()
        assert context == ""
    
    def test_conversation_history_limit(self, llm_service):
        """Test conversation history length limit."""
        # Add more messages than the limit
        for i in range(25):
            llm_service.add_to_conversation("user", f"Message {i}")
        
        # Should keep only recent messages
        assert len(llm_service.conversation_history) <= llm_service.max_history_length * 2
    
    @pytest.mark.asyncio
    async def test_generate_response_hf_success(self, llm_service):
        """Test successful Hugging Face response generation."""
        mock_response = {
            "generated_text": "User: Hello\nAssistant: Hi there! How can I help you today?"
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await llm_service.generate_response("Hello", use_fallback=False)
            
            assert result["text"] == "Hi there! How can I help you today?"
            assert result["model"] == llm_service.default_model
            assert result["latency"] > 0
            assert "tokens_used" in result
    
    @pytest.mark.asyncio
    async def test_generate_response_openai_success(self, llm_service):
        """Test successful OpenAI response generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello! I'm here to help."
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 25
        
        with patch.object(llm_service.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await llm_service.generate_response("Hello", use_fallback=True)
            
            assert result["text"] == "Hello! I'm here to help."
            assert result["model"] == llm_service.fallback_model
            assert result["latency"] > 0
            assert result["tokens_used"] == 25
            assert result["fallback_used"] is True
    
    @pytest.mark.asyncio
    async def test_generate_response_hf_failure_fallback(self, llm_service):
        """Test fallback to OpenAI when HF fails."""
        mock_openai_response = Mock()
        mock_openai_response.choices = [Mock()]
        mock_openai_response.choices[0].message.content = "Fallback response"
        mock_openai_response.usage = Mock()
        mock_openai_response.usage.total_tokens = 15
        
        with patch('aiohttp.ClientSession') as mock_session:
            # HF fails
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 500
            
            with patch.object(llm_service.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_openai_response
                
                result = await llm_service.generate_response("Hello", use_fallback=False)
                
                assert result["text"] == "Fallback response"
                assert result["model"] == llm_service.fallback_model
                assert result["fallback_used"] is True
    
    def test_clean_response(self, llm_service):
        """Test response text cleaning."""
        prompt = "User: Hello\nAssistant:"
        generated_text = "User: Hello\nAssistant: Hi there! How are you?"
        
        cleaned = llm_service._clean_response(generated_text, prompt)
        assert cleaned == "Hi there! How are you?"
    
    def test_clean_response_no_prompt(self, llm_service):
        """Test response cleaning when prompt not found."""
        prompt = "User: Hello\nAssistant:"
        generated_text = "Hi there! How are you?"
        
        cleaned = llm_service._clean_response(generated_text, prompt)
        assert cleaned == "Hi there! How are you?"
    
    def test_clean_response_remove_assistant_prefix(self, llm_service):
        """Test removing Assistant: prefix from response."""
        prompt = "User: Hello\nAssistant:"
        generated_text = "Assistant: Hi there!"
        
        cleaned = llm_service._clean_response(generated_text, prompt)
        assert cleaned == "Hi there!"
    
    def test_clean_response_length_limit(self, llm_service):
        """Test response length limiting."""
        prompt = "User: Hello\nAssistant:"
        long_text = "A" * 600  # Very long text
        
        cleaned = llm_service._clean_response(long_text, prompt)
        assert len(cleaned) <= 503  # 500 + "..."
        assert cleaned.endswith("...")
    
    def test_clear_conversation(self, llm_service):
        """Test clearing conversation history."""
        llm_service.add_to_conversation("user", "Hello")
        llm_service.add_to_conversation("assistant", "Hi!")
        
        assert len(llm_service.conversation_history) == 2
        
        llm_service.clear_conversation()
        
        assert len(llm_service.conversation_history) == 0
    
    def test_get_performance_stats(self, llm_service):
        """Test performance statistics retrieval."""
        # Add some mock latency data
        llm_service.hf_latency = [1.0, 1.5, 2.0]
        llm_service.openai_latency = [0.8, 1.2]
        llm_service.fallback_count = 2
        llm_service.add_to_conversation("user", "Hello")
        llm_service.add_to_conversation("assistant", "Hi!")
        
        stats = llm_service.get_performance_stats()
        
        assert stats["hf_average_latency"] == 1.5
        assert stats["openai_average_latency"] == 1.0
        assert stats["fallback_count"] == 2
        assert stats["total_generations"] == 5
        assert stats["conversation_length"] == 2
    
    def test_get_performance_stats_empty(self, llm_service):
        """Test performance statistics with no data."""
        stats = llm_service.get_performance_stats()
        
        assert stats["hf_average_latency"] == 0
        assert stats["openai_average_latency"] == 0
        assert stats["fallback_count"] == 0
        assert stats["total_generations"] == 0
        assert stats["conversation_length"] == 0
    
    @pytest.mark.asyncio
    async def test_generate_response_empty_input(self, llm_service):
        """Test response generation with empty input."""
        with pytest.raises(Exception):
            await llm_service.generate_response("")
    
    @pytest.mark.asyncio
    async def test_generate_response_whitespace_input(self, llm_service):
        """Test response generation with whitespace-only input."""
        with pytest.raises(Exception):
            await llm_service.generate_response("   ")


class TestLLMIntegration:
    """Integration tests for LLM service."""
    
    @pytest.mark.asyncio
    async def test_full_response_generation_pipeline(self, llm_service):
        """Test complete response generation pipeline."""
        mock_response = {
            "generated_text": "User: Hello\nAssistant: Hi there! How can I help you today?"
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await llm_service.generate_response("Hello")
            
            assert "text" in result
            assert "model" in result
            assert "latency" in result
            assert result["latency"] > 0
            assert len(llm_service.conversation_history) == 2  # user + assistant
    
    @pytest.mark.asyncio
    async def test_conversation_context_integration(self, llm_service):
        """Test conversation context integration."""
        # Add conversation history
        llm_service.add_to_conversation("user", "What's your name?")
        llm_service.add_to_conversation("assistant", "I'm an AI assistant.")
        
        mock_response = {
            "generated_text": "User: What's your name?\nAssistant: I'm an AI assistant.\nUser: How are you?\nAssistant: I'm doing well, thank you for asking!"
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await llm_service.generate_response("How are you?")
            
            assert result["text"] == "I'm doing well, thank you for asking!"
            assert len(llm_service.conversation_history) == 4  # 2 previous + 2 new
    
    @pytest.mark.asyncio
    async def test_latency_monitoring_integration(self, llm_service):
        """Test latency monitoring integration."""
        mock_response = {"generated_text": "Latency test response"}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            # Perform multiple generations
            for _ in range(3):
                await llm_service.generate_response("Test message")
            
            stats = llm_service.get_performance_stats()
            
            assert len(llm_service.hf_latency) == 3
            assert stats["total_generations"] == 3
            assert stats["hf_average_latency"] > 0


class TestLLMEdgeCases:
    """Test edge cases for LLM service."""
    
    @pytest.mark.asyncio
    async def test_response_with_special_characters(self, llm_service):
        """Test response generation with special characters."""
        mock_response = {
            "generated_text": "User: Test\nAssistant: Here's a response with special chars: !@#$%^&*()"
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await llm_service.generate_response("Test")
            
            assert "special chars" in result["text"]
            assert "!@#$%^&*()" in result["text"]
    
    @pytest.mark.asyncio
    async def test_response_with_unicode(self, llm_service):
        """Test response generation with unicode characters."""
        mock_response = {
            "generated_text": "User: Test\nAssistant: Here's some unicode: 🚀🌟🎉"
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await llm_service.generate_response("Test")
            
            assert "🚀🌟🎉" in result["text"]
    
    @pytest.mark.asyncio
    async def test_conversation_history_overflow(self, llm_service):
        """Test conversation history overflow handling."""
        # Add many messages to trigger overflow
        for i in range(30):
            llm_service.add_to_conversation("user", f"Message {i}")
            llm_service.add_to_conversation("assistant", f"Response {i}")
        
        # Should not exceed limit
        assert len(llm_service.conversation_history) <= llm_service.max_history_length * 2


if __name__ == "__main__":
    pytest.main([__file__]) 