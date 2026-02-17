"""
Smoke tests for the Self-Info RAG answer chain.

Requires:
1. Vector store built: python -m src.tools.self_info_cli build
2. LLM API key available (DEEPSEEK_API_KEY or MISTRAL_API_KEY)

Tests are skipped gracefully if either prerequisite is missing.
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()


def _has_llm_key() -> bool:
    """Check if any LLM API key is available."""
    return bool(
        os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("MISTRAL_API_KEY")
    )


def _store_is_built() -> bool:
    """Check if the vector store has been built."""
    try:
        from src.knowledge.self_info_vectorstore import get_self_info_store
        stores = get_self_info_store()
        return stores["facts"]._collection.count() > 0
    except Exception:
        return False


@pytest.fixture(scope="module")
def rag_ready():
    """Skip if store not built or no LLM key."""
    if not _store_is_built():
        pytest.skip("Vector store not built. Run: python -m src.tools.self_info_cli build")
    if not _has_llm_key():
        pytest.skip("No LLM API key available (DEEPSEEK_API_KEY or MISTRAL_API_KEY)")


class TestAnswerAboutAteet:
    """Smoke tests for the RAG answer chain."""

    def test_email_answer(self, rag_ready):
        """Must return ab@masxai.com when asked about email."""
        from src.knowledge.self_info_rag import answer_about_ateet

        result = answer_about_ateet("What is your email address?")

        assert isinstance(result, dict)
        assert "answer" in result
        assert "ab@masxai.com" in result["answer"].lower()

    def test_structured_output(self, rag_ready):
        """Output must contain answer, key_facts, sources, route."""
        from src.knowledge.self_info_rag import answer_about_ateet

        result = answer_about_ateet("What is your name?")

        assert "answer" in result
        assert "key_facts" in result
        assert "sources" in result
        assert "route" in result
        assert isinstance(result["key_facts"], list)
        assert isinstance(result["sources"], list)

    def test_grounding_refusal(self, rag_ready):
        """Should refuse to answer about information not in the knowledge base."""
        from src.knowledge.self_info_rag import answer_about_ateet

        result = answer_about_ateet(
            "What is the chemical formula for water?"
        )

        # Should either refuse or give a very generic non-hallucinated response
        answer_lower = result["answer"].lower()
        # The answer should not pretend to know chemistry
        assert "h2o" not in answer_lower or "knowledge base" in answer_lower
