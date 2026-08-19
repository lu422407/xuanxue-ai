"""Reranker：对初检结果做二次排序。

基于关键词覆盖率的轻量重排（BM25-lite）。
生产环境可替换为交叉编码器模型。
"""

import re
from typing import Any, Dict, List

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+")


def _keywords(text: str) -> set:
    return set(_TOKEN_RE.findall(text.lower()))


class KeywordReranker:
    def rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        query_kw = _keywords(query)
        if not query_kw:
            return results
        ranked = []
        for r in results:
            doc_kw = _keywords(r["text"])
            overlap = len(query_kw & doc_kw)
            boost = overlap / max(len(query_kw), 1)
            r = dict(r)
            r["score"] = r["score"] * 0.7 + boost * 0.3
            ranked.append(r)
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked