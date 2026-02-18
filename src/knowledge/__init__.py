"""
Self-Info RAG Knowledge Package for EchoAI.

Two-layer knowledge base:
- Layer A (Facts Store): self_info.json Q&A records
- Layer B (Evidence Vault): CV, GitHub READMEs, LinkedIn data

Public API:
- answer_about_ateet: RAG answer chain (temperature=0)
- build_or_update_self_info_store: build/refresh both indices
- retrieve_self_info: hybrid retrieval with filtering
- get_self_info_store: lazy singleton for both Chroma collections
"""

from src.knowledge.self_info_rag import answer_about_ateet
from src.knowledge.self_info_vectorstore import (
    build_or_update_self_info_store,
    get_self_info_store,
)
from src.knowledge.self_info_retriever import retrieve_self_info

__all__ = [
    "answer_about_ateet",
    "build_or_update_self_info_store",
    "get_self_info_store",
    "retrieve_self_info",
]
