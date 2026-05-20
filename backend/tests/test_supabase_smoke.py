"""
Smoke test for EchoAI Supabase + pgvector integration.

Tests the critical path:
  1. Embedding model produces 384-dim vectors
  2. Supabase connection + query works
  3. Self-info vector store initialises
  4. Reply cache semantic search works end-to-end

Usage:
    python -m pytest tests/test_supabase_smoke.py -v
    # or directly:
    python tests/test_supabase_smoke.py
"""

import asyncio
import os
import sys
import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_SMOKE") != "1",
    reason="Supabase/HuggingFace smoke tests are opt-in; set RUN_SUPABASE_SMOKE=1.",
)


# ---------------------------------------------------------------------------
# 1. Embedding model
# ---------------------------------------------------------------------------


class TestLocalEmbeddings:
    """Verify the custom LocalEmbeddings class produces correct output."""

    def test_embed_query_produces_384_dim(self):
        from backend.knowledge.self_info_vectorstore import _get_embeddings

        emb = _get_embeddings()
        vec = emb.embed_query("Hello world")
        assert isinstance(vec, list), "embed_query should return a list"
        assert len(vec) == 384, f"Expected 384-dim, got {len(vec)}"

    def test_embed_documents_batch(self):
        from backend.knowledge.self_info_vectorstore import _get_embeddings

        emb = _get_embeddings()
        docs = ["First document", "Second document", "Third one"]
        vecs = emb.embed_documents(docs)
        assert len(vecs) == 3, f"Expected 3 vectors, got {len(vecs)}"
        for i, v in enumerate(vecs):
            assert len(v) == 384, f"Doc {i}: expected 384-dim, got {len(v)}"

    def test_embed_empty_list(self):
        from backend.knowledge.self_info_vectorstore import _get_embeddings

        emb = _get_embeddings()
        assert emb.embed_documents([]) == []


# ---------------------------------------------------------------------------
# 2. Supabase connection
# ---------------------------------------------------------------------------


class TestSupabaseConnection:
    """Verify Supabase connectivity."""

    @pytest.mark.asyncio
    async def test_db_operations_initialise(self):
        from backend.db.db_operations import DBOperations

        db = DBOperations()
        await db.initialize()
        assert db._initialized, "DBOperations should be initialised"
        # Sanity query — should not raise
        async with db._pool.acquire() as conn:
            row = await conn.fetchval("SELECT 1")
        assert row == 1
        await db.close()


# ---------------------------------------------------------------------------
# 3. Self-info vector store
# ---------------------------------------------------------------------------


class TestSelfInfoStore:
    """Verify the pgvector self-info store loads."""

    def test_store_loads(self):
        from backend.knowledge.self_info_vectorstore import get_self_info_store

        stores = get_self_info_store()
        assert stores is not None
        assert stores.facts is not None
        assert stores.evidence is not None

    def test_facts_search(self):
        from backend.knowledge.self_info_vectorstore import get_self_info_store

        stores = get_self_info_store()
        results = stores.facts.similarity_search("work experience", k=2)
        assert len(results) > 0, "Facts store should return results"


# ---------------------------------------------------------------------------
# 4. Reply cache round-trip
# ---------------------------------------------------------------------------


class TestReplyCache:
    """Verify reply cache semantic search works."""

    @pytest.mark.asyncio
    async def test_find_similar_reply_returns_none_for_nonsense(self):
        from backend.agents.langchain_rag_agent import get_rag_agent
        from backend.db.db_operations import DBOperations

        db = DBOperations()
        await db.initialize()
        agent = get_rag_agent(db)

        result = await agent.reply_cache_manager.find_similar_reply(
            "zzz_completely_random_test_string_12345"
        )
        # Should return None — no cached reply matches random text
        assert result is None
        await db.close()


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("EchoAI Supabase Smoke Test")
    print("=" * 60)

    # Quick non-pytest run for CI
    from backend.knowledge.self_info_vectorstore import _get_embeddings

    emb = _get_embeddings()
    vec = emb.embed_query("test")
    assert len(vec) == 384, f"FAIL: embedding dim = {len(vec)}"
    print(f"[OK] Embeddings: 384-dim OK (device={emb._device})")

    from backend.db.db_operations import DBOperations

    db = DBOperations()
    asyncio.run(db.initialize())
    print("[OK] Supabase connection: OK")

    from backend.knowledge.self_info_vectorstore import get_self_info_store

    stores = get_self_info_store()
    print(f"[OK] Self-info stores: facts={stores.facts}, evidence={stores.evidence}")

    results = stores.facts.similarity_search("work experience", k=1)
    print(f"[OK] Facts search: {len(results)} result(s)")

    asyncio.run(db.close())
    print("\n" + "=" * 60)
    print("ALL SMOKE TESTS PASSED")
    print("=" * 60)
