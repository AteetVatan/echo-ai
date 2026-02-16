"""
Language Model service for EchoAI voice chat system.

This module provides LLM functionality using Mistral AI API as primary
and GPT-4o-mini (OpenAI) as fallback for generating conversational responses.
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional
import aiohttp
import openai
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from src.utils import get_settings
from src.utils import get_logger, log_performance, log_error_with_context
from src.constants import ModelName, ChatRole, LATENCY_WINDOW_SIZE, MAX_CONVERSATION_HISTORY, LLM_RESPONSE_MAX_LENGTH
from src.exceptions import LLMError


logger = get_logger(__name__)
settings = get_settings()


class LLMService:
    """Language Model service with fallback support."""
    
    def __init__(self):
        self.mistral_api_key = settings.MISTRAL_API_KEY
        self.mistral_api_base = settings.MISTRAL_API_BASE
        self.mistral_model = settings.MISTRAL_MODEL
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.timeout = settings.LLM_TIMEOUT
        
        # Model instances
        self.mistral_client = None
        self.openai_client = None
        self.models_warmed_up = False
        
        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_length = MAX_CONVERSATION_HISTORY
        
        # Performance tracking
        self.performance_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_latency": 0.0,
            "latencies": []
        }
    
    async def warm_up_models(self) -> None:
        """Warm up LLM models for optimal performance."""
        try:
            logger.info("Warming up LLM models...")
            
            # Warm up Mistral client
            if self.mistral_api_key:
                try:
                    self.mistral_client = MistralClient(
                        api_key=self.mistral_api_key,
                        endpoint=self.mistral_api_base
                    )
                    logger.info(f"Mistral client initialized with model {self.mistral_model}")
                except Exception as e:
                    logger.warning(f"Failed to initialize Mistral client: {str(e)}")
            
            # Warm up OpenAI client
            if self.openai_api_key:
                try:
                    self.openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
                    logger.info("OpenAI client initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
            
            self.models_warmed_up = True
            logger.info("LLM models warmed up successfully")
            
        except Exception as e:
            logger.error(f"Failed to warm up LLM models: {str(e)}")
    
    def add_to_conversation(self, role: str, content: str) -> None:
        """Add message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})
        
        # Keep only recent messages
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def get_conversation_context(self) -> str:
        """Get conversation context as formatted string."""
        if not self.conversation_history:
            return ""
        
        context_parts = []
        for message in self.conversation_history:
            role = message["role"]
            content = message["content"]
            if role == ChatRole.USER:
                context_parts.append(f"User: {content}")
            elif role == ChatRole.ASSISTANT:
                context_parts.append(f"Assistant: {content}")
        
        return "\n".join(context_parts)
    
    @log_performance
    async def generate_response(self, user_input: str, *, use_fallback: bool = False) -> Dict[str, Any]:
        """
        Generate response using primary or fallback LLM service.
        
        Args:
            user_input: User input text
            use_fallback: Whether to use fallback service
            
        Returns:
            Dict with response result
        """
        start_time = time.time()
        
        try:
            self.performance_stats["total_requests"] += 1
            
            # Try primary service first (unless fallback is explicitly requested)
            if not use_fallback and self.mistral_client:
                try:
                    result = await self._generate_with_mistral(user_input)
                    self._update_stats(result["latency"], True)
                    return result
                except Exception as e:
                    logger.warning(f"Primary LLM failed, trying fallback: {str(e)}")
            
            # Use fallback service
            if self.openai_client:
                try:
                    result = await self._generate_with_openai(user_input)
                    self._update_stats(result["latency"], True)
                    return result
                except Exception as e:
                    logger.error(f"Fallback LLM also failed: {str(e)}")
                    self._update_stats(time.time() - start_time, False)
                    return {"error": f"LLM failed: {str(e)}"}
            else:
                error_msg = "No LLM services available"
                self._update_stats(time.time() - start_time, False)
                return {"error": error_msg}
                
        except Exception as e:
            latency = time.time() - start_time
            self._update_stats(latency, False)
            log_error_with_context(logger, e, {"method": "generate_response", "input_length": len(user_input)})
            return {"error": f"Response generation failed: {str(e)}"}
    
    async def _generate_with_mistral(self, user_input: str) -> Dict[str, Any]:
        """Generate response using Mistral AI API."""
        start_time = time.time()
        
        try:
            if not self.mistral_client:
                raise LLMError("Mistral client not initialized")
            
            # Build messages with conversation history
            messages = []
            
            # Add conversation history
            for msg in self.conversation_history:
                messages.append(ChatMessage(
                    role=msg["role"],
                    content=msg["content"]
                ))
            
            # Add current user input
            messages.append(ChatMessage(
                role=ChatRole.USER,
                content=user_input
            ))
            
            # Generate response
            response = self.mistral_client.chat(
                model=self.mistral_model, #mistral-small
                messages=messages,
                temperature=self.temperature,
                #max_tokens=500
            )
            
            assistant_response = response.choices[0].message.content.strip()
            cleaned_response = self._clean_response(assistant_response)
            
            latency = time.time() - start_time
            
            logger.debug(f"Mistral generation completed in {latency:.3f}s")
            
            return {
                "text": cleaned_response,
                "model": ModelName.MISTRAL_AI,
                "latency": latency,
                "tokens_used": response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 0
            }
            
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"method": "_generate_with_mistral", "latency": latency})
            raise
    
    async def _generate_with_openai(self, user_input: str) -> Dict[str, Any]:
        """Generate response using OpenAI model."""
        start_time = time.time()
        
        try:
            if not self.openai_client:
                raise LLMError("OpenAI client not initialized")
            
            # Build messages with conversation history
            messages = []
            
            # Add conversation history
            for msg in self.conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add current user input
            messages.append({
                "role": ChatRole.USER,
                "content": user_input
            })
            
            # Generate response
            response = await self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=self.temperature,
                #max_tokens=500
            )
            
            assistant_response = response.choices[0].message.content.strip()
            cleaned_response = self._clean_response(assistant_response)
            
            latency = time.time() - start_time
            
            logger.debug(f"OpenAI generation completed in {latency:.3f}s")
            
            return {
                "text": cleaned_response,
                "model": ModelName.OPENAI_GPT4O_MINI,
                "latency": latency,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"method": "_generate_with_openai", "latency": latency})
            raise
    
    def _clean_response(self, response: str) -> str:
        """Clean and format LLM response."""
        # Remove extra whitespace
        response = response.strip()
        
        # Remove any remaining prompt artifacts
        if response.startswith("User:"):
            response = response.split("User:", 1)[0].strip()
        
        if response.startswith("Assistant:"):
            response = response.split("Assistant:", 1)[1].strip()
        
        # Limit response length
        if len(response) > LLM_RESPONSE_MAX_LENGTH:
            response = response[:LLM_RESPONSE_MAX_LENGTH] + "..."
        
        return response
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")
    
    def _update_stats(self, latency: float, success: bool) -> None:
        """Update performance statistics."""
        self.performance_stats["latencies"].append(latency)
        
        if success:
            self.performance_stats["successful_requests"] += 1
        else:
            self.performance_stats["failed_requests"] += 1
        
        # Keep only last 100 latencies
        if len(self.performance_stats["latencies"]) > LATENCY_WINDOW_SIZE:
            self.performance_stats["latencies"] = self.performance_stats["latencies"][-LATENCY_WINDOW_SIZE:]
        
        # Update average latency
        if self.performance_stats["latencies"]:
            self.performance_stats["avg_latency"] = sum(self.performance_stats["latencies"]) / len(self.performance_stats["latencies"])
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "total_requests": self.performance_stats["total_requests"],
            "successful_requests": self.performance_stats["successful_requests"],
            "failed_requests": self.performance_stats["failed_requests"],
            "avg_latency": self.performance_stats["avg_latency"],
            "models_warmed_up": self.models_warmed_up,
            "primary_model": ModelName.MISTRAL_AI if self.mistral_client else ModelName.NONE,
            "fallback_model": ModelName.OPENAI_GPT4O_MINI if self.openai_client else ModelName.NONE,
            "conversation_length": len(self.conversation_history)
        }


# Global service instance
llm_service = LLMService() 