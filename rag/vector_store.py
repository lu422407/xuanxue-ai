"""内存向量库（测试/本地演示用）。

生产环境应替换为向量数据库（如 Milvus / Qdrant / pgvector），
接口对齐即可：add(doc_id, text, metadata) / search(query_vector, top_k)。
"""

import threading
from typing import Any, Dict, List, Optional, Tuple

from rag.embedding import cosine_similarity


class VectorStore:
    def __init__(self, dim: int = 128):
        self._dim = dim
        self._docs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    @property
    def dim(self) -> int:
        return self._dim

    def add(self, doc_id: str, text: str, vector: List[float],
            metadata: Optional[Dict[str, Any]] = None) -> None:
        if len(vector) != self._dim:
            raise ValueError(f"向量维度必须为 {self._dim}")
        with self._lock:
            self._docs[doc_id] = {
                "text": text, "vector": list(vector),
                "metadata": metadata or {},
            }

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            doc = self._docs.get(doc_id)
            return dict(doc) if doc else None

    def exists(self, doc_id: str) -> bool:
        with self._lock:
            return doc_id in self._docs

    def all_doc_ids(self) -> List[str]:
        with self._lock:
            return list(self._docs.keys())

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """按余弦相似度返回 top_k 文档。"""
        with self._lock:
            scored = [
                {"doc_id": doc_id, "score": cosine_similarity(query_vector, doc["vector"]),
                 "text": doc["text"], "metadata": dict(doc["metadata"])}
                for doc_id, doc in self._docs.items()
            ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def delete(self, doc_id: str) -> None:
        with self._lock:
            self._docs.pop(doc_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._docs)