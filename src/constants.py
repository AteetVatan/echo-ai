"""
Centralised constants and enums for EchoAI.

All magic strings, event names, status labels, model identifiers, and
numeric thresholds live here so they are defined once and imported
everywhere else.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# WebSocket message types (client → server and server → client)
# ---------------------------------------------------------------------------

class WSMessageType(str, Enum):
    AUDIO = "audio"
    AUDIO_CHUNK = "audio_chunk"
    START_STREAMING = "start_streaming"
    STOP_STREAMING = "stop_streaming"
    TEXT = "text"
    PING = "ping"
    PONG = "pong"
    STREAMING_BUFFER = "streaming_buffer"

    CONNECTION = "connection"
    PROCESSING = "processing"
    RESPONSE = "response"
    TEXT_RESPONSE = "text_response"
    STREAMING_RESPONSE = "streaming_response"
    STREAMING_STARTED = "streaming_started"
    STREAMING_STOPPED = "streaming_stopped"
    CHUNK_RECEIVED = "chunk_received"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Pipeline / RAG source labels
# ---------------------------------------------------------------------------

class PipelineSource(str, Enum):
    CACHE = "cache"
    RAG_SELF_INFO = "rag_self_info"
    LLM_FALLBACK = "llm_fallback"
    LLM_DIRECT = "llm_direct"
    ERROR_FALLBACK = "error_fallback"
    ERROR = "error"
    PIPELINE = "pipeline"
    AGENT = "agent"


# ---------------------------------------------------------------------------
# Model identifiers
# ---------------------------------------------------------------------------

class ModelName(str, Enum):
    DEEPSEEK_AI = "deepseek_ai"
    MISTRAL_AI = "mistral_ai"
    OPENAI_GPT4O_MINI = "openai_gpt4o_mini"
    EDGE_TTS = "edge_tts"
    EDGE_TTS_CACHED = "edge_tts_cached"
    FASTER_WHISPER_SMALL = "faster_whisper_small"
    OPENAI_WHISPER = "openai_whisper"
    LANGCHAIN_RAG = "langchain_rag_agent"
    AGNO_AGENT = "agno_agent"
    UNKNOWN = "unknown"
    NONE = "none"


# ---------------------------------------------------------------------------
# Chat roles
# ---------------------------------------------------------------------------

class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Knowledge / cache metadata
# ---------------------------------------------------------------------------

class KnowledgeType(str, Enum):
    SELF_INFO = "self_info"
    REPLY_CACHE = "reply_cache"
    CV_PROFILE = "cv_profile"


# ---------------------------------------------------------------------------
# Chroma collection names
# ---------------------------------------------------------------------------

class ChromaCollection(str, Enum):
    REPLY_CACHE = "echoai_reply_cache"
    SELF_INFO = "echoai_self_info"


# ---------------------------------------------------------------------------
# Numeric thresholds (no more magic numbers)
# ---------------------------------------------------------------------------

SEMANTIC_CACHE_SIMILARITY_THRESHOLD = 0.95
REPLY_CACHE_SIMILARITY_THRESHOLD = 0.85
IN_MEMORY_CACHE_MAX_SIZE = 1000
IN_MEMORY_CACHE_EVICT_COUNT = 100
LATENCY_WINDOW_SIZE = 100
MAX_CONVERSATION_HISTORY = 10
LLM_RESPONSE_MAX_LENGTH = 1000

AUDIO_CHUNK_MAX_BYTES = 1024 * 1024        # 1 MB per chunk
AUDIO_BUFFER_MAX_BYTES = 10 * 1024 * 1024  # 10 MB total buffer

TEXT_SPLITTER_CHUNK_SIZE = 500
TEXT_SPLITTER_CHUNK_OVERLAP = 50
RAG_RETRIEVER_TOP_K = 5
STREAMING_BATCH_SIZE = 5
STREAM_PROCESSING_BATCH_SIZE = 10

TAIL_PAD_SECONDS = 0.01
NORMALIZE_TARGET_RMS = 0.1
NORMALIZE_MAX_GAIN = 10.0

DEFAULT_AUDIO_CHUNK_SIZE = 1024
