"""
CLI utilities for Self-Info RAG.

Usage:
    python -m src.tools.self_info_cli build
    python -m src.tools.self_info_cli ask "What is your email address?"
    python -m src.tools.self_info_cli ask "Tell me about your CV" --index evidence
    python -m src.tools.self_info_cli ask "What are your skills?" --doc-type about_me --tag hr
"""

from __future__ import annotations

import argparse
import os
import sys


def _ensure_env():
    """Load .env and add project root to sys.path for imports."""
    # Ensure project root is on path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from dotenv import load_dotenv

    load_dotenv()


def cmd_build(args: argparse.Namespace) -> None:
    """Build or rebuild the self-info vector store."""
    _ensure_env()

    # Force rebuild if requested
    if args.rebuild:
        os.environ["SELF_INFO_REBUILD"] = "1"

    from src.knowledge.self_info_vectorstore import build_or_update_self_info_store

    print("Building self-info vector store...")
    build_or_update_self_info_store()

    print("\n✅ Build complete:")
    print("   Facts store:    ready (Supabase pgvector)")
    print("   Evidence store: ready (Supabase pgvector)")


def cmd_ask(args: argparse.Namespace) -> None:
    """Ask a question using the RAG chain."""
    _ensure_env()

    from src.knowledge.self_info_rag import answer_about_ateet

    question = args.question
    doc_type = args.doc_type
    tags = [t.strip() for t in args.tag.split(",")] if args.tag else None

    print(f"\n🔍 Question: {question}")
    if doc_type:
        print(f"   Filter doc_type: {doc_type}")
    if tags:
        print(f"   Filter tags: {tags}")

    result = answer_about_ateet(question, doc_type=doc_type, tags=tags)

    print(f"\n💡 Answer:\n{result['answer']}")
    print(f"\n📌 Route: {result['route']}")
    print(f"📎 Sources ({len(result['sources'])}): {result['sources']}")
    if result["key_facts"]:
        print("\n📋 Key facts:")
        for i, fact in enumerate(result["key_facts"], 1):
            print(f"   {i}. {fact[:120]}...")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Self-Info RAG CLI — build index and ask questions",
        prog="python -m src.tools.self_info_cli",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- build --
    build_parser = subparsers.add_parser("build", help="Build/rebuild the vector store")
    build_parser.add_argument(
        "--rebuild",
        action="store_true",
        default=True,
        help="Force full rebuild (delete + re-embed)",
    )
    build_parser.set_defaults(func=cmd_build)

    # -- ask --
    ask_parser = subparsers.add_parser("ask", help="Ask a question via RAG")
    ask_parser.add_argument("question", help="The question to ask")
    ask_parser.add_argument("--doc-type", default=None, help="Filter by doc_type")
    ask_parser.add_argument(
        "--tag", default=None, help="Filter by tag(s), comma-separated"
    )
    ask_parser.add_argument(
        "--index",
        choices=["facts", "evidence", "both"],
        default=None,
        help="Force a specific index (overrides router)",
    )
    ask_parser.set_defaults(func=cmd_ask)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
