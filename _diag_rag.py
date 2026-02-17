"""Focused diagnostic: try to build the store directly."""
import traceback
import sys

print(f"Python: {sys.executable}")

# Step 1: Check settings
from src.utils import get_settings
settings = get_settings()
print(f"SELF_INFO_CHROMA_DIR: {settings.SELF_INFO_CHROMA_DIR}")

# Step 2: Try loading items
from pathlib import Path
from src.knowledge.self_info_loader import load_self_info_items
json_path = Path(settings.SELF_INFO_JSON_PATH)
print(f"JSON path exists: {json_path.exists()}")
items = load_self_info_items(json_path)
print(f"Loaded {len(items)} items from self_info.json")

# Step 3: Convert to documents
from src.knowledge.self_info_documents import to_langchain_documents
docs = to_langchain_documents(items)
print(f"Converted to {len(docs)} LangChain documents")

# Step 4: Try creating Chroma store from scratch
import os
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from src.constants import ChromaCollection

embeddings = SentenceTransformerEmbeddings(model_name=settings.EMBEDDING_MODEL)
persist_dir = settings.SELF_INFO_CHROMA_DIR
os.makedirs(persist_dir, exist_ok=True)
print(f"Persist dir: {persist_dir}")

try:
    store = Chroma(
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
        collection_name=ChromaCollection.SELF_INFO_FACTS,
        collection_metadata={"hnsw:space": "cosine"},
    )
    print("Chroma store created OK")
except Exception as e:
    print(f"Chroma creation failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 5: Try upsert
try:
    ids = [doc.metadata["stable_id"] for doc in docs[:5]]  # just first 5
    texts = [doc.page_content for doc in docs[:5]]
    metadatas = [doc.metadata for doc in docs[:5]]
    embs = embeddings.embed_documents(texts)
    store._collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embs)
    print(f"Upserted 5 docs OK")
except Exception as e:
    print(f"Upsert failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 6: Try search
try:
    results = store.similarity_search("work experience", k=2)
    print(f"Search returned {len(results)} results")
    for i, r in enumerate(results):
        print(f"  [{i+1}] {r.page_content[:150]}")
except Exception as e:
    print(f"Search failed: {e}")
    traceback.print_exc()
