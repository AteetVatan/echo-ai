"""
Deterministic query router for Self-Info RAG.

Classifies user queries to decide which index to hit first:
- facts  → FAQ records (name, email, skills, certifications, location, etc.)
- evidence → document chunks (project details, CV details, "show me" / "explain")
- both  → timeline / relationship queries (hit both indices)

No LLM call required — uses keyword matching + intent patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

QueryTarget = Literal["facts", "evidence", "both"]


@dataclass(frozen=True)
class QueryRoute:
    """Result of query classification."""

    primary: QueryTarget
    secondary: QueryTarget | None
    query_type: str  # human-readable label for logging


# ---------------------------------------------------------------------------
# Pattern lists (extend as needed)
# ---------------------------------------------------------------------------

_FACTUAL_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(name|full name|who are you)\b",
        r"\b(email|e-mail|mail)\b",
        r"\b(phone|contact|reach|connect)\b",
        r"\b(location|located|city|country|where.*live|based)\b",
        r"\b(title|role|position|designation)\b",
        r"\b(bio|introduction|about you|about me|about ateet)\b",
        r"\b(skills?|tech stack|stack|tools?|frameworks?|languages?)\b",
        r"\b(certifications?|certified|pcep)\b",
        r"\b(education|degree|school|university|masterschool)\b",
        r"\b(linkedin|github|portfolio|website|url|link)\b",
        r"\b(salary|rate|pricing)\b",
        r"\b(hobbies|interests|personality)\b",
        r"\bhow do you\b",
        r"\bwhat is your\b",
        r"\bwhat are your\b",
        r"\btell me about yourself\b",
    ]
]

_EVIDENCE_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(show me|prove|evidence|detail|elaborate)\b",
        r"\b(explain.*project|describe.*project|project.*details?)\b",
        r"\b(cv|resume|curriculum)\b",
        r"\b(experience at|worked at|work.*at|employment)\b",
        r"\b(ihs markit|markit)\b",
        r"\bapplybots\b",
        r"\bgalileo\b",
        r"\bshotgraph\b",
        r"\bmasx\b",
        r"\bmedai\b",
        r"\bdrone\b",
        r"\b(readme|documentation|docs)\b",
        r"\b(endorsement|recommendation)\b",
    ]
]

_TIMELINE_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(timeline|career path|progression|journey)\b",
        r"\b(map|relationship|connect.*to)\b",
        r"\b(end.to.end|all.*projects|overview)\b",
        r"\b(history|over the years)\b",
    ]
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def route_query(query: str) -> QueryRoute:
    """Classify *query* and return routing decision.

    Priority order:
    1. Timeline / relationship → both indices
    2. Evidence / detail → evidence first, facts as supplement
    3. Factual / profile → facts first, evidence as supplement
    4. Default → facts first
    """

    # Score each category
    timeline_score = sum(1 for p in _TIMELINE_PATTERNS if p.search(query))
    evidence_score = sum(1 for p in _EVIDENCE_PATTERNS if p.search(query))
    factual_score = sum(1 for p in _FACTUAL_PATTERNS if p.search(query))

    if timeline_score > 0:
        return QueryRoute(primary="both", secondary=None, query_type="timeline")

    if evidence_score > factual_score:
        return QueryRoute(primary="evidence", secondary="facts", query_type="evidence")

    if factual_score > 0:
        return QueryRoute(primary="facts", secondary="evidence", query_type="factual")

    # Default: facts first (most queries are about profile)
    return QueryRoute(primary="facts", secondary="evidence", query_type="default")
