"""
Dual-index Chroma vector store for Self-Info RAG.

Index 1 (facts)    — atomic Q&A records from self_info.json
Index 2 (evidence) — chunked CV, GitHub READMEs, LinkedIn CSVs

The store supports upsert-by-stable_id and an optional full rebuild
controlled by the ``SELF_INFO_REBUILD`` env var.
"""

from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path
from typing import Any, NamedTuple

from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_chroma import Chroma

from src.constants import ChromaCollection
from src.knowledge.evidence_loader import load_evidence_documents
from src.knowledge.self_info_documents import to_langchain_documents
from src.knowledge.self_info_loader import load_self_info_items
from src.utils import get_logger, get_settings

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

class SelfInfoStores(NamedTuple):
    """Typed container for the dual-index self-info Chroma stores."""
    facts: Chroma
    evidence: Chroma

    def get(self, name: str) -> Chroma:
        """Access a store by name string (e.g. from query router)."""
        return getattr(self, name)


_store_lock = threading.RLock()
_store_instance: SelfInfoStores | None = None
_embeddings_instance: SentenceTransformerEmbeddings | None = None


def _get_embeddings() -> SentenceTransformerEmbeddings:
    """Return the shared embedding model (cached singleton — loaded once)."""
    global _embeddings_instance  # noqa: PLW0603
    if _embeddings_instance is None:
        settings = get_settings()
        _embeddings_instance = SentenceTransformerEmbeddings(model_name=settings.EMBEDDING_MODEL)
    return _embeddings_instance


# ---------------------------------------------------------------------------
# Build / update
# ---------------------------------------------------------------------------


def build_or_update_self_info_store() -> SelfInfoStores:
    """Build (or refresh) both Chroma indices and return them.

    Behaviour depends on ``SELF_INFO_REBUILD``:
    - ``True``  → delete persist dir and re-embed everything from scratch.
    - ``False`` → upsert only (add new / update changed docs by stable_id).

    Returns
    -------
    SelfInfoStores
        Named tuple with ``.facts`` and ``.evidence`` attributes.
    """
    global _store_instance  # noqa: PLW0603

    settings = get_settings()
    persist_dir = Path(settings.SELF_INFO_CHROMA_DIR)
    rebuild = settings.SELF_INFO_REBUILD

    embeddings = _get_embeddings()

    # ------------------------------------------------------------------
    # Optional: full rebuild
    # ------------------------------------------------------------------
    if rebuild and persist_dir.exists():
        logger.info("SELF_INFO_REBUILD=1 → deleting %s for full rebuild", persist_dir)
        shutil.rmtree(persist_dir)

    persist_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Index 1 — Facts (self_info.json)
    # ------------------------------------------------------------------
    json_path = Path(settings.SELF_INFO_JSON_PATH)
    items = load_self_info_items(json_path)
    fact_docs = to_langchain_documents(items)

    facts_store = Chroma(
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
        collection_name=ChromaCollection.SELF_INFO_FACTS,
        collection_metadata={"hnsw:space": "cosine"},
    )

    _upsert_documents(facts_store, fact_docs)
    try:
        _facts_count = facts_store._collection.count()
    except Exception:
        _facts_count = len(fact_docs)
    logger.info(
        "Facts index: %d docs in collection '%s'",
        _facts_count,
        ChromaCollection.SELF_INFO_FACTS,
    )

    # ------------------------------------------------------------------
    # Index 2 — Evidence (CV, READMEs, LinkedIn)
    # ------------------------------------------------------------------
    evidence_dir = Path(settings.EVIDENCE_DOCS_DIR)
    evidence_docs = load_evidence_documents(evidence_dir)

    evidence_store = Chroma(
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
        collection_name=ChromaCollection.SELF_INFO_EVIDENCE,
        collection_metadata={"hnsw:space": "cosine"},
    )

    _upsert_documents(evidence_store, evidence_docs)
    try:
        _evidence_count = evidence_store._collection.count()
    except Exception:
        _evidence_count = len(evidence_docs)
    logger.info(
        "Evidence index: %d docs in collection '%s'",
        _evidence_count,
        ChromaCollection.SELF_INFO_EVIDENCE,
    )

    result = SelfInfoStores(facts=facts_store, evidence=evidence_store)

    with _store_lock:
        _store_instance = result

    logger.info("Self-Info vector store ready at %s", persist_dir)
    return result


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------

def _upsert_documents(store: Chroma, docs: list) -> None:
    """Upsert documents using their ``stable_id`` metadata as Chroma IDs."""
    if not docs:
        return

    ids = [doc.metadata["stable_id"] for doc in docs]
    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]

    # Chroma's underlying collection supports upsert natively
    store._collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=store._embedding_function.embed_documents(texts),
    )


# ---------------------------------------------------------------------------
# Lazy singleton accessor
# ---------------------------------------------------------------------------

def get_self_info_store() -> SelfInfoStores:
    """Return the singleton store, building it on first call.

    Thread-safe for typical app usage (single build, many reads).
    """
    global _store_instance  # noqa: PLW0603

    if _store_instance is not None:
        return _store_instance

    with _store_lock:
        # Double-check after acquiring lock
        if _store_instance is not None:
            return _store_instance

        settings = get_settings()
        persist_dir = Path(settings.SELF_INFO_CHROMA_DIR)
        embeddings = _get_embeddings()

        # If persist dir exists and has data, reuse it (no rebuild)
        if persist_dir.exists() and not settings.SELF_INFO_REBUILD:
            try:
                facts_store = Chroma(
                    persist_directory=str(persist_dir),
                    embedding_function=embeddings,
                    collection_name=ChromaCollection.SELF_INFO_FACTS,
                    collection_metadata={"hnsw:space": "cosine"},
                )
                evidence_store = Chroma(
                    persist_directory=str(persist_dir),
                    embedding_function=embeddings,
                    collection_name=ChromaCollection.SELF_INFO_EVIDENCE,
                    collection_metadata={"hnsw:space": "cosine"},
                )

                # Probe with similarity_search instead of count() 
                # (count() crashes on ChromaDB 0.5.0 with SQLite compat bug)
                probe = facts_store.similarity_search("test", k=1)
                if len(probe) > 0:
                    logger.info(
                        "Reusing existing self-info store from %s",
                        persist_dir,
                    )
                    _store_instance = SelfInfoStores(facts=facts_store, evidence=evidence_store)
                    return _store_instance
                else:
                    logger.info("Persisted store is empty, will rebuild")
            except Exception as reuse_err:
                logger.warning(
                    "Failed to reuse persisted store (%s). "
                    "Deleting and rebuilding from scratch.",
                    reuse_err,
                )
                try:
                    shutil.rmtree(persist_dir)
                except Exception as rm_err:
                    logger.error("Could not delete corrupt store dir: %s", rm_err)

        # Build fresh
        logger.info("Building self-info store (first access or empty)")
        _store_instance = build_or_update_self_info_store()
        return _store_instance
