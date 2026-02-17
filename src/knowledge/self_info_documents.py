"""
Convert SelfInfoItem records into LangChain Documents for Chroma indexing.

Each document gets a deterministic ``stable_id`` so we can upsert without
duplicating entries.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from langchain_core.documents import Document

if TYPE_CHECKING:
    from src.knowledge.self_info_schema import SelfInfoItem


def _make_stable_id(doc_type: str, question: str) -> str:
    """Return the first 16 hex chars of sha-256(doc_type + question)."""
    raw = f"{doc_type}:{question}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def to_langchain_documents(items: list[SelfInfoItem]) -> list[Document]:
    """Convert validated SelfInfoItem list into LangChain Documents.

    Parameters
    ----------
    items:
        Validated self-info records.

    Returns
    -------
    list[Document]
        Each document has:
        - ``page_content``  = ``Q: {question}\\nA: {answer}``
        - ``metadata``      = doc_type, tags (JSON), tags_str, source, stable_id, layer
    """
    documents: list[Document] = []
    for item in items:
        stable_id = _make_stable_id(item.doc_type, item.question)
        doc = Document(
            page_content=f"Q: {item.question}\nA: {item.answer}",
            metadata={
                "doc_type": item.doc_type,
                "tags": json.dumps(item.tags),          # JSON string (Chroma can't store lists)
                "tags_str": ", ".join(item.tags),        # comma-sep for post-filtering
                "source": "self_info.json",
                "stable_id": stable_id,
                "layer": "facts",
            },
        )
        documents.append(doc)
    return documents
