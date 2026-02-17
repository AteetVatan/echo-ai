"""
Hybrid retriever for Self-Info RAG.

Combines vector similarity search with BM25 keyword matching, applies
metadata post-filtering (doc_type + tags), and routes queries to the
appropriate index via the query router.
"""

from __future__ import annotations

import json
from typing import Literal

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from src.knowledge.query_router import QueryRoute, route_query
from src.knowledge.self_info_vectorstore import get_self_info_store
from src.utils import get_logger

logger = get_logger(__name__)


def _post_filter(
    docs: list[Document],
    *,
    doc_type: str | None = None,
    tags: list[str] | None = None,
) -> list[Document]:
    """Apply Python-side metadata filters to retrieved documents."""
    result = docs

    if doc_type:
        doc_type_lower = doc_type.lower()
        result = [d for d in result if d.metadata.get("doc_type") == doc_type_lower]

    if tags:
        tags_lower = {t.lower() for t in tags}
        filtered = []
        for d in result:
            # Try parsing JSON tags list first
            meta_tags_raw = d.metadata.get("tags", "")
            try:
                meta_tags = set(json.loads(meta_tags_raw))
            except (json.JSONDecodeError, TypeError):
                meta_tags = set()

            # Fallback: comma-separated tags_str
            tags_str = d.metadata.get("tags_str", "")
            if tags_str:
                meta_tags.update(t.strip().lower() for t in tags_str.split(","))

            if tags_lower & meta_tags:
                filtered.append(d)
        result = filtered

    return result


def _retrieve_from_store(
    store,  # Chroma instance
    query: str,
    k: int,
    search_type: str,
    *,
    doc_type: str | None = None,
) -> list[Document]:
    """Run vector search on a single Chroma collection.

    Applies doc_type as a Chroma metadata filter when possible.
    """
    search_kwargs: dict = {"k": k}
    if doc_type:
        search_kwargs["filter"] = {"doc_type": doc_type.lower()}

    try:
        retriever = store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs,
        )
        return retriever.invoke(query)
    except Exception as exc:
        logger.warning("Chroma retrieval failed (filter=%s): %s", doc_type, exc)
        # Retry without filter
        retriever = store.as_retriever(
            search_type=search_type,
            search_kwargs={"k": k},
        )
        return retriever.invoke(query)


def _bm25_search(docs: list[Document], query: str, k: int) -> list[Document]:
    """Run BM25 keyword search over an in-memory document list."""
    if not docs:
        return []
    try:
        bm25 = BM25Retriever.from_documents(docs, k=k)
        return bm25.invoke(query)
    except Exception as exc:
        logger.warning("BM25 search failed: %s", exc)
        return []


def _merge_and_dedupe(
    vec_docs: list[Document],
    bm25_docs: list[Document],
    *,
    vec_weight: float = 0.6,
) -> list[Document]:
    """Merge vector + BM25 results, deduplicate by stable_id, preserve order."""
    seen: set[str] = set()
    merged: list[Document] = []

    # Interleave: vector-first
    all_docs = vec_docs + bm25_docs
    for doc in all_docs:
        sid = doc.metadata.get("stable_id", id(doc))
        if sid not in seen:
            seen.add(sid)
            merged.append(doc)

    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def retrieve_self_info(
    query: str,
    *,
    doc_type: str | None = None,
    tags: list[str] | None = None,
    k: int = 4,
    search_type: Literal["similarity", "mmr"] = "similarity",
) -> list[Document]:
    """Retrieve relevant documents using hybrid search + query routing.

    Parameters
    ----------
    query:
        User question.
    doc_type:
        Optional metadata filter (e.g. ``"about_me"``, ``"career"``).
    tags:
        Optional tag filter — docs with any matching tag are kept.
    k:
        Number of results to return.
    search_type:
        Chroma search type (``"similarity"`` or ``"mmr"``).

    Returns
    -------
    list[Document]
        Up to *k* documents, post-filtered and deduplicated.
    """
    stores = get_self_info_store()
    route: QueryRoute = route_query(query)

    logger.info("Query route: %s (primary=%s)", route.query_type, route.primary)

    all_docs: list[Document] = []

    # ------------------------------------------------------------------
    # Primary index retrieval
    # ------------------------------------------------------------------
    if route.primary in ("facts", "both"):
        vec_docs = _retrieve_from_store(
            stores.facts, query, k=k, search_type=search_type, doc_type=doc_type
        )
        # Skip BM25 for now — vector search on well-structured Q&A is sufficient.
        # BM25 can be added later as a cached module-level index if needed.
        all_docs.extend(vec_docs)

    if route.primary in ("evidence", "both"):
        vec_docs = _retrieve_from_store(
            stores.evidence, query, k=k, search_type=search_type, doc_type=doc_type
        )
        all_docs.extend(vec_docs)

    # ------------------------------------------------------------------
    # Secondary index (supplement if primary didn't yield enough)
    # ------------------------------------------------------------------
    if route.secondary and len(all_docs) < k:
        sec_store = stores.get(route.secondary)
        extra = _retrieve_from_store(
            sec_store, query, k=k, search_type=search_type, doc_type=doc_type
        )
        all_docs.extend(extra)

    # ------------------------------------------------------------------
    # Post-filter
    # ------------------------------------------------------------------
    filtered = _post_filter(all_docs, doc_type=doc_type, tags=tags)

    # Expand if filtering reduced results too much
    if len(filtered) < k and (doc_type or tags):
        logger.info("Post-filter yielded %d docs (< k=%d), expanding search", len(filtered), k)
        for store in (stores.facts, stores.evidence):
            extra = _retrieve_from_store(
                store, query, k=k * 3, search_type=search_type
            )
            extra_filtered = _post_filter(extra, doc_type=doc_type, tags=tags)
            filtered.extend(extra_filtered)

    # Dedupe final results
    seen: set[str] = set()
    final: list[Document] = []
    for doc in filtered:
        sid = doc.metadata.get("stable_id", str(id(doc)))
        if sid not in seen:
            seen.add(sid)
            final.append(doc)
        if len(final) >= k:
            break

    logger.info("Returning %d docs for query: %s", len(final), query[:80])
    return final
