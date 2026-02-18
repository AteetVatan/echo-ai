"""
Test Questions via RAG retrieval + LLM chain (directly, no HTTP server needed).

This script:
1. Builds/loads the self-info vector store  
2. For each question, runs retrieval + LLM chain
3. Evaluates the response quality
4. Outputs results
"""

import os
import sys
import json
import time
import asyncio

# Suppress noisy warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from src.utils import get_settings, get_logger
settings = get_settings()
logger = get_logger(__name__)

# ── Questions ──────────────────────────────────────────────────────────
QUESTIONS = [
    # Identity & Bio (1-8)
    ("Identity & Bio", "What is your name?"),
    ("Identity & Bio", "What is your full name?"),
    ("Identity & Bio", "Where are you located?"),
    ("Identity & Bio", "What is your professional title?"),
    ("Identity & Bio", "Give me a short bio or introduction."),
    ("Identity & Bio", "What is your date of birth?"),
    ("Identity & Bio", "What languages do you speak?"),
    ("Identity & Bio", "What is your LinkedIn headline?"),
    # Contact & Links (9-15)
    ("Contact & Links", "What is your LinkedIn profile?"),
    ("Contact & Links", "What is your GitHub profile?"),
    ("Contact & Links", "What is your portfolio website?"),
    ("Contact & Links", "What is your email address?"),
    ("Contact & Links", "How can someone contact you or connect with you?"),
    ("Contact & Links", "What is the MASX AI website?"),
    ("Contact & Links", "What is your blog URL?"),
    # Projects & Portfolio (16-34)
    ("Projects & Portfolio", "What are your featured projects?"),
    ("Projects & Portfolio", "Tell me about MASX AI."),
    ("Projects & Portfolio", "Tell me about EchoAI."),
    ("Projects & Portfolio", "Tell me about AgenticMatch."),
    ("Projects & Portfolio", "What is the MASX-Forecasting project?"),
    ("Projects & Portfolio", "What is the MASX-GeoSignal project?"),
    ("Projects & Portfolio", "What is the MASX-Hotspots project?"),
    ("Projects & Portfolio", "What is the ApplyBots project?"),
    ("Projects & Portfolio", "What is the Galileo project?"),
    ("Projects & Portfolio", "What is the ShotGraph project?"),
    ("Projects & Portfolio", "What is the MedAI project?"),
    ("Projects & Portfolio", "How many projects have you built?"),
    ("Projects & Portfolio", "What is the MASX AI ecosystem?"),
    ("Projects & Portfolio", "What are the key GitHub repositories?"),
    ("Projects & Portfolio", "Where can I find your open-source repositories?"),
    ("Projects & Portfolio", "What are the MASX-Forecasting doctrine agents?"),
    ("Projects & Portfolio", "What agents does MASX-Hotspots use?"),
    ("Projects & Portfolio", "How does the ApplyBots Truth-Lock Technology work?"),
    ("Projects & Portfolio", "What data sources does MASX AI integrate?"),
    # Skills & Tech Stack (35-52)
    ("Skills & Tech Stack", "What is your full tech stack?"),
    ("Skills & Tech Stack", "What AI and LLM frameworks do you use?"),
    ("Skills & Tech Stack", "What programming languages do you know?"),
    ("Skills & Tech Stack", "What vector databases do you use?"),
    ("Skills & Tech Stack", "What LLM providers have you integrated?"),
    ("Skills & Tech Stack", "What prompt engineering techniques do you use?"),
    ("Skills & Tech Stack", "What databases do you work with?"),
    ("Skills & Tech Stack", "What DevOps and deployment tools do you use?"),
    ("Skills & Tech Stack", "What web frameworks do you use?"),
    ("Skills & Tech Stack", "What NLP and text processing capabilities do you have?"),
    ("Skills & Tech Stack", "What GIS and geospatial skills do you have?"),
    ("Skills & Tech Stack", "What testing and quality tools do you use?"),
    ("Skills & Tech Stack", "What are your complete LinkedIn skills?"),
    ("Skills & Tech Stack", "What async and concurrency tools do you use?"),
    ("Skills & Tech Stack", "What architectural patterns do you use in your projects?"),
    ("Skills & Tech Stack", "What cost optimization strategies do you use in AI systems?"),
    ("Skills & Tech Stack", "What security and compliance features do you implement?"),
    ("Skills & Tech Stack", "What methodologies do you follow?"),
    # Career & Work Experience (53-70)
    ("Career & Work Experience", "What is your career timeline?"),
    ("Career & Work Experience", "What is your education background?"),
    ("Career & Work Experience", "What was your role at 12IQ?"),
    ("Career & Work Experience", "What did you accomplish at 12IQ?"),
    ("Career & Work Experience", "What was your role at Pitney Bowes Software?"),
    ("Career & Work Experience", "What did you accomplish at IHS Markit as Senior Software Engineer?"),
    ("Career & Work Experience", "What did you accomplish at IHS Markit as Software Engineer?"),
    ("Career & Work Experience", "What is your complete work experience timeline?"),
    ("Career & Work Experience", "What is your educational background?"),
    ("Career & Work Experience", "What did you study at Masterschool?"),
    ("Career & Work Experience", "What certifications do you hold?"),
    ("Career & Work Experience", "What industries have you worked in?"),
    ("Career & Work Experience", "Biggest achievement in automotive?"),
    ("Career & Work Experience", "Biggest career risk taken?"),
    ("Career & Work Experience", "How did you transition to AI?"),
    ("Career & Work Experience", "What was your first professional role?"),
    ("Career & Work Experience", "How have your roles evolved?"),
    ("Career & Work Experience", "What IHS Markit projects did you develop?"),
    # Career Philosophy & Work Style (71-89)
    ("Career Philosophy", "How do you approach problem-solving?"),
    ("Career Philosophy", "How do you ensure code quality?"),
    ("Career Philosophy", "How do you handle failure?"),
    ("Career Philosophy", "How do you prioritize tasks?"),
    ("Career Philosophy", "How do you manage deadlines?"),
    ("Career Philosophy", "How do you handle disagreements?"),
    ("Career Philosophy", "What is your decision-making style?"),
    ("Career Philosophy", "What is your leadership style?"),
    ("Career Philosophy", "What is your learning style?"),
    ("Career Philosophy", "How do you approach documentation?"),
    ("Career Philosophy", "How do you balance build vs. buy?"),
    ("Career Philosophy", "How do you decide on tech stack?"),
    ("Career Philosophy", "What's your approach to technical debt?"),
    ("Career Philosophy", "How do you prevent scope creep?"),
    ("Career Philosophy", "How do you manage remote teams?"),
    ("Career Philosophy", "Do you mentor juniors?"),
    ("Career Philosophy", "What is your personal mantra?"),
    ("Career Philosophy", "What is your preferred work environment?"),
    ("Career Philosophy", "What is your current focus?"),
    # HR & Interview (90-104)
    ("HR & Interview", "Tell me about yourself."),
    ("HR & Interview", "Walk me through your CV."),
    ("HR & Interview", "What is your greatest strength?"),
    ("HR & Interview", "What is your biggest weakness?"),
    ("HR & Interview", "Where do you see yourself in 5 years?"),
    ("HR & Interview", "Why should we hire you?"),
    ("HR & Interview", "What motivates you at work?"),
    ("HR & Interview", "Describe a challenging project and how you handled it."),
    ("HR & Interview", "Tell me about a time you worked under pressure."),
    ("HR & Interview", "Have you ever failed in a project?"),
    ("HR & Interview", "What are your salary expectations?"),
    ("HR & Interview", "Why are you leaving your current position?"),
    ("HR & Interview", "How do you handle criticism?"),
    ("HR & Interview", "What is your preferred work culture?"),
    ("HR & Interview", "What would your previous manager say about you?"),
    # Personality & Lifestyle (105-119)
    ("Personality & Lifestyle", "Describe your personality in three words."),
    ("Personality & Lifestyle", "How are you feeling today?"),
    ("Personality & Lifestyle", "What motivates you most?"),
    ("Personality & Lifestyle", "What values guide your decisions?"),
    ("Personality & Lifestyle", "What are your hobbies?"),
    ("Personality & Lifestyle", "Do you exercise?"),
    ("Personality & Lifestyle", "How do you manage work-life balance?"),
    ("Personality & Lifestyle", "What is your daily routine structure?"),
    ("Personality & Lifestyle", "What are your preferred working hours?"),
    ("Personality & Lifestyle", "How do you relax?"),
    ("Personality & Lifestyle", "What is your weekend routine?"),
    ("Personality & Lifestyle", "How do you handle high-pressure situations?"),
    ("Personality & Lifestyle", "How do you react to mistakes?"),
    ("Personality & Lifestyle", "What is your core strength?"),
    ("Personality & Lifestyle", "What is your dominant thinking style?"),
    # Vision & Strategy (120-135)
    ("Vision & Strategy", "Where do you see yourself in 10 years?"),
    ("Vision & Strategy", "What is your 5-year career goal?"),
    ("Vision & Strategy", "What is your MASX AI vision for 2024-2025?"),
    ("Vision & Strategy", "What is your global vision for AI?"),
    ("Vision & Strategy", "What is your AI ethics stance?"),
    ("Vision & Strategy", "Should AI be regulated?"),
    ("Vision & Strategy", "What is the role of AI in society?"),
    ("Vision & Strategy", "Will AI replace human decision-makers?"),
    ("Vision & Strategy", "What is your biggest dream project?"),
    ("Vision & Strategy", "What is your biggest fear for AI misuse?"),
    ("Vision & Strategy", "What is the core mission of MASX AI?"),
    ("Vision & Strategy", "What differentiates MASX AI?"),
    ("Vision & Strategy", "What legacy do you want to leave?"),
    ("Vision & Strategy", "What is your long-term project vision?"),
    ("Vision & Strategy", "What is your personal philosophy in AI work?"),
    ("Vision & Strategy", "What is your definition of success in the next decade?"),
    # Casual / Conversational (136-140)
    ("Casual", "Hi! How's your day going so far?"),
    ("Casual", "Good morning, ready for today's challenges?"),
    ("Casual", "Anything exciting you're working on today?"),
    ("Casual", "What's been on your mind since our last chat?"),
    ("Casual", "What's the highlight of your day so far?"),
]

