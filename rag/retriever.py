"""RAG 检索器。

流程：问题 → Embedding → Vector Search → Rerank → 返回带 source_id 的文档。
"""

import re
from typing import Any, Callable, Dict, List, Optional

from rag.embedding import cosine_similarity, embed
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
        bigram 精确匹配对全量文档计算，避免向量 top_k 截断把精确命中挤出候选。
        """
        query_vector = self._embed(query)
        query_bigrams = _bigrams(query)
        candidates = self.store.search(query_vector, top_k=top_k)
        for r in candidates:
            r["score"] = r["score"] * 0.6
        if query_bigrams:
            all_ids = self.store.all_doc_ids()
            exact_extra: List[Dict[str, Any]] = []
            for doc_id in all_ids:
                doc = self.store.get(doc_id)
                if not doc or any(c["doc_id"] == doc_id for c in candidates):
                    continue
                overlap = len(query_bigrams & _bigrams(doc["text"])) / len(query_bigrams)
                if overlap > 0:
                    vector_score = cosine_similarity(query_vector, doc["vector"])
                    exact_extra.append({
                        "doc_id": doc_id, "score": vector_score * 0.6 + overlap * 0.4,
                        "text": doc["text"], "metadata": dict(doc["metadata"]),
                    })
            candidates.extend(exact_extra)
        candidates.sort(key=lambda x: x["score"], reverse=True)
        results = candidates[:top_k]
        if reranker is not None:
            results = reranker.rerank(query, results)
        return results