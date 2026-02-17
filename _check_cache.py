"""Check reply cache for stale/wrong responses and test RAG retrieval."""
import sqlite3
import sys

# 1) Check reply cache
print("=" * 60)
print("REPLY CACHE CHECK")
print("=" * 60)
try:
    conn = sqlite3.connect("src/db/audio_cache.db")
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables: {[t[0] for t in tables]}")
    
    if any(t[0] == "reply_cache" for t in tables):
        cursor2 = conn.execute("SELECT COUNT(*) FROM reply_cache")
        count = cursor2.fetchone()[0]
        print(f"Reply cache rows: {count}")
        
        cursor3 = conn.execute("SELECT user_text, response_text FROM reply_cache")
        for row in cursor3.fetchall():
            q = row[0][:100]
            a = row[1][:200]
            has_jobsync = "JobSync" in row[1]
            print(f"\n  Q: {q}")
            print(f"  A: {a}...")
            if has_jobsync:
                print(f"  *** CONTAINS 'JobSync' - THIS IS THE PROBLEM ***")
    conn.close()
except Exception as e:
    print(f"Error: {e}")

# 2) Test RAG retrieval for "work experience"
print("\n" + "=" * 60)
print("RAG RETRIEVAL TEST")
print("=" * 60)
try:
    from src.utils import get_settings
    settings = get_settings()
    
    from src.knowledge.self_info_vectorstore import get_self_info_store
    stores = get_self_info_store()
    
    query = "Tell me about your work experience"
    print(f"\nQuery: '{query}'")
    
    print("\n--- Facts Store Results ---")
    facts_results = stores.facts.similarity_search(query, k=5)
    for i, doc in enumerate(facts_results):
        content = doc.page_content[:200]
        has_applybots = "ApplyBots" in doc.page_content
        has_jobsync = "JobSync" in doc.page_content
        print(f"  [{i+1}] {'✓ ApplyBots' if has_applybots else '✗ No ApplyBots'} | {'!!! JobSync' if has_jobsync else 'OK'}")
        print(f"      {content}...")
    
    print("\n--- Evidence Store Results ---")
    evidence_results = stores.evidence.similarity_search(query, k=5)
    for i, doc in enumerate(evidence_results):
        content = doc.page_content[:200]
        has_applybots = "ApplyBots" in doc.page_content
        has_jobsync = "JobSync" in doc.page_content
        print(f"  [{i+1}] {'✓ ApplyBots' if has_applybots else '✗ No ApplyBots'} | {'!!! JobSync' if has_jobsync else 'OK'}")
        print(f"      {content}...")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
