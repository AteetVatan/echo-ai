"""
Test a single question via RAG retrieval + LLM chain.
Usage: python _test_single_q.py "What is your name?"
"""
import os, sys, time
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from src.utils import get_settings, get_logger
settings = get_settings()
logger = get_logger(__name__)

def test_question(question: str):
    print("=" * 80)
    print(f"Testing: {question}")
    print("=" * 80)

    # Step 1: Build the store
    print("\n[1/3] Loading self-info vector store...")
    from src.knowledge.self_info_vectorstore import get_self_info_store
    stores = get_self_info_store()
    print("  Stores loaded.")

    # Step 2: Set up retriever
    print("[2/3] Setting up EnsembleRetriever + LLM...")
    from langchain.retrievers import EnsembleRetriever
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate

    facts_retriever = stores.facts.as_retriever(search_type="similarity", search_kwargs={"k": 6})
    evidence_retriever = stores.evidence.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    merged_retriever = EnsembleRetriever(
        retrievers=[facts_retriever, evidence_retriever],
        weights=[0.6, 0.4]
    )

    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        openai_api_key=settings.DEEPSEEK_API_KEY,
        openai_api_base=settings.DEEPSEEK_BASE_URL,
        temperature=0.3,
        max_tokens=500,
    )

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

    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    rag_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=merged_retriever,
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )

    # Step 3: Test
    print(f"[3/3] Querying...\n")
    t0 = time.time()
    result = rag_chain.invoke({"query": question})
    elapsed = time.time() - t0

    response = result["result"]
    source_docs = result.get("source_documents", [])

    print(f"RESPONSE ({elapsed:.1f}s):")
    print("-" * 60)
    print(response)
    print("-" * 60)
    print(f"\nSource docs retrieved: {len(source_docs)}")
    for i, doc in enumerate(source_docs):
        print(f"  [{i}] {doc.page_content[:120]}...")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What is your name?"
    test_question(q)
