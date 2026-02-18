"""
Pre-build text + audio cache for all 140 EchoAI questions.

This script:
1. Initialises the LangChain RAG agent (vectorstore + LLMs + reply cache)
2. For each question, generates a text answer via the RAG pipeline
3. Synthesises audio via Edge-TTS
4. Stores both in the reply cache (SQLite + Chroma) and audio cache (MP3 files)

Run:  python prebuild_cache.py
"""

import os
import sys
import time
import hashlib
import asyncio

# Suppress noisy warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from src.utils import get_settings, get_logger

settings = get_settings()
logger = get_logger(__name__)

# ── Voice to use (must match production) ──────────────────────────────
TTS_VOICE = "en-US-AndrewMultilingualNeural"

# ── All 140 questions (from questions.md) ─────────────────────────────
QUESTIONS = [
    # Identity & Bio (1-8)
    "What is your name?",
    "What is your full name?",
    "Where are you located?",
    "What is your professional title?",
    "Give me a short bio or introduction.",
    "What is your date of birth?",
    "What languages do you speak?",
    "What is your LinkedIn headline?",
    # Contact & Links (9-15)
    "What is your LinkedIn profile?",
    "What is your GitHub profile?",
    "What is your portfolio website?",
    "What is your email address?",
    "How can someone contact you or connect with you?",
    "What is the MASX AI website?",
    "What is your blog URL?",
    # Projects & Portfolio (16-34)
    "What are your featured projects?",
    "Tell me about MASX AI.",
    "Tell me about EchoAI.",
    "Tell me about AgenticMatch.",
    "What is the MASX-Forecasting project?",
    "What is the MASX-GeoSignal project?",
    "What is the MASX-Hotspots project?",
    "What is the ApplyBots project?",
    "What is the Galileo project?",
    "What is the ShotGraph project?",
    "What is the MedAI project?",
    "How many projects have you built?",
    "What is the MASX AI ecosystem?",
    "What are the key GitHub repositories?",
    "Where can I find your open-source repositories?",
    "What are the MASX-Forecasting doctrine agents?",
    "What agents does MASX-Hotspots use?",
    "How does the ApplyBots Truth-Lock Technology work?",
    "What data sources does MASX AI integrate?",
    # Skills & Tech Stack (35-52)
    "What is your full tech stack?",
    "What AI and LLM frameworks do you use?",
    "What programming languages do you know?",
    "What vector databases do you use?",
    "What LLM providers have you integrated?",
    "What prompt engineering techniques do you use?",
    "What databases do you work with?",
    "What DevOps and deployment tools do you use?",
    "What web frameworks do you use?",
    "What NLP and text processing capabilities do you have?",
    "What GIS and geospatial skills do you have?",
    "What testing and quality tools do you use?",
    "What are your complete LinkedIn skills?",
    "What async and concurrency tools do you use?",
    "What architectural patterns do you use in your projects?",
    "What cost optimization strategies do you use in AI systems?",
    "What security and compliance features do you implement?",
    "What methodologies do you follow?",
    # Career & Work Experience (53-70)
    "What is your career timeline?",
    "What is your education background?",
    "What was your role at 12IQ?",
    "What did you accomplish at 12IQ?",
    "What was your role at Pitney Bowes Software?",
    "What did you accomplish at IHS Markit as Senior Software Engineer?",
    "What did you accomplish at IHS Markit as Software Engineer?",
    "What is your complete work experience timeline?",
    "What is your educational background?",
    "What did you study at Masterschool?",
    "What certifications do you hold?",
    "What industries have you worked in?",
    "Biggest achievement in automotive?",
    "Biggest career risk taken?",
    "How did you transition to AI?",
    "What was your first professional role?",
    "How have your roles evolved?",
    "What IHS Markit projects did you develop?",
    # Career Philosophy & Work Style (71-89)
    "How do you approach problem-solving?",
    "How do you ensure code quality?",
    "How do you handle failure?",
    "How do you prioritize tasks?",
    "How do you manage deadlines?",
    "How do you handle disagreements?",
    "What is your decision-making style?",
    "What is your leadership style?",
    "What is your learning style?",
    "How do you approach documentation?",
    "How do you balance build vs. buy?",
    "How do you decide on tech stack?",
    "What's your approach to technical debt?",
    "How do you prevent scope creep?",
    "How do you manage remote teams?",
    "Do you mentor juniors?",
    "What is your personal mantra?",
    "What is your preferred work environment?",
    "What is your current focus?",
    # HR & Interview (90-104)
    "Tell me about yourself.",
    "Walk me through your CV.",
    "What is your greatest strength?",
    "What is your biggest weakness?",
    "Where do you see yourself in 5 years?",
    "Why should we hire you?",
    "What motivates you at work?",
    "Describe a challenging project and how you handled it.",
    "Tell me about a time you worked under pressure.",
    "Have you ever failed in a project?",
    "What are your salary expectations?",
    "Why are you leaving your current position?",
    "How do you handle criticism?",
    "What is your preferred work culture?",
    "What would your previous manager say about you?",
    # Personality & Lifestyle (105-119)
    "Describe your personality in three words.",
    "How are you feeling today?",
    "What motivates you most?",
    "What values guide your decisions?",
    "What are your hobbies?",
    "Do you exercise?",
    "How do you manage work-life balance?",
    "What is your daily routine structure?",
    "What are your preferred working hours?",
    "How do you relax?",
    "What is your weekend routine?",
    "How do you handle high-pressure situations?",
    "How do you react to mistakes?",
    "What is your core strength?",
    "What is your dominant thinking style?",
    # Vision & Strategy (120-135)
    "Where do you see yourself in 10 years?",
    "What is your 5-year career goal?",
    "What is your MASX AI vision for 2024-2025?",
    "What is your global vision for AI?",
    "What is your AI ethics stance?",
    "Should AI be regulated?",
    "What is the role of AI in society?",
    "Will AI replace human decision-makers?",
    "What is your biggest dream project?",
    "What is your biggest fear for AI misuse?",
    "What is the core mission of MASX AI?",
    "What differentiates MASX AI?",
    "What legacy do you want to leave?",
    "What is your long-term project vision?",
    "What is your personal philosophy in AI work?",
    "What is your definition of success in the next decade?",
    # Casual / Conversational (136-140)
    "Hi! How's your day going so far?",
    "Good morning, ready for today's challenges?",
    "Anything exciting you're working on today?",
    "What's been on your mind since our last chat?",
    "What's the highlight of your day so far?",
]