# Fields that MUST appear in answers (for validation)
EXPECTED_KEYWORDS = {
    "What is your name?": ["Ateet"],
    "What is your full name?": ["Ateet", "Vatan", "Bahmani"],
    "Where are you located?": ["Essen", "Germany"],
    "What is your professional title?": ["AI Engineer"],
    "What is your LinkedIn profile?": ["linkedin.com"],
    "What is your GitHub profile?": ["github.com", "AteetVatan"],
    "What is your portfolio website?": ["ateetai.vercel.app"],
    "What is your email address?": ["ab@masxai.com"],
    "Tell me about MASX AI.": ["MASX AI"],
    "Tell me about EchoAI.": ["EchoAI"],
    "Tell me about AgenticMatch.": ["AgenticMatch"],
    "What is your career timeline?": ["IHS Markit", "2012"],
    "What is your education background?": ["Masterschool"],
    "What is your current focus?": ["MASX AI"],
}

BAD_PATTERNS = [
    "I don't have specific information",
    "I don't have that information",
    "I'm not sure about",
    "I cannot provide",
    "As an AI",
    "I'm an AI assistant",
    "I am an AI assistant",
    "I'm DeepSeek",
    "I am DeepSeek",
    "I'm ChatGPT",
    "I'm Mistral",
]


