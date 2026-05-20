"""Compatibility helpers for LangChain's Supabase vector store.

LangChain Community 0.3.x still mutates ``query_builder.params`` on RPC
builders. Newer postgrest-py versions expose params under
``query_builder.request.params`` instead, so vector searches fail before the
RPC is executed. This subclass keeps the public VectorStore API while using
the RPC arguments supported by this project's SQL functions.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document


def _metadata_matches_filter(
    metadata: Dict[str, Any], filter_: Optional[Dict[str, Any]]
) -> bool:
    """Apply the simple metadata filter forms used by local retrievers."""
    if not filter_:
        return True

    for key, expected in filter_.items():
        actual = metadata.get(key)
        if isinstance(expected, dict) and "$in" in expected:
            if actual not in expected["$in"]:
                return False
        elif actual != expected:
            return False

    return True


class CompatibleSupabaseVectorStore(SupabaseVectorStore):
    """SupabaseVectorStore variant compatible with postgrest-py 2.22+."""

    def _rpc_rows(
        self,
        query: List[float],
        k: int,
        filter: Optional[Dict[str, Any]] = None,
        postgrest_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        # If metadata filtering is needed, fetch a wider candidate set and
        # apply the project filter client-side. The SQL functions here do not
        # accept LangChain's optional "filter" RPC argument.
        match_count = max(k * 4, k) if filter else k
        query_builder = self._client.rpc(
            self.query_name,
            {
                "query_embedding": query,
                "match_count": match_count,
            },
        )

        if postgrest_filter:
            query_builder.request.params = query_builder.request.params.set(
                "and", f"({postgrest_filter})"
            )

        response = query_builder.execute()
        rows = response.data or []
        if not isinstance(rows, list):
            rows = [rows]

        return [
            row
            for row in rows
            if row.get("content")
            and _metadata_matches_filter(row.get("metadata", {}), filter)
        ][:k]

    def similarity_search_by_vector_with_relevance_scores(
        self,
        query: List[float],
        k: int,
        filter: Optional[Dict[str, Any]] = None,
        postgrest_filter: Optional[str] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Tuple[Document, float]]:
        rows = self._rpc_rows(query, k, filter, postgrest_filter)
        matches = [
            (
                Document(
                    metadata=row.get("metadata", {}),
                    page_content=row.get("content", ""),
                ),
                row.get("similarity", 0.0),
            )
            for row in rows
        ]

        if score_threshold is not None:
            matches = [
                (doc, similarity)
                for doc, similarity in matches
                if similarity >= score_threshold
            ]
            if len(matches) == 0:
                warnings.warn(
                    "No relevant docs were retrieved using the relevance score"
                    f" threshold {score_threshold}",
                    stacklevel=2,
                )

        return matches

    def similarity_search_by_vector_returning_embeddings(
        self,
        query: List[float],
        k: int,
        filter: Optional[Dict[str, Any]] = None,
        postgrest_filter: Optional[str] = None,
    ) -> List[Tuple[Document, float, np.ndarray]]:
        rows = self._rpc_rows(query, k, filter, postgrest_filter)
        return [
            (
                Document(
                    metadata=row.get("metadata", {}),
                    page_content=row.get("content", ""),
                ),
                row.get("similarity", 0.0),
                np.fromstring(
                    row.get("embedding", "").strip("[]"), np.float32, sep=","
                ),
            )
            for row in rows
        ]
