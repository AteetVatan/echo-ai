"""
Dual-index Supabase pgvector store for Self-Info RAG.

Index 1 (facts)    — atomic Q&A records from self_info.json
Index 2 (evidence) — chunked CV, GitHub READMEs, LinkedIn CSVs

Replaces the previous ChromaDB implementation with SupabaseVectorStore.
The store supports upsert-by-stable_id and an optional full rebuild
controlled by the ``SELF_INFO_REBUILD`` env var.

On first access, if the pgvector tables are empty, the store builds
lazily by embedding source documents and inserting into Supabase.
This removes the need for a Docker build-time dependency on Supabase.
"""

from __future__ import annotations

import threading
from typing import NamedTuple

from langchain_core.embeddings import Embeddings
from postgrest.exceptions import APIError
from supabase import create_client, Client as SupabaseClient

from backend.knowledge.evidence_loader import load_evidence_documents
from backend.knowledge.self_info_documents import to_langchain_documents
from backend.knowledge.self_info_loader import load_self_info_items
from backend.knowledge.supabase_compat import (
    CompatibleSupabaseVectorStore as SupabaseVectorStore,
)
from backend.utils import get_logger, get_settings

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Embedding class using transformers directly
#
# Necessary because sentence-transformers 5.x is incompatible with
# transformers 5.x (broken lazy-import paths). This class loads the
# same HuggingFace model and reproduces the same mean-pooling + L2
# normalisation that SentenceTransformer('all-MiniLM-L6-v2') performs,
# producing identical 384-dim vectors.
# ---------------------------------------------------------------------------


class LocalEmbeddings(Embeddings):
    """LangChain-compatible embeddings using transformers AutoModel.

    Loads ``sentence-transformers/<model_name>`` from HuggingFace and
    produces 384-dim L2-normalised vectors via mean pooling — identical
    output to ``SentenceTransformer(model_name).encode()``.
    """

    BATCH_SIZE = 32  # documents per forward pass

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        import torch
        import transformers
        from transformers import AutoModel, AutoTokenizer

        # Suppress progress bar + LOAD REPORT (prints directly to stderr)
        transformers.logging.set_verbosity_error()

        hf_name = f"sentence-transformers/{model_name}"
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(hf_name)
            self.model = AutoModel.from_pretrained(hf_name)
        except (OSError, RuntimeError, ValueError) as e:
            raise RuntimeError(
                f"Failed to load embedding model '{hf_name}'. "
                f"Ensure the model is cached or network is available: {e}"
            ) from e

        # Device selection: CUDA > MPS > CPU
        if torch.cuda.is_available():
            self._device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self._device = torch.device("mps")
        else:
            self._device = torch.device("cpu")

        self.model.to(self._device).eval()
        logger.info(
            "LocalEmbeddings ready: model=%s, device=%s, dim=%d",
            hf_name,
            self._device,
            self.model.config.hidden_size,
        )

    def _encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode a single batch of texts into normalised embeddings."""
        import torch

        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        ).to(self._device)

        with torch.no_grad():
            output = self.model(**encoded)

        # Mean pooling over token embeddings (attention-mask weighted)
        mask = encoded["attention_mask"].unsqueeze(-1).float()
        embeddings = (output.last_hidden_state * mask).sum(1) / mask.sum(1)
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings.cpu().tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of documents with automatic batching."""
        if not texts:
            return []

        results: list[list[float]] = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            try:
                results.extend(self._encode_batch(batch))
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    logger.warning(
                        "OOM on batch of %d, falling back to one-at-a-time", len(batch)
                    )
                    for text in batch:
                        results.extend(self._encode_batch([text]))
                else:
                    raise
        return results

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        return self._encode_batch([text])[0]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


class SelfInfoStores(NamedTuple):
    """Typed container for the dual-index self-info pgvector stores."""

    facts: SupabaseVectorStore
    evidence: SupabaseVectorStore

    def get(self, name: str) -> SupabaseVectorStore:
        """Access a store by name string (e.g. from query router)."""
        return getattr(self, name)


_store_lock = threading.RLock()
_store_instance: SelfInfoStores | None = None
_embeddings_instance: LocalEmbeddings | None = None
_supabase_client: SupabaseClient | None = None


def _get_embeddings() -> LocalEmbeddings:
    """Return the shared embedding model (cached singleton — loaded once)."""
    global _embeddings_instance  # noqa: PLW0603
    if _embeddings_instance is None:
        settings = get_settings()
        _embeddings_instance = LocalEmbeddings(model_name=settings.EMBEDDING_MODEL)
    return _embeddings_instance


def _get_supabase_client() -> SupabaseClient:
    """Return a shared Supabase client (singleton)."""
    global _supabase_client  # noqa: PLW0603
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _supabase_client


# ---------------------------------------------------------------------------
# Build / update
# ---------------------------------------------------------------------------


