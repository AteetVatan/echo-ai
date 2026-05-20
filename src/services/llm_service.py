"""Language model service with DeepSeek primary and Mistral fallback."""

import asyncio
import time
from typing import Any

import openai
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from src.constants import (
    ChatRole,
    LATENCY_WINDOW_SIZE,
    LLM_RESPONSE_MAX_LENGTH,
    MAX_CONVERSATION_HISTORY,
    ModelName,
)
from src.exceptions import LLMError
from src.utils import get_logger, get_settings, log_error_with_context, log_performance


logger = get_logger(__name__)
settings = get_settings()
DEEPSEEK_ERRORS = (LLMError, openai.OpenAIError, AttributeError, IndexError, TypeError)
MISTRAL_ERRORS = (
    LLMError,
    RuntimeError,
    AttributeError,
    IndexError,
    TypeError,
    ValueError,
)


class LLMService:
    """Language model service with fallback support."""

    def __init__(self) -> None:
        self._load_settings()
        self.deepseek_client = None
        self.mistral_client = None
        self.models_warmed_up = False
        self.conversation_history: list[dict[str, str]] = []
        self.max_history_length = MAX_CONVERSATION_HISTORY
        self.performance_stats = self._new_performance_stats()

    def _load_settings(self) -> None:
        """Copy LLM settings onto the service instance."""
        self.deepseek_api_key = settings.DEEPSEEK_API_KEY
        self.deepseek_api_base = settings.DEEPSEEK_API_BASE
        self.deepseek_model = settings.DEEPSEEK_MODEL
        self.mistral_api_key = settings.MISTRAL_API_KEY
        self.mistral_api_base = settings.MISTRAL_API_BASE
        self.mistral_model = settings.MISTRAL_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.timeout = settings.LLM_TIMEOUT

    @staticmethod
    def _new_performance_stats() -> dict[str, Any]:
        """Create a fresh performance stats dictionary."""
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_latency": 0.0,
            "latencies": [],
        }

    async def warm_up_models(self) -> None:
        """Warm up configured LLM clients."""
        logger.info("Warming up LLM models...")
        self._warm_up_deepseek_client()
        self._warm_up_mistral_client()
        self.models_warmed_up = True
        logger.info("LLM models warmed up successfully")

    def _warm_up_deepseek_client(self) -> None:
        """Initialise the primary OpenAI-compatible client."""
        if not self.deepseek_api_key:
            return
        try:
            self.deepseek_client = openai.AsyncOpenAI(
                api_key=self.deepseek_api_key,
                base_url=self.deepseek_api_base,
                timeout=self.timeout,
            )
            logger.info(
                "DeepSeek client initialized with model %s", self.deepseek_model
            )
        except (openai.OpenAIError, TypeError, ValueError) as exc:
            logger.warning("Failed to initialize DeepSeek client: %s", exc)

    def _warm_up_mistral_client(self) -> None:
        """Initialise the fallback Mistral client."""
        if not self.mistral_api_key:
            return
        try:
            self.mistral_client = MistralClient(
                api_key=self.mistral_api_key,
                endpoint=self.mistral_api_base,
                timeout=int(self.timeout),
            )
            logger.info("Mistral client initialized with model %s", self.mistral_model)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to initialize Mistral client: %s", exc)

    def add_to_conversation(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[
                -self.max_history_length :
            ]

    def get_conversation_context(self) -> str:
        """Get conversation context as a formatted string."""
        if not self.conversation_history:
            return ""
        return "\n".join(
            self._format_context_message(message)
            for message in self.conversation_history
        )

    @staticmethod
    def _format_context_message(message: dict[str, str]) -> str:
        """Format one conversation message for prompt context."""
        role = message["role"]
        if role == ChatRole.USER:
            return f"User: {message['content']}"
        if role == ChatRole.ASSISTANT:
            return f"Assistant: {message['content']}"
        return message["content"]

    @log_performance
    async def generate_response(
        self, user_input: str, *, use_fallback: bool = False
    ) -> dict[str, Any]:
        """Generate a response using the primary or fallback LLM."""
        start_time = time.time()
        self.performance_stats["total_requests"] += 1
        if not use_fallback and self.deepseek_client:
            result = await self._try_primary_llm(user_input)
            if "error" not in result:
                return result
        if self.mistral_client:
            return await self._try_fallback_llm(user_input, start_time)
        self._update_stats(time.time() - start_time, success=False)
        return {"error": "No LLM services available"}

    async def _try_primary_llm(self, user_input: str) -> dict[str, Any]:
        """Try DeepSeek and return an error marker on failure."""
        try:
            result = await self._generate_with_deepseek(user_input)
            self._update_stats(result["latency"], success=True)
            return result
        except LLMError as exc:
            logger.warning("Primary LLM failed, trying fallback: %s", exc)
            return {"error": str(exc)}

    async def _try_fallback_llm(
        self, user_input: str, start_time: float
    ) -> dict[str, Any]:
        """Try Mistral and convert failure into a public error payload."""
        try:
            result = await self._generate_with_mistral(user_input)
            self._update_stats(result["latency"], success=True)
            return result
        except LLMError as exc:
            self._update_stats(time.time() - start_time, success=False)
            logger.error("Fallback LLM failed: %s", exc)
            return {"error": f"LLM failed: {exc}"}

    async def _generate_with_deepseek(self, user_input: str) -> dict[str, Any]:
        """Generate a response through DeepSeek."""
        start_time = time.time()
        try:
            if not self.deepseek_client:
                raise LLMError("DeepSeek client not initialized")
            response = await self._create_deepseek_completion(user_input)
            return self._deepseek_result(response, start_time)
        except DEEPSEEK_ERRORS as exc:
            self._raise_llm_error("_generate_with_deepseek", start_time, exc)

    async def _create_deepseek_completion(self, user_input: str):
        """Call the OpenAI-compatible DeepSeek chat completion API."""
        return await self.deepseek_client.chat.completions.create(
            model=self.deepseek_model,
            messages=self._deepseek_messages(user_input),
            temperature=self.temperature,
            timeout=self.timeout,
        )

    def _deepseek_result(self, response: Any, start_time: float) -> dict[str, Any]:
        """Build a public result payload from a DeepSeek response."""
        latency = time.time() - start_time
        content = response.choices[0].message.content.strip()
        logger.debug("DeepSeek generation completed in %.3fs", latency)
        return {
            "text": self._clean_response(content),
            "model": ModelName.DEEPSEEK_AI,
            "latency": latency,
            "tokens_used": response.usage.total_tokens,
        }

    def _deepseek_messages(self, user_input: str) -> list[dict[str, str]]:
        """Build OpenAI-compatible messages for DeepSeek."""
        messages = list(self.conversation_history)
        messages.append({"role": ChatRole.USER, "content": user_input})
        return messages

    async def _generate_with_mistral(self, user_input: str) -> dict[str, Any]:
        """Generate a response through Mistral."""
        start_time = time.time()
        try:
            if not self.mistral_client:
                raise LLMError("Mistral client not initialized")
            response = await self._call_mistral_chat(self._mistral_messages(user_input))
            return self._mistral_result(response, start_time)
        except MISTRAL_ERRORS as exc:
            self._raise_llm_error("_generate_with_mistral", start_time, exc)

    def _mistral_messages(self, user_input: str) -> list[ChatMessage]:
        """Build SDK-native messages for Mistral."""
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in self.conversation_history
        ]
        messages.append(ChatMessage(role=ChatRole.USER, content=user_input))
        return messages

    async def _call_mistral_chat(self, messages: list[ChatMessage]) -> Any:
        """Run the synchronous Mistral SDK call off the event loop."""
        return await asyncio.to_thread(
            self.mistral_client.chat,
            model=self.mistral_model,
            messages=messages,
            temperature=self.temperature,
        )

    def _mistral_result(self, response: Any, start_time: float) -> dict[str, Any]:
        """Build a public result payload from a Mistral response."""
        latency = time.time() - start_time
        content = response.choices[0].message.content.strip()
        logger.debug("Mistral generation completed in %.3fs", latency)
        return {
            "text": self._clean_response(content),
            "model": ModelName.MISTRAL_AI,
            "latency": latency,
            "tokens_used": self._mistral_tokens_used(response),
        }

    @staticmethod
    def _mistral_tokens_used(response: Any) -> int:
        """Extract token usage from SDK responses that expose it."""
        if hasattr(response.usage, "total_tokens"):
            return response.usage.total_tokens
        return 0

    def _raise_llm_error(self, method: str, start_time: float, exc: Exception) -> None:
        """Log and re-raise a domain LLM error with context."""
        log_error_with_context(
            logger,
            exc,
            {"method": method, "latency": time.time() - start_time},
        )
        raise LLMError(f"{method} failed") from exc

    def _clean_response(self, response: str) -> str:
        """Clean and format an LLM response."""
        response = self._remove_prompt_artifacts(response.strip())
        if len(response) > LLM_RESPONSE_MAX_LENGTH:
            return response[:LLM_RESPONSE_MAX_LENGTH] + "..."
        return response

    @staticmethod
    def _remove_prompt_artifacts(response: str) -> str:
        """Remove role prefixes that occasionally leak from prompts."""
        if response.startswith("User:"):
            return response.split("User:", 1)[0].strip()
        if response.startswith("Assistant:"):
            return response.split("Assistant:", 1)[1].strip()
        return response

    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")

    def _update_stats(self, latency: float, *, success: bool) -> None:
        """Update performance statistics."""
        self.performance_stats["latencies"].append(latency)
        key = "successful_requests" if success else "failed_requests"
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
            "total_requests": self.performance_stats["total_requests"],
            "successful_requests": self.performance_stats["successful_requests"],
            "failed_requests": self.performance_stats["failed_requests"],
            "avg_latency": self.performance_stats["avg_latency"],
            "models_warmed_up": self.models_warmed_up,
            "primary_model": self._primary_model_name(),
            "fallback_model": self._fallback_model_name(),
            "conversation_length": len(self.conversation_history),
        }

    def _primary_model_name(self) -> ModelName:
        """Return the active primary model identifier."""
        return ModelName.DEEPSEEK_AI if self.deepseek_client else ModelName.NONE

    def _fallback_model_name(self) -> ModelName:
        """Return the active fallback model identifier."""
        return ModelName.MISTRAL_AI if self.mistral_client else ModelName.NONE


llm_service = LLMService()
