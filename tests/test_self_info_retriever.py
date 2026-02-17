"""
Tests for self_info_retriever and query_router.

These tests require the vector store to be built first.
Run: python -m src.tools.self_info_cli build
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.knowledge.query_router import route_query


# ---------------------------------------------------------------------------
# Query Router tests (pure logic, no store needed)
# ---------------------------------------------------------------------------


class TestQueryRouter:
    """Test deterministic query classification."""

    def test_factual_query(self):
        """Factual question routes to facts index."""
        route = route_query("What is your full name?")
        assert route.primary == "facts"
        assert route.query_type == "factual"

    def test_email_query(self):
        """Email question routes to facts index."""
        route = route_query("What is your email address?")
        assert route.primary == "facts"

    def test_evidence_query(self):
        """Project detail question routes to evidence index."""
        route = route_query("Explain the ApplyBots project in detail")
        assert route.primary == "evidence"
        assert route.query_type == "evidence"

    def test_cv_query(self):
        """CV question routes to evidence index."""
        route = route_query("Show me your CV experience")
        assert route.primary == "evidence"

    def test_timeline_query(self):
        """Timeline question routes to both indices."""
        route = route_query("What is your career timeline?")
        assert route.primary == "both"
        assert route.query_type == "timeline"

    def test_default_query(self):
        """Ambiguous question defaults to facts."""
        route = route_query("Can you help me?")
        assert route.primary == "facts"
        assert route.query_type == "default"

    def test_skills_query(self):
        """Skills question routes to facts."""
        route = route_query("What are your skills?")
        assert route.primary == "facts"
        assert route.query_type == "factual"


# ---------------------------------------------------------------------------
# Retriever tests (require built store)
# ---------------------------------------------------------------------------

def _store_is_built() -> bool:
    """Check if the vector store has been built."""
    try:
        from src.knowledge.self_info_vectorstore import get_self_info_store
        stores = get_self_info_store()
        return stores["facts"]._collection.count() > 0
    except Exception:
        return False


@pytest.fixture(scope="module")
def built_store():
    """Skip if store not built."""
    if not _store_is_built():
        pytest.skip("Vector store not built. Run: python -m src.tools.self_info_cli build")


class TestRetriever:
    """Test hybrid retrieval (requires built vector store)."""

    def test_retrieves_full_name(self, built_store):
        """Retrieve correct doc for name query."""
        from src.knowledge.self_info_retriever import retrieve_self_info

        docs = retrieve_self_info("What is your full name?", k=3)
        assert len(docs) > 0
        content = " ".join(d.page_content for d in docs).lower()
        assert "ateet" in content

    def test_retrieves_location(self, built_store):
        """Retrieve correct doc for location query."""
        from src.knowledge.self_info_retriever import retrieve_self_info

        docs = retrieve_self_info("Where are you located?", k=3)
        assert len(docs) > 0

    def test_retrieves_portfolio(self, built_store):
        """Retrieve correct doc for portfolio query."""
        from src.knowledge.self_info_retriever import retrieve_self_info

        docs = retrieve_self_info("What is your portfolio website?", k=3)
        assert len(docs) > 0

    def test_doc_type_filter(self, built_store):
        """Filtering by doc_type returns only matching docs."""
        from src.knowledge.self_info_retriever import retrieve_self_info

        docs = retrieve_self_info(
            "Tell me about yourself", doc_type="about_me", k=4
        )
        for doc in docs:
            if doc.metadata.get("layer") == "facts":
                assert doc.metadata.get("doc_type") == "about_me"
