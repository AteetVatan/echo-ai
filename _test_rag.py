"""Test RAG retrieval for work experience query."""
import sys
import os

# Suppress warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from src.utils import get_settings
settings = get_settings()

from pathlib import Path
from src.knowledge.self_info_vectorstore import build_or_update_self_info_store

print("Building store from disk...")
stores = build_or_update_self_info_store()

query = "Tell me about your work experience"
print(f"\nQuery: '{query}'\n")

print("--- Facts Store Top 5 ---")
facts_results = stores.facts.similarity_search(query, k=5)
for i, doc in enumerate(facts_results):
    content = doc.page_content[:300].replace("\n", " ")
    ab = "APPLYBOTS" if "ApplyBots" in doc.page_content else ""
    js = "JOBSYNC!" if "JobSync" in doc.page_content else ""
    print(f"[{i+1}] {ab} {js}")
    print(f"    {content}")
    print()

print("--- Evidence Store Top 5 ---")
evidence_results = stores.evidence.similarity_search(query, k=5)
for i, doc in enumerate(evidence_results):
    content = doc.page_content[:300].replace("\n", " ")
    ab = "APPLYBOTS" if "ApplyBots" in doc.page_content else ""
    js = "JOBSYNC!" if "JobSync" in doc.page_content else ""
    print(f"[{i+1}] {ab} {js}")
    print(f"    {content}")
    print()