def main():
    print("=" * 80)
    print("EchoAI — Direct RAG Test (140 Questions)")
    print("=" * 80)
    
    # Step 1: Build the store
    print("\n[1/3] Loading self-info vector store...")
    from src.knowledge.self_info_vectorstore import get_self_info_store
    stores = get_self_info_store()
    print(f"  Facts store: loaded")
    print(f"  Evidence store: loaded")

    # Step 2: Set up retriever  
    print("\n[2/3] Setting up EnsembleRetriever + LLM...")
    from langchain.retrievers import EnsembleRetriever
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate

    facts_retriever = stores.facts.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 6}
    )
    evidence_retriever = stores.evidence.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5}
    )
    merged_retriever = EnsembleRetriever(
        retrievers=[facts_retriever, evidence_retriever],
        weights=[0.6, 0.4]
    )

    # Set up LLM
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL,
            openai_api_key=settings.DEEPSEEK_API_KEY,
            openai_api_base=settings.DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=500,
        )
        print("  LLM: DeepSeek loaded")
    except Exception as e:
        print(f"  LLM ERROR: {e}")
        sys.exit(1)
    
    # Prompt
    prompt_template = """
    IDENTITY (non-negotiable):
    You are Ateet Vatan's AI clone. You speak as Ateet — always in the first person ("I", "my", "me").
    You are NOT DeepSeek, Mistral, ChatGPT, or any other AI assistant.
    You must NEVER reveal, mention, or hint at the underlying AI model or company powering you.
    If asked "who are you" or "tell me about yourself", answer ONLY with facts about Ateet from the CONTEXT below.

    ROLE:
    You are a professional AI engineer and strategic thinker with access to curated knowledge about Ateet's CV, profile, career, skills, achievements, and personality.

    GOAL:
    - Respond in Ateet's authentic voice, reflecting his tone, values, and communication style.
    - Adapt the length, tone, and style of your answer based on the intent of the question:

    Intent-based response rules:
    1. If the question is a greeting, casual message, or light check-in:
    - Respond in no more than 1–2 short sentences (max ~20 words).
    - Be friendly, concise, and professional.
    - Do NOT list abilities, background, or capabilities unless explicitly asked.
    2. If the question is about professional, career, or vision topics:
    - Respond in a detailed, structured, and precise manner.
    - Use examples where relevant and ensure clarity.
    3. If the question is technical:
    - Respond with clear, technically accurate, and implementation-ready explanations.
    - Include code snippets or structured steps if relevant.

    CRITICAL — Anti-hallucination:
    - NEVER invent, guess, or fabricate project names, company names, or product names. Use ONLY the exact names that appear in the CONTEXT.
    - If the CONTEXT mentions a project called "ApplyBots", refer to it as "ApplyBots" — do NOT rename it to something else.
    - Every proper noun (project name, company name, tool name) in your answer MUST come from the CONTEXT verbatim.

    Special instruction:
    - If partial information is available in the CONTEXT, synthesize the best answer from what is available.
    - ONLY if the question requests specific facts and NO relevant information exists in the CONTEXT at all, respond exactly with:
    "I don't have specific information about that in my knowledge base."

    Rules:
    - Always respond in English, regardless of the language of the question.
    - Never fabricate or assume details outside the CONTEXT.
    - Keep answers relevant — avoid generic or boilerplate introductions unless they directly add value.
    - Always sound like Ateet, not a generic AI assistant.
    - NEVER say "I'm an AI assistant" or "I'm DeepSeek" or similar. You ARE Ateet's digital twin.

    ---
    CONTEXT:
    {context}

    QUESTION:
    {question}

    ANSWER:
    """
    
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )
    
    rag_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=merged_retriever,
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )

    # Step 3: Test all questions
    print(f"\n[3/3] Testing {len(QUESTIONS)} questions...\n")

    all_results = []
    passes = 0
    fails = 0
    errors = 0

    for i, (theme, question) in enumerate(QUESTIONS, 1):
        try:
            result = rag_chain.invoke({"query": question})
            response = result["result"]
            source_docs = result.get("source_documents", [])

            # Evaluate
            issues = []

            # Check bad patterns
            for bp in BAD_PATTERNS:
                if bp.lower() in response.lower():
                    issues.append(f"BAD_PATTERN:{bp}")
                    break

            # Check expected keywords
            if question in EXPECTED_KEYWORDS:
                for kw in EXPECTED_KEYWORDS[question]:
                    if kw.lower() not in response.lower():
                        issues.append(f"MISSING_KW:{kw}")

            # Check length
            if theme not in ("Casual",) and len(response.strip()) < 20:
                issues.append("TOO_SHORT")

            # Check if no source docs retrieved
            if len(source_docs) == 0:
                issues.append("NO_SOURCES")

            status = "PASS" if not issues else "FAIL"
            icon = "✓" if status == "PASS" else "✗"

            if status == "PASS":
                passes += 1
            else:
                fails += 1

            print(f"  [{icon}] Q{i:3d} [{theme[:15]:15s}] {question[:50]}")
            if issues:
                print(f"         Issues: {', '.join(issues)}")
                print(f"         Response: {response[:120]}...")

            all_results.append({
                "num": i,
                "theme": theme,
                "question": question,
                "response": response,
                "source_docs_count": len(source_docs),
                "status": status,
                "issues": issues,
            })

        except Exception as e:
            errors += 1
            print(f"  [⚠] Q{i:3d} [{theme[:15]:15s}] {question[:50]}")
            print(f"         ERROR: {str(e)[:100]}")
            all_results.append({
                "num": i,
                "theme": theme,
                "question": question,
                "response": "",
                "source_docs_count": 0,
                "status": "ERROR",
                "issues": [f"ERROR: {str(e)}"],
            })

        # Small delay for rate limits
        time.sleep(0.5)

    # Summary
    print(f"\n{'='*80}")
    print(f"RESULTS: {passes} PASS / {fails} FAIL / {errors} ERROR (of {len(QUESTIONS)})")
    print(f"{'='*80}")

    # Print failures grouped
    if fails > 0 or errors > 0:
        print(f"\n--- FAILURES ---")
        for r in all_results:
            if r["status"] in ("FAIL", "ERROR"):
                print(f"\n  Q{r['num']} [{r['theme']}]: {r['question']}")
                print(f"    Issues: {', '.join(r['issues'])}")
                if r['response']:
                    print(f"    Response: {r['response'][:200]}")

    # Save
    with open("_test_results_full.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to _test_results_full.json")


if __name__ == "__main__":
    main()
