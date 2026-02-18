"""
Rebuild the Self-Info vector store from scratch.

Deletes the persisted Chroma directory and re-embeds all facts + evidence.
Usage:
    python rebuild_self_info.py
"""

import shutil
from pathlib import Path

from src.utils import get_settings, get_logger
from src.knowledge.self_info_vectorstore import (
    build_or_update_self_info_store,
    _store_lock,
)
import src.knowledge.self_info_vectorstore as _mod

logger = get_logger(__name__)


def main():
    settings = get_settings()
    persist_dir = Path(settings.SELF_INFO_CHROMA_DIR)

    # 1. Delete existing store
    if persist_dir.exists():
        print(f"Deleting existing store at {persist_dir} ...")
        shutil.rmtree(persist_dir)
        print("  Deleted.")
    else:
        print(f"No existing store at {persist_dir}, nothing to delete.")

    # 2. Reset the in-memory singleton so the next call rebuilds
    with _store_lock:
        _mod._store_instance = None

    # 3. Rebuild from scratch
    print("Rebuilding self-info store ...")
    stores = build_or_update_self_info_store()

    # 4. Report
    facts_count = stores.facts._collection.count()
    evidence_count = stores.evidence._collection.count()
    print(f"\nDone!")
    print(f"  Facts:    {facts_count} documents")
    print(f"  Evidence: {evidence_count} documents")
    print(f"  Stored at: {persist_dir}")


if __name__ == "__main__":
    main()
