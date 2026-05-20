from __future__ import annotations

import os
from types import SimpleNamespace

from langchain_core.embeddings import Embeddings

os.environ["DEBUG"] = "false"

from backend.knowledge.supabase_compat import CompatibleSupabaseVectorStore


class FakeEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeRPCBuilder:
    def __init__(self, data):
        self.request = SimpleNamespace(params={})
        self._data = data

    def execute(self):
        return SimpleNamespace(data=self._data)


class FakeSupabaseClient:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return FakeRPCBuilder(self.data)


def test_similarity_search_uses_match_count_rpc_arg_without_params_attr():
    client = FakeSupabaseClient(
        [
            {
                "content": "cached answer",
                "metadata": {"doc_type": "reply_cache"},
                "similarity": 0.91,
            }
        ]
    )
    store = CompatibleSupabaseVectorStore(
        client=client,
        embedding=FakeEmbeddings(),
        table_name="documents_reply_cache",
        query_name="match_reply_cache",
    )

    results = store.similarity_search_with_relevance_scores("hello", k=3)

    assert client.calls == [
        (
            "match_reply_cache",
            {"query_embedding": [0.1, 0.2, 0.3], "match_count": 3},
        )
    ]
    assert results[0][0].page_content == "cached answer"
    assert results[0][1] == 0.91


def test_similarity_search_applies_simple_metadata_filter_client_side():
    client = FakeSupabaseClient(
        [
            {
                "content": "wrong",
                "metadata": {"doc_type": "career"},
                "similarity": 0.95,
            },
            {
                "content": "right",
                "metadata": {"doc_type": "about_me"},
                "similarity": 0.93,
            },
        ]
    )
    store = CompatibleSupabaseVectorStore(
        client=client,
        embedding=FakeEmbeddings(),
        table_name="documents_self_info_facts",
        query_name="match_self_info_facts",
    )

    results = store.similarity_search_with_relevance_scores(
        "who are you", k=1, filter={"doc_type": "about_me"}
    )

    assert client.calls[0][1]["match_count"] == 4
    assert [doc.page_content for doc, _ in results] == ["right"]