def _deterministic_audio_path(question: str) -> str:
    """Generate a deterministic audio file path based on the question text."""
    q_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()[:12]
    return os.path.join("audio_cache", f"prebuild_{q_hash}.mp3")


async def main():
    print("=" * 70)
    print("EchoAI — Pre-Build Text + Audio Cache")
    print(f"  Voice : {TTS_VOICE}")
    print(f"  Questions: {len(QUESTIONS)}")
    print("=" * 70)

    # ── Step 1: Initialise RAG agent ──────────────────────────────────
    print("\n[1/3] Initialising LangChain RAG Agent...")
    from src.agents.langchain_rag_agent import get_rag_agent
    agent = get_rag_agent()
    print("  ✓ RAG agent ready")

    # ── Step 2: Initialise TTS service ────────────────────────────────
    print("[2/3] Initialising TTS service...")
    from src.services.tts_service import tts_service
    print(f"  ✓ TTS service ready (voice={TTS_VOICE})")

    # ── Step 3: Process all questions ─────────────────────────────────
    print(f"\n[3/3] Processing {len(QUESTIONS)} questions...\n")

    successes = 0
    skipped = 0
    failures = 0
    total_start = time.time()

    for i, question in enumerate(QUESTIONS, 1):
        audio_path = _deterministic_audio_path(question)

        try:
            # Check if already cached in reply cache (idempotent)
            existing = await agent.reply_cache.find_similar_reply(question)
            if existing and existing.similarity_score >= 0.99:
                # Also check the audio file exists
                if os.path.exists(existing.audio_file_path):
                    skipped += 1
                    print(f"  [SKIP] Q{i:3d} {question[:55]}")
                    continue

            # ── Generate text response via RAG ────────────────────────
            rag_result = await agent.process_query(question, session_id=None)
            response_text = rag_result.get("response_text", "")

            if not response_text or "error" in rag_result:
                failures += 1
                err = rag_result.get("error", "empty response")
                print(f"  [FAIL] Q{i:3d} {question[:55]}")
                print(f"         RAG error: {err}")
                continue

            # ── Generate audio via TTS ────────────────────────────────
            tts_result = await tts_service.synthesize_speech(
                response_text, use_streaming=False, voice=TTS_VOICE
            )

            if "error" in tts_result or not tts_result.get("audio_data"):
                failures += 1
                print(f"  [FAIL] Q{i:3d} {question[:55]}")
                print(f"         TTS error: {tts_result.get('error', 'no audio')}")
                continue

            audio_data = tts_result["audio_data"]

            # ── Save audio file at deterministic path ─────────────────
            os.makedirs("audio_cache", exist_ok=True)
            with open(audio_path, "wb") as f:
                f.write(audio_data)

            # ── Store in reply cache (SQLite + Chroma) ────────────────
            await agent.reply_cache.store_reply(
                question, response_text, audio_path
            )

            successes += 1
            size_kb = len(audio_data) / 1024
            print(f"  [ OK ] Q{i:3d} {question[:55]} ({size_kb:.0f} KB)")

        except Exception as e:
            failures += 1
            print(f"  [FAIL] Q{i:3d} {question[:55]}")
            print(f"         Error: {str(e)[:100]}")

        # Small delay between API calls to avoid rate limits
        await asyncio.sleep(0.3)

    elapsed = time.time() - total_start

    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"DONE in {elapsed:.1f}s")
    print(f"  ✓ Success: {successes}")
    print(f"  ⊘ Skipped: {skipped} (already cached)")
    print(f"  ✗ Failed : {failures}")
    print(f"{'=' * 70}")

    # Count total cache files
    mp3_count = len([f for f in os.listdir("audio_cache") if f.endswith(".mp3")])
    print(f"\nTotal audio files in audio_cache/: {mp3_count}")

    if failures > 0:
        print("\n⚠  Some questions failed. Re-run the script to retry them.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
