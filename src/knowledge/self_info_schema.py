"""
Pydantic v2 schema for self_info.json records.

Each record is an atomic fact with doc_type, tags, question, and answer.
Validators normalise casing/whitespace and enforce non-empty content.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class SelfInfoItem(BaseModel):
    """Single Q&A record from self_info.json."""

    doc_type: str
    tags: list[str]
    question: str
    answer: str

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("doc_type", mode="before")
    @classmethod
    def _normalise_doc_type(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("doc_type must be a string")
        v = v.strip().lower()
        if not v:
            raise ValueError("doc_type must not be empty")
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def _normalise_tags(cls, v: list) -> list[str]:
        if not isinstance(v, list):
            raise ValueError("tags must be a list")
        seen: set[str] = set()
        result: list[str] = []
        for tag in v:
            t = str(tag).strip().lower()
            if t and t not in seen:
                seen.add(t)
                result.append(t)
        return result

    @field_validator("question", mode="before")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("question must be a string")
        v = v.strip()
        if not v:
            raise ValueError("question must not be empty")
        return v

    @field_validator("answer", mode="before")
    @classmethod
    def _strip_answer(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("answer must be a string")
        v = v.strip()
        if not v:
            raise ValueError("answer must not be empty")
        return v
