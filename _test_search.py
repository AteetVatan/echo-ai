"""Simulate the exact EnsembleRetriever used by the RAG chain."""
import warnings
warnings.filterwarnings("ignore")

from src.knowledge.self_info_vectorstore import get_self_info_store
from langchain.retrievers import EnsembleRetriever

stores = get_self_info_store()

facts_retriever = stores.facts.as_retriever(search_type="similarity", search_kwargs={"k": 6})
evidence_retriever = stores.evidence.as_retriever(search_type="similarity", search_kwargs={"k": 5})
merged_retriever = EnsembleRetriever(
    retrievers=[facts_retriever, evidence_retriever],
    weights=[0.6, 0.4]
)

query = "tell me about your work experience"
docs = merged_retriever.invoke(query)

lines = [f"Query: '{query}'", f"Total docs returned: {len(docs)}", "=" * 80]
for i, doc in enumerate(docs):
    content = doc.page_content.replace("\n", " ").replace("\r", " ")
    lines.append(f"\n[{i}] {content[:250]}")

output = "\n".join(lines)
with open("_test_ensemble.txt", "w", encoding="utf-8") as f:
    f.write(output)
print("Results written to _test_ensemble.txt")
