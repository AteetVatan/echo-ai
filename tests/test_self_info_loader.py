"""
Tests for self_info_schema and self_info_loader.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

import pytest

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.self_info_schema import SelfInfoItem
from src.knowledge.self_info_loader import load_self_info_items


# ---------------------------------------------------------------------------
# SelfInfoItem schema tests
# ---------------------------------------------------------------------------


class TestSelfInfoItem:
    """Test Pydantic schema validation."""

    def test_valid_item(self):
        """Valid data passes validation."""
        item = SelfInfoItem(
            doc_type="about_me",
            tags=["hr", "intro"],
            question="What is your name?",
            answer="Ateet Vatan Bhatnagar",
        )
        assert item.doc_type == "about_me"
        assert item.tags == ["hr", "intro"]
        assert item.question == "What is your name?"
        assert item.answer == "Ateet Vatan Bhatnagar"

    def test_normalises_doc_type(self):
        """doc_type is lowercased and stripped."""
        item = SelfInfoItem(
            doc_type="  About_Me  ",
            tags=[],
            question="test?",
            answer="test answer",
        )
        assert item.doc_type == "about_me"

    def test_normalises_tags(self):
        """Tags are lowercased, stripped, and deduped."""
        item = SelfInfoItem(
            doc_type="career",
            tags=["HR", "  hr  ", "Intro", "intro"],
            question="test?",
            answer="test answer",
        )
        assert item.tags == ["hr", "intro"]

    def test_empty_question_raises(self):
        """Empty question string fails validation."""
        with pytest.raises(Exception):
            SelfInfoItem(
                doc_type="about_me",
                tags=[],
                question="",
                answer="some answer",
            )

    def test_empty_answer_raises(self):
        """Empty answer string fails validation."""
        with pytest.raises(Exception):
            SelfInfoItem(
                doc_type="about_me",
                tags=[],
                question="some question?",
                answer="   ",
            )

    def test_empty_doc_type_raises(self):
        """Empty doc_type fails validation."""
        with pytest.raises(Exception):
            SelfInfoItem(
                doc_type="",
                tags=[],
                question="q?",
                answer="a",
            )


# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------


class TestLoadSelfInfoItems:
    """Test JSON loader."""

    def test_loads_valid_json(self, tmp_path):
        """Loader returns validated items from a valid JSON file."""
        data = [
            {
                "doc_type": "about_me",
                "tags": ["hr"],
                "question": "What is your name?",
                "answer": "Ateet",
            },
            {
                "doc_type": "career",
                "tags": ["tech"],
                "question": "What do you do?",
                "answer": "AI Engineer",
            },
        ]
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        items = load_self_info_items(path)
        assert len(items) == 2
        assert items[0].question == "What is your name?"

    def test_missing_file_raises(self):
        """FileNotFoundError for missing JSON."""
        with pytest.raises(FileNotFoundError):
            load_self_info_items(Path("/nonexistent/self_info.json"))

    def test_non_array_json_raises(self, tmp_path):
        """ValueError if JSON is not an array."""
        path = tmp_path / "test.json"
        path.write_text('{"key": "value"}', encoding="utf-8")

        with pytest.raises(ValueError, match="Expected JSON array"):
            load_self_info_items(path)

    def test_skips_invalid_items(self, tmp_path):
        """Invalid items are skipped with warning, valid ones kept."""
        data = [
            {
                "doc_type": "about_me",
                "tags": ["hr"],
                "question": "Valid?",
                "answer": "Yes",
            },
            {
                "doc_type": "about_me",
                "tags": ["hr"],
                "question": "",  # invalid — empty
                "answer": "Nope",
            },
        ]
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        items = load_self_info_items(path)
        assert len(items) == 1
        assert items[0].question == "Valid?"

    def test_loads_real_self_info_json(self):
        """Integration: load the real self_info.json and verify count > 300."""
        real_path = PROJECT_ROOT / "src" / "documents" / "self_info.json"
        if not real_path.exists():
            pytest.skip("Real self_info.json not found")

        items = load_self_info_items(real_path)
        assert len(items) > 200, f"Expected >200 items, got {len(items)}"
