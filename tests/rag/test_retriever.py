"""RAG 检索与知识库加载测试。"""

import pytest

from rag.knowledge_loader import load_knowledge
from rag.retriever import Retriever


@pytest.fixture()
def retriever():
    r = Retriever()
    n = load_knowledge(r)
    assert n >= 5
    return r


def test_knowledge_loaded(retriever):
    assert retriever.store.exists("rule_bazi_001")
    assert retriever.store.exists("case_ziwei_001")


def test_retrieve_relevant_rule(retriever):
    results = retriever.retrieve("正官是什么意思", top_k=3)
    assert results
    assert results[0]["score"] > 0
    # 正官相关文档应排在前面
    assert results[0]["metadata"]["source_id"] in ("rule_bazi_001",)


def test_retrieve_with_reranker(retriever):
    from rag.reranker import KeywordReranker

    results = retriever.retrieve("紫微入命 官禄宫事业", top_k=3, reranker=KeywordReranker())
    assert results


def test_topk_limit(retriever):
    results = retriever.retrieve("八字", top_k=2)
    assert len(results) <= 2