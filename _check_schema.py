import traceback
try:
    import chromadb
    client1 = chromadb.PersistentClient(path="src/db/chroma_db")
    cols1 = client1.list_collections()
    print("=== src/db/chroma_db ===")
    for c in cols1:
        count = c.count()
        print(f"  {c.name}: {count} vectors")
        if count > 0:
            sample = c.get(limit=1, include=["embeddings", "documents", "metadatas"])
            dim = len(sample["embeddings"][0]) if sample.get("embeddings") and sample["embeddings"] else "?"
            print(f"    dim={dim}")
            if sample.get("documents"):
                print(f"    doc[:80]: {sample['documents'][0][:80]}")
                print(f"    meta: {sample['metadatas'][0]}")

    client2 = chromadb.PersistentClient(path="src/db/self_info_knowledge_v2")
    cols2 = client2.list_collections()
    print("\n=== src/db/self_info_knowledge_v2 ===")
    for c in cols2:
        count = c.count()
        print(f"  {c.name}: {count} vectors")
        if count > 0:
            sample = c.get(limit=1, include=["embeddings", "documents", "metadatas"])
            dim = len(sample["embeddings"][0]) if sample.get("embeddings") and sample["embeddings"] else "?"
            print(f"    dim={dim}")
            if sample.get("metadatas"):
                print(f"    meta keys: {list(sample['metadatas'][0].keys())}")
except Exception:
    traceback.print_exc()
