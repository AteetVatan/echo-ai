"""RAG Persona Database - Personal Document RAG System with Agno Orchestration."""

__version__ = "0.1.0"
__author__ = "AI Team"
__email__ = "team@example.com"

from .rag_core.settings import load_settings
from .rag_core.schema import DocumentItem, Metadata

__all__ = ["load_settings", "DocumentItem", "Metadata"]
