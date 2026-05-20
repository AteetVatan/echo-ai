"""
Grounded RAG answer chain for Self-Info queries.

Rules:
- Temperature = 0 (hardcoded, defence-in-depth).
- Use ONLY retrieved context — never invent facts.
- If context is insufficient → explicit refusal.
- Returns structured output: answer, key_facts, sources, route.
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

from backend.constants import (
    INSUFFICIENT_SELF_INFO_ANSWER,
    RAG_LLM_MAX_TOKENS,
    RAG_RETRIEVER_TOP_K,
)
from backend.knowledge.self_info_retriever import retrieve_self_info
from backend.utils import get_logger, get_settings

logger = get_logger(__name__)

_RAG_TEMPLATE = """\
You are Ateet's AI clone — a professional AI engineer. You have access ONLY
to the CONTEXT passages below. Follow these rules strictly:

1. Answer using ONLY information present in the CONTEXT.
2. If the CONTEXT does not contain enough information, reply EXACTLY:
   "I don't have that information in my self_info knowledge base."
3. Do NOT invent links, employers, dates, certifications, or metrics.
4. Adapt your tone to the question:
   - Greeting / casual → 1–2 short sentences.
   - Professional / career → detailed, structured answer.
   - Technical → clear, implementation-ready explanation.
5. Sound like Ateet — confident, precise, systems-thinking — not a generic chatbot.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""

_PROMPT = PromptTemplate(
    template=_RAG_TEMPLATE,
    input_variables=["context", "question"],
)


def _get_llm():
    """Return the best available LangChain chat model at temperature=0."""
    settings = get_settings()
    try:
        from langchain_openai import ChatOpenAI

        if settings.DEEPSEEK_API_KEY:
            return ChatOpenAI(
                model=settings.DEEPSEEK_MODEL,
                openai_api_key=settings.DEEPSEEK_API_KEY,
                openai_api_base=settings.DEEPSEEK_API_BASE,
                temperature=0,
                max_tokens=RAG_LLM_MAX_TOKENS,
                timeout=settings.LLM_TIMEOUT,
            )
    except (ImportError, TypeError, ValueError) as exc:
        logger.warning("DeepSeek LLM init failed: %s", exc)

    try:
        from langchain_mistralai import ChatMistralAI

        if settings.MISTRAL_API_KEY:
            return ChatMistralAI(
                model=settings.MISTRAL_MODEL,
                mistral_api_key=settings.MISTRAL_API_KEY,
                temperature=0,
                max_tokens=RAG_LLM_MAX_TOKENS,
            )
    except (ImportError, TypeError, ValueError) as exc:
        logger.warning("Mistral LLM init failed: %s", exc)

    raise RuntimeError("No LLM available — both DeepSeek and Mistral failed")


def answer_about_ateet(
    question: str,
    *,
    doc_type: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Answer a question about Ateet using grounded RAG.

    Parameters
    ----------
    question:
        User question (natural language).
    doc_type:
        Optional metadata filter.
    tags:
        Optional tag filter.

    Returns
    -------
    dict with keys:
        - ``answer``    : str — the grounded response
        - ``key_facts`` : list[str] — extracted facts used (page_content snippets)
        - ``sources``   : list[str] — stable_ids of documents used
        - ``route``     : str — which index was primary
    """
    docs: list[Document] = retrieve_self_info(
        question, doc_type=doc_type, tags=tags, k=RAG_RETRIEVER_TOP_K
    )
    answer = _generate_answer(question, docs)
    key_facts = [_first_fact(doc) for doc in docs]
    sources = [d.metadata.get("stable_id", "unknown") for d in docs]
    route_label = _route_label(docs)
    logger.info(
        "RAG answer for '%s': route=%s, sources=%s", question[:60], route_label, sources
    )
    return {
        "answer": answer.strip(),
        "key_facts": key_facts,
        "sources": sources,
        "route": route_label,
    }


def _generate_answer(question: str, docs: list[Document]) -> str:
    """Generate a grounded answer from retrieved documents."""
    try:
        llm = _get_llm()
        prompt_text = _PROMPT.format(context=_context(docs), question=question)
        response = llm.invoke(prompt_text)
        return response.content if hasattr(response, "content") else str(response)
    except (RuntimeError, TypeError, ValueError, AttributeError) as exc:
        logger.error("LLM generation failed: %s", exc)
        return INSUFFICIENT_SELF_INFO_ANSWER


def _context(docs: list[Document]) -> str:
    """Build the prompt context string."""
    context_parts: list[str] = []
    for i, doc in enumerate(docs, 1):
        source_name = doc.metadata.get("source", "unknown")
        context_parts.append(f"[{i}] (source: {source_name})\n{doc.page_content}")
    return "\n\n".join(context_parts) if context_parts else "No relevant context found."


def _first_fact(doc: Document) -> str:
    """Extract the first line snippet from a source document."""
    return doc.page_content.strip().split("\n")[0][:200]


def _route_label(docs: list[Document]) -> str:
    """Build the route label from document metadata."""
    routes = {doc.metadata.get("layer", "unknown") for doc in docs}
    return ",".join(sorted(routes))
