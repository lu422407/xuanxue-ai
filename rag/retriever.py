"""RAG 检索器。

流程：问题 → Embedding → Vector Search → Rerank → 返回带 source_id 的文档。
"""

import re
from typing import Any, Callable, Dict, List, Optional

from rag.embedding import embed
from rag.vector_store import VectorStore

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+")


def _bigrams(text: str) -> set:
    tokens = _TOKEN_RE.findall(text.lower())
    return {t[i:i + 2] for t in tokens for i in range(len(t) - 1)}


class Retriever:
    def __init__(self, store: Optional[VectorStore] = None,
                 embed_fn: Callable[[str], List[float]] = embed,
                 dim: int = 256):
        self.store = store or VectorStore(dim=dim)
        self._embed = embed_fn

    def add_knowledge(self, source_id: str, text: str,
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """向知识库添加文档。"""
        vector = self._embed(text)
        meta = dict(metadata or {})
        meta.setdefault("source_id", source_id)
        self.store.add(source_id, text, vector, meta)

    def retrieve(self, query: str, top_k: int = 5,
                 reranker: Optional[Any] = None) -> List[Dict[str, Any]]:
        """检索与查询最相关的文档。

        评分 = 向量余弦 * 0.6 + 字符 bigram 重叠率 * 0.4。
        bigram 重叠提供确定性的精确匹配信号，弥补哈希向量的碰撞噪声。
        """
        query_vector = self._embed(query)
        query_bigrams = _bigrams(query)
        results = self.store.search(query_vector, top_k=top_k)
        for r in results:
            doc_bigrams = _bigrams(r["text"])
            if query_bigrams:
                overlap = len(query_bigrams & doc_bigrams) / len(query_bigrams)
                r["score"] = r["score"] * 0.6 + overlap * 0.4
        results.sort(key=lambda x: x["score"], reverse=True)
        if reranker is not None:
            results = reranker.rerank(query, results)
        return results