def build_or_update_self_info_store() -> SelfInfoStores:
    """Build (or refresh) both pgvector indices and return them.

    Behaviour depends on ``SELF_INFO_REBUILD``:
    - ``True``  → TRUNCATE pgvector tables and re-embed everything.
    - ``False`` → upsert only (add new / update changed docs by stable_id).

    Returns
    -------
    SelfInfoStores
        Named tuple with ``.facts`` and ``.evidence`` attributes.
    """
    global _store_instance  # noqa: PLW0603

    settings = get_settings()
    rebuild = settings.SELF_INFO_REBUILD

    embeddings = _get_embeddings()
    client = _get_supabase_client()

    # ------------------------------------------------------------------
    # Optional: full rebuild via TRUNCATE
    # ------------------------------------------------------------------
    if rebuild:
        logger.info("SELF_INFO_REBUILD=1 → truncating pgvector tables for full rebuild")
        try:
            client.table("documents_self_info_facts").delete().neq("id", "").execute()
            client.table("documents_self_info_evidence").delete().neq(
                "id", ""
            ).execute()
            logger.info("Truncated self-info pgvector tables")
        except (APIError, RuntimeError, TypeError, ValueError) as e:
            logger.warning("Failed to truncate tables (may be empty): %s", e)

    # ------------------------------------------------------------------
    # Create SupabaseVectorStore instances
    # ------------------------------------------------------------------
    facts_store = SupabaseVectorStore(
        client=client,
        embedding=embeddings,
        table_name="documents_self_info_facts",
        query_name="match_self_info_facts",
    )

    evidence_store = SupabaseVectorStore(
        client=client,
        embedding=embeddings,
        table_name="documents_self_info_evidence",
        query_name="match_self_info_evidence",
    )

    # ------------------------------------------------------------------
    # Index 1 — Facts (self_info.json)
    # ------------------------------------------------------------------
    from pathlib import Path

    json_path = Path(settings.SELF_INFO_JSON_PATH)
    items = load_self_info_items(json_path)
    fact_docs = to_langchain_documents(items)

    _upsert_documents(facts_store, fact_docs, client, "documents_self_info_facts")

    try:
        result = (
            client.table("documents_self_info_facts")
            .select("id", count="exact")
            .execute()
        )
        _facts_count = result.count if result.count is not None else len(fact_docs)
    except (APIError, RuntimeError, TypeError, ValueError):
        _facts_count = len(fact_docs)

    logger.info("Facts index: %d docs in 'documents_self_info_facts'", _facts_count)

    # ------------------------------------------------------------------
    # Index 2 — Evidence (CV, READMEs, LinkedIn)
    # ------------------------------------------------------------------
    evidence_dir = Path(settings.EVIDENCE_DOCS_DIR)
    evidence_docs = load_evidence_documents(evidence_dir)

    _upsert_documents(
        evidence_store, evidence_docs, client, "documents_self_info_evidence"
    )

    try:
        result = (
            client.table("documents_self_info_evidence")
            .select("id", count="exact")
            .execute()
        )
        _evidence_count = (
            result.count if result.count is not None else len(evidence_docs)
        )
    except (APIError, RuntimeError, TypeError, ValueError):
        _evidence_count = len(evidence_docs)

    logger.info(
        "Evidence index: %d docs in 'documents_self_info_evidence'", _evidence_count
    )

    result = SelfInfoStores(facts=facts_store, evidence=evidence_store)

    with _store_lock:
        _store_instance = result

    logger.info("Self-Info pgvector store ready")
    return result


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def _upsert_documents(
    store: SupabaseVectorStore,
    docs: list,
    client: SupabaseClient,
    table_name: str,
) -> None:
    """Upsert documents using their ``stable_id`` metadata as IDs."""
    if not docs:
        return

    ids = [doc.metadata["stable_id"] for doc in docs]
    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]

    # SupabaseVectorStore.add_texts supports ids= for upsert
    store.add_texts(texts=texts, metadatas=metadatas, ids=ids)


# ---------------------------------------------------------------------------
# Lazy singleton accessor
# ---------------------------------------------------------------------------


def get_self_info_store() -> SelfInfoStores:
    """Return the singleton store, building it on first call.

    Thread-safe for typical app usage (single build, many reads).
    If the pgvector tables are empty, triggers a full build (~10s).
    """
    global _store_instance  # noqa: PLW0603

    if _store_instance is not None:
        return _store_instance

    with _store_lock:
        # Double-check after acquiring lock
        if _store_instance is not None:
            return _store_instance

        settings = get_settings()
        embeddings = _get_embeddings()
        client = _get_supabase_client()

        # Check if pgvector tables already have data
        if not settings.SELF_INFO_REBUILD:
            try:
                facts_store = SupabaseVectorStore(
                    client=client,
                    embedding=embeddings,
                    table_name="documents_self_info_facts",
                    query_name="match_self_info_facts",
                )
                evidence_store = SupabaseVectorStore(
                    client=client,
                    embedding=embeddings,
                    table_name="documents_self_info_evidence",
                    query_name="match_self_info_evidence",
                )

                # Probe: do the tables have data?
                # Use a lightweight row-count query instead of similarity_search
                # to avoid supabase-py/postgrest-py '.params' incompatibility.
                probe = (
                    client.table("documents_self_info_facts")
                    .select("id", count="exact")
                    .limit(1)
                    .execute()
                )
                if probe.count and probe.count > 0:
                    logger.info("Reusing existing self-info pgvector store")
                    _store_instance = SelfInfoStores(
                        facts=facts_store, evidence=evidence_store
                    )
                    return _store_instance
                else:
                    logger.info("pgvector tables are empty, will build")
            except (APIError, RuntimeError, TypeError, ValueError) as reuse_err:
                logger.warning(
                    "Failed to probe pgvector store (%s). Building from scratch.",
                    reuse_err,
                )

        # Build fresh
        logger.info("Building self-info store (first access or empty)")
        _store_instance = build_or_update_self_info_store()
        return _store_instance
