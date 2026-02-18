"""
Domain exception hierarchy for EchoAI.

All service/agent/pipeline code should raise (and callers should catch)
these typed exceptions instead of bare ``Exception``.
"""


class EchoAIError(Exception):
    """Base exception for all EchoAI errors."""


class STTError(EchoAIError):
    """Speech-to-Text processing failure."""


class LLMError(EchoAIError):
    """Language-model generation failure."""


class TTSError(EchoAIError):
    """Text-to-Speech synthesis failure."""


class RAGError(EchoAIError):
    """RAG retrieval or agent failure."""


class PipelineError(EchoAIError):
    """Voice-pipeline orchestration failure."""


class DatabaseError(EchoAIError):
    """Database operation failure."""


class AudioProcessingError(EchoAIError):
    """Audio conversion / processing failure."""
