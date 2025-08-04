"""
Language Model (LLM) service for EchoAI voice chat system.

This module provides LLM functionality using Mistral 7B (Hugging Face) as the primary
service with OpenAI GPT-4o-mini as a fallback for reliability and deterministic responses.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
import aiohttp
import openai
from src.utils.config import get_settings
from src.utils.logging import get_logger, log_performance, log_error_with_context


logger = get_logger(__name__)
settings = get_settings()


class LLMService:
    """Handles Language Model interactions with fallback mechanisms."""
    
    def __init__(self):
        self.hf_api_key = settings.huggingface_api_key
        self.openai_api_key = settings.openai_api_key
        self.default_model = settings.default_llm_model
        self.fallback_model = settings.fallback_llm_model
        self.temperature = settings.llm_temperature
        self.timeout = settings.llm_timeout
        
        # Initialize OpenAI client
        self.openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        # Performance monitoring
        self.hf_latency = []
        self.openai_latency = []
        self.fallback_count = 0
        
        # Conversation context
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_length = 10
        
        # Model warm-up flag
        self._models_warmed_up = False
    
    async def warm_up_models(self) -> None:
        """Pre-load models to reduce latency on first use."""
        if self._models_warmed_up:
            return
        
        try:
            logger.info("Warming up LLM models...")
            
            # Warm up Hugging Face model
            if "huggingface" in self.default_model.lower():
                await self._warm_up_hf_model()
            
            # Warm up OpenAI model
            await self._warm_up_openai_model()
            
            self._models_warmed_up = True
            logger.info("LLM models warmed up successfully")
            
        except Exception as e:
            logger.warning(f"Failed to warm up models: {str(e)}")
    
    async def _warm_up_hf_model(self) -> None:
        """Warm up Hugging Face Mistral model."""
        try:
            test_prompt = "Hello, how are you?"
            result = await self._generate_with_hf(test_prompt)
            logger.debug(f"HF model warm-up test result: {result[:50]}...")
            
        except Exception as e:
            logger.warning(f"Failed to warm up HF model: {str(e)}")
    
    async def _warm_up_openai_model(self) -> None:
        """Warm up OpenAI GPT model."""
        try:
            test_prompt = "Hello, how are you?"
            result = await self._generate_with_openai(test_prompt)
            logger.debug(f"OpenAI model warm-up test result: {result[:50]}...")
            
        except Exception as e:
            logger.warning(f"Failed to warm up OpenAI model: {str(e)}")
    
    def add_to_conversation(self, role: str, content: str) -> None:
        """
        Add message to conversation history.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
        """
        self.conversation_history.append({"role": role, "content": content})
        
        # Keep only recent history
        if len(self.conversation_history) > self.max_history_length * 2:
            self.conversation_history = self.conversation_history[-self.max_history_length * 2:]
    
    def get_conversation_context(self) -> str:
        """
        Get formatted conversation context for LLM.
        
        Returns:
            str: Formatted conversation history
        """
        if not self.conversation_history:
            return ""
        
        context_parts = []
        for msg in self.conversation_history[-self.max_history_length:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    @log_performance
    async def generate_response(self, user_input: str, use_fallback: bool = False) -> Dict[str, Any]:
        """
        Generate LLM response with fallback logic.
        
        Args:
            user_input: User's input text
            use_fallback: Force use of fallback model
            
        Returns:
            Dict containing response and metadata
        """
        try:
            # Add user input to conversation
            self.add_to_conversation("user", user_input)
            
            # Choose model based on fallback flag
            if use_fallback or "openai" in self.default_model.lower():
                return await self._generate_with_openai(user_input)
            else:
                return await self._generate_with_hf(user_input)
                
        except Exception as e:
            logger.error(f"Primary LLM failed, trying fallback: {str(e)}")
            return await self._generate_with_openai(user_input)
    
    async def _generate_with_hf(self, user_input: str) -> Dict[str, Any]:
        """
        Generate response using Hugging Face Mistral.
        
        Args:
            user_input: User's input text
            
        Returns:
            Dict with response and metadata
        """
        start_time = time.time()
        
        try:
            # Prepare conversation context
            context = self.get_conversation_context()
            
            # Create prompt with context
            if context:
                prompt = f"{context}\nUser: {user_input}\nAssistant:"
            else:
                prompt = f"User: {user_input}\nAssistant:"
            
            # Use Hugging Face Inference API
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.hf_api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 150,
                        "temperature": self.temperature,
                        "do_sample": self.temperature > 0,
                        "return_full_text": False
                    }
                }
                
                async with session.post(
                    f"https://api-inference.huggingface.co/models/{self.default_model}",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        latency = time.time() - start_time
                        self.hf_latency.append(latency)
                        
                        # Extract generated text
                        if isinstance(result, list) and len(result) > 0:
                            generated_text = result[0].get("generated_text", "")
                        else:
                            generated_text = result.get("generated_text", "")
                        
                        # Clean up response
                        response_text = self._clean_response(generated_text, prompt)
                        
                        # Add to conversation
                        self.add_to_conversation("assistant", response_text)
                        
                        logger.info(f"HF LLM completed in {latency:.3f}s: '{response_text[:50]}...'")
                        
                        return {
                            "text": response_text,
                            "model": self.default_model,
                            "latency": latency,
                            "tokens_used": len(prompt.split()) + len(response_text.split())
                        }
                    else:
                        raise Exception(f"HF API error: {response.status}")
                        
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"model": self.default_model, "latency": latency})
            raise
    
    async def _generate_with_openai(self, user_input: str) -> Dict[str, Any]:
        """
        Generate response using OpenAI GPT.
        
        Args:
            user_input: User's input text
            
        Returns:
            Dict with response and metadata
        """
        start_time = time.time()
        
        try:
            # Prepare conversation messages
            messages = []
            
            # Add system message
            messages.append({
                "role": "system",
                "content": "You are a helpful AI assistant. Provide concise, natural responses suitable for voice conversation."
            })
            
            # Add conversation history
            for msg in self.conversation_history[-self.max_history_length:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                max_tokens=150,
                temperature=self.temperature,
                stream=False
            )
            
            latency = time.time() - start_time
            self.openai_latency.append(latency)
            self.fallback_count += 1
            
            response_text = response.choices[0].message.content.strip()
            
            # Add to conversation
            self.add_to_conversation("assistant", response_text)
            
            logger.info(f"OpenAI LLM completed in {latency:.3f}s: '{response_text[:50]}...'")
            
            return {
                "text": response_text,
                "model": self.fallback_model,
                "latency": latency,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "fallback_used": True
            }
            
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"model": self.fallback_model, "latency": latency})
            raise
    
    def _clean_response(self, generated_text: str, prompt: str) -> str:
        """
        Clean up generated response text.
        
        Args:
            generated_text: Raw generated text
            prompt: Original prompt
            
        Returns:
            str: Cleaned response text
        """
        # Remove the prompt from the response
        if prompt in generated_text:
            response = generated_text.replace(prompt, "").strip()
        else:
            response = generated_text.strip()
        
        # Remove any remaining "Assistant:" prefixes
        if response.startswith("Assistant:"):
            response = response[10:].strip()
        
        # Limit response length
        if len(response) > 500:
            response = response[:500] + "..."
        
        return response
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for monitoring.
        
        Returns:
            Dict with performance metrics
        """
        return {
            "hf_average_latency": sum(self.hf_latency) / len(self.hf_latency) if self.hf_latency else 0,
            "openai_average_latency": sum(self.openai_latency) / len(self.openai_latency) if self.openai_latency else 0,
            "fallback_count": self.fallback_count,
            "total_generations": len(self.hf_latency) + len(self.openai_latency),
            "conversation_length": len(self.conversation_history)
        }


# Global LLM service instance
llm_service = LLMService() 