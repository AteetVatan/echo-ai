"""
Hybrid query expansion for the RAG agent.

Strategy:
  1. Regex-first  — instant, zero-cost pattern matching for known topics.
  2. LLM fallback — for short/ambiguous queries that don't match any regex,
     a lightweight LLM call rewrites the query into a retrieval-friendly
     question about Ateet.

Kept in its own file for easy maintenance.
"""

import re
from typing import List, Tuple, Optional
from re import Pattern

from src.utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------
QueryExpansionRule = Tuple[Pattern[str], str]

# ---------------------------------------------------------------------------
# Regex-based expansions  (checked first — instant & free)
# ---------------------------------------------------------------------------
QUERY_EXPANSIONS: List[QueryExpansionRule] = [
    # ── Identity / About ────────────────────────────────────────────
    (re.compile(r"\b(about|who|intro)\b", re.I),
     "Tell me about Ateet Vatan Bahmani — his background, role, and expertise."),
    (re.compile(r"\b(name|full\s*name)\b", re.I),
     "What is Ateet Vatan Bahmani's full name?"),
    (re.compile(r"\b(bio|biography|profile|summary)\b", re.I),
     "Give me a short bio or introduction of Ateet Vatan Bahmani."),
    (re.compile(r"\b(title|designation|role|position)\b", re.I),
     "What is Ateet's professional title and current role?"),

    # ── Work Experience / Career ────────────────────────────────────
    (re.compile(r"work.*exp", re.I),
     "What is Ateet's complete work experience and employment history?"),
    (re.compile(r"\b(career|jobs?|employ)", re.I),
     "What is Ateet's career history and employment timeline?"),
    (re.compile(r"\b(timeline|career\s*path|career\s*journey)\b", re.I),
     "What is Ateet's career timeline from start to present?"),
    (re.compile(r"\b(ihs|markit|ihs\s*markit)\b", re.I),
     "Tell me about Ateet's work at IHS Markit."),
    (re.compile(r"\b(freelanc|consult|self.?employ)\b", re.I),
     "Tell me about Ateet's freelance and consulting work."),
    (re.compile(r"\b(senior|promotion|growth)\b", re.I),
     "How did Ateet grow from Software Engineer to Senior Software Engineer?"),
    (re.compile(r"\b(first\s*job|first\s*role|started)\b", re.I),
     "What was Ateet's first professional role?"),
    (re.compile(r"\b(years?\s*(of)?\s*exp|how\s*long|tenure)\b", re.I),
     "How many years of professional experience does Ateet have?"),

    # ── Skills / Tech Stack ─────────────────────────────────────────
    (re.compile(r"\bskills?\b", re.I),
     "What are Ateet's technical skills and tech stack?"),
    (re.compile(r"\b(tech\s*stack|technologies|tools)\b", re.I),
     "What is Ateet's full tech stack and toolset?"),
    (re.compile(r"\b(python|flask|fastapi)\b", re.I),
     "What Python frameworks and tools does Ateet use?"),
    (re.compile(r"\b(langchain|langgraph|llm\s*framework)\b", re.I),
     "What AI and LLM frameworks does Ateet use, including LangChain?"),
    (re.compile(r"\b(autogen|crewai|multi.?agent)\b", re.I),
     "What multi-agent frameworks does Ateet use, such as AutoGen and CrewAI?"),
    (re.compile(r"\b(react|angular|vite|frontend|front.?end)\b", re.I),
     "What frontend technologies does Ateet work with?"),
    (re.compile(r"\b(aws|cloud|lambda|ecs|s3|azure|devops)\b", re.I),
     "What is Ateet's cloud and DevOps expertise?"),
    (re.compile(r"\b(docker|ci.?cd|github\s*actions|gitlab)\b", re.I),
     "What DevOps and CI/CD tools does Ateet use?"),
    (re.compile(r"\b(database|supabase|redis|sql|vector\s*db|chroma|faiss|pinecone)\b", re.I),
     "What databases and data infrastructure does Ateet work with?"),
    (re.compile(r"\b(c\s*#|\.net|dotnet|csharp)\b", re.I),
     "Does Ateet have experience with C# and .NET?"),
    (re.compile(r"\b(hugging\s*face|transformers|embeddings)\b", re.I),
     "What Hugging Face and embedding models does Ateet use?"),
    (re.compile(r"\b(rag|retrieval|vector\s*search)\b", re.I),
     "What is Ateet's experience with RAG and retrieval-augmented generation?"),
    (re.compile(r"\b(api|rest|microservice)\b", re.I),
     "What is Ateet's experience building APIs and microservices?"),
    (re.compile(r"\b(full\s*stack|fullstack)\b", re.I),
     "What is Ateet's fullstack development experience?"),

    # ── Education / Certifications ──────────────────────────────────
    (re.compile(r"\beducat", re.I),
     "What is Ateet's education and academic background?"),
    (re.compile(r"\bcertif", re.I),
     "What certifications does Ateet have?"),
    (re.compile(r"\b(pcep|masterschool|degree|diploma|course|training)\b", re.I),
     "What formal education, courses, and certifications has Ateet completed?"),

    # ── Projects / Portfolio ────────────────────────────────────────
    (re.compile(r"\bproject", re.I),
     "What projects has Ateet worked on?"),
    (re.compile(r"\b(portfolio|featured)\b", re.I),
     "What are Ateet's featured projects and portfolio highlights?"),
    (re.compile(r"\b(masx|geopolit|doctrine|strategic)\b", re.I),
     "Tell me about Ateet's MASX AI project."),
    (re.compile(r"\b(echo\s*ai|voice\s*clone|digital\s*twin)\b", re.I),
     "Tell me about Ateet's EchoAI project — the AI voice clone system."),
    (re.compile(r"\b(agentic\s*match|agenticmatch|clip|brand\s*match)\b", re.I),
     "Tell me about Ateet's AgenticMatch-3H project."),
    (re.compile(r"\b(nexora|portfolio\s*app|portfolio\s*website)\b", re.I),
     "Tell me about Ateet's Nexora portfolio website."),
    (re.compile(r"\b(movie|crud|management\s*system)\b", re.I),
     "Tell me about Ateet's Movie Management System project."),
    (re.compile(r"\b(drone|delivery\s*planner)\b", re.I),
     "Tell me about Ateet's Drone Delivery Planner project."),
    (re.compile(r"\b(masterblog|blog\s*api)\b", re.I),
     "Tell me about Ateet's Masterblog API project."),
    (re.compile(r"\b(github|open.?source|repo)", re.I),
     "Where can I find Ateet's open-source repositories on GitHub?"),

    # ── Contact / Links ─────────────────────────────────────────────
    (re.compile(r"\b(contact|email|phone|reach)\b", re.I),
     "What are Ateet's contact details and how can I reach him?"),
    (re.compile(r"\b(linkedin|social)\b", re.I),
     "What is Ateet's LinkedIn profile and social links?"),
    (re.compile(r"\b(website|site|url|link)\b", re.I),
     "What are Ateet's online profiles and links?"),

    # ── Location ────────────────────────────────────────────────────
    (re.compile(r"\b(locat|city|countr|where.*live|based|essen|germany)\b", re.I),
     "Where is Ateet located?"),

    # ── Personality / Soft Skills / HR ──────────────────────────────
    (re.compile(r"\b(hobb|interest|personal)\b", re.I),
     "What are Ateet's hobbies and personal interests?"),
    (re.compile(r"\b(personalit|character|trait|soft\s*skill)\b", re.I),
     "What are Ateet's personality traits and soft skills?"),
    (re.compile(r"\b(strength|weakness|superpower)\b", re.I),
     "What are Ateet's strengths and weaknesses?"),
    (re.compile(r"\b(leadership|lead|manage|team)\b", re.I),
     "What is Ateet's leadership and team management style?"),
    (re.compile(r"\b(mentor|coach|guid)\b", re.I),
     "Does Ateet mentor juniors? What is his mentoring approach?"),
    (re.compile(r"\b(communicat|collaborat|teamwork)\b", re.I),
     "What is Ateet's communication and collaboration style?"),
    (re.compile(r"\b(motiv|passion|drive|inspir)\b", re.I),
     "What motivates and drives Ateet in his career?"),
    (re.compile(r"\b(conflict|disagree|challeng)\b", re.I),
     "How does Ateet handle conflict and challenges?"),
    (re.compile(r"\b(stress|pressure|deadline|burn.?out)\b", re.I),
     "How does Ateet handle stress and pressure?"),
    (re.compile(r"\b(decision|decide|judgment)\b", re.I),
     "What is Ateet's decision-making style?"),
    (re.compile(r"\b(problem.?solv|debug|troubleshoot)\b", re.I),
     "How does Ateet approach problem-solving and debugging?"),
    (re.compile(r"\b(automat|efficien|productiv)\b", re.I),
     "How does Ateet approach automation and efficiency?"),
    (re.compile(r"\b(innovat|creativ|experiment)\b", re.I),
     "What is Ateet's approach to innovation and experimentation?"),
    (re.compile(r"\b(ethic|responsible|trust|guardrail)\b", re.I),
     "What is Ateet's view on AI ethics and responsible AI?"),

    # ── Vision / Goals / Future ─────────────────────────────────────
    (re.compile(r"\b(vision|goal|future|plan|ambition|aspir)\b", re.I),
     "What is Ateet's vision and future goals?"),
    (re.compile(r"\b(focus|current|working\s*on|building)\b", re.I),
     "What is Ateet currently focused on and building?"),
    (re.compile(r"\b(pivot|transition|career\s*change|switch)\b", re.I),
     "Why did Ateet pivot from traditional software to AI engineering?"),

    # ── Hiring / Interview ──────────────────────────────────────────
    (re.compile(r"\b(hir|interview|recruit|looking\s*for|availab|open\s*to)\b", re.I),
     "Is Ateet available for hire? What roles is he targeting?"),
    (re.compile(r"\b(salary|compensat|rate|freelance\s*rate)\b", re.I),
     "What kind of roles and engagements is Ateet looking for?"),
    (re.compile(r"\b(remote|onsite|hybrid|reloca)\b", re.I),
     "Is Ateet open to remote, hybrid, or on-site work? Would he relocate?"),
    (re.compile(r"\b(why\s*hire|why\s*choose|why\s*ateet|value\s*add)\b", re.I),
     "Why should someone hire Ateet? What value does he bring?"),

    # ── Architecture / Design ───────────────────────────────────────
    (re.compile(r"\b(architect|design\s*pattern|system\s*design|scalab)\b", re.I),
     "What is Ateet's experience with software architecture and system design?"),
    (re.compile(r"\b(document|spec|prd|tech\s*spec)\b", re.I),
     "How does Ateet approach documentation and technical specs?"),

    # ── Achievements / Results ──────────────────────────────────────
    (re.compile(r"\b(achiev|accomplish|result|impact|success)\b", re.I),
     "What are Ateet's key achievements and career accomplishments?"),
    (re.compile(r"\b(award|recogni|honor)\b", re.I),
     "Has Ateet received any awards or recognition?"),

    # ── AI-specific topics ──────────────────────────────────────────
    (re.compile(r"\b(ai|artificial\s*intellig|machine\s*learn|ml|deep\s*learn)\b", re.I),
     "What is Ateet's AI and machine learning experience?"),
    (re.compile(r"\b(prompt|prompt\s*eng|injection)\b", re.I),
     "What is Ateet's experience with prompt engineering and security?"),
    (re.compile(r"\b(agent|agentic|autonomous)\b", re.I),
     "What is Ateet's experience building agentic and autonomous AI systems?"),
    (re.compile(r"\b(tts|stt|speech|voice)\b", re.I),
     "What is Ateet's experience with speech and voice AI technologies?"),

    # ── Work style / Process ────────────────────────────────────────
    (re.compile(r"\b(agile|scrum|kanban|sprint)\b", re.I),
     "What development methodologies does Ateet follow?"),
    (re.compile(r"\b(code\s*review|testing|quality|tdd)\b", re.I),
     "What is Ateet's approach to code quality, testing, and reviews?"),
    (re.compile(r"\b(learn|upskill|self.?taught|keep\s*up)\b", re.I),
     "How does Ateet keep learning and stay up to date with technology?"),
]


# ---------------------------------------------------------------------------
# LLM-based fallback rewriter
# ---------------------------------------------------------------------------

_REWRITE_SYSTEM_PROMPT = (
    "You are a query rewriter. The user is visiting Ateet Vatan Bahmani's "
    "AI portfolio assistant. Their input is short, vague, or misspelled.\n\n"
    "Your ONLY job: rewrite it into a single, clear, retrieval-friendly "
    "question about Ateet.\n\n"
    "Rules:\n"
    "- Output ONLY the rewritten question, nothing else.\n"
    "- Keep it under 25 words.\n"
    "- Correct any spelling mistakes.\n"
    "- If the input is a greeting or casual message (hi, hello, hey, etc.), "
    "return it UNCHANGED.\n"
    "- Always frame the question around Ateet's background, career, skills, "
    "projects, or experience."
)


def expand_query_regex(user_text: str) -> Optional[str]:
    """Try regex-based expansion. Returns expanded query or None."""
    for pattern, expansion in QUERY_EXPANSIONS:
        if pattern.search(user_text):
            return expansion
    return None


async def expand_query_llm(user_text: str, llm) -> str:
    """Use a lightweight LLM call to rewrite a short query.

    Args:
        user_text: The raw user input.
        llm:       A LangChain BaseChatModel (DeepSeek / Mistral / etc.).

    Returns:
        The rewritten query string (or original if LLM fails).
    """
    try:
        from langchain_core.messages import SystemMessage, HumanMessage

        response = llm.invoke([
            SystemMessage(content=_REWRITE_SYSTEM_PROMPT),
            HumanMessage(content=user_text),
        ])

        rewritten = (
            response.content.strip()
            if hasattr(response, "content")
            else str(response).strip()
        )

        # Sanity: if LLM returned empty or excessively long, keep original
        if not rewritten or len(rewritten) > 200:
            return user_text

        logger.info("LLM query rewrite: '%s' → '%s'", user_text, rewritten)
        return rewritten

    except Exception as e:
        logger.warning("LLM query rewrite failed, using original: %s", e)
        return user_text


async def expand_query(user_text: str, llm=None) -> str:
    """Hybrid query expansion: regex first, then LLM fallback.

    Args:
        user_text: Raw user input.
        llm:       Optional LangChain chat model for fallback rewrites.

    Returns:
        Expanded (or original) query string.
    """
    words = user_text.strip().split()

    # Already a full question — skip expansion
    if len(words) >= 5:
        return user_text

    # 1. Try regex (instant, free)
    regex_result = expand_query_regex(user_text)
    if regex_result:
        logger.info("Query expanded (regex): '%s' → '%s'", user_text, regex_result)
        return regex_result

    # 2. LLM fallback for unmatched short queries
    if llm is not None:
        return await expand_query_llm(user_text, llm)

    # No LLM available — return as-is
    return user_text
