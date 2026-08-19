"""引用溯源校验（Citation Checker）。

防止 LLM"编造出处"：LLM 引用古籍/案例时必须附带可追溯的 source_id，
本模块核实该 source_id 存在于向量库，且引用内容与原文语义一致。
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rag.embedding import cosine_similarity, embed

# 引用格式：[source:source_id]
_CITATION_RE = re.compile(r"\[source:\s*([A-Za-z0-9_\-]+)\]")
# 中文/英文引号
_QUOTE_RE = re.compile(r"[「『\"“]([^」』\"”]{4,80})[」』\"”]")


@dataclass
class CitationReport:
    valid_sources: List[str] = field(default_factory=list)
    invalid_sources: List[str] = field(default_factory=list)
    semantic_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    unverifiable_snippets: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.invalid_sources and not self.semantic_mismatches


def extract_citations(text: str) -> List[str]:
    return _CITATION_RE.findall(text)


def check_citations(answer_text: str, store, similarity_threshold: float = 0.5) -> CitationReport:
    """校验答案中的引用。store 需提供 exists/get 方法。"""
    report = CitationReport()
    sources = extract_citations(answer_text)
    seen = set()
    for source_id in sources:
        if source_id in seen:
            continue
        seen.add(source_id)
        if not store.exists(source_id):
            report.invalid_sources.append(source_id)
            continue
        report.valid_sources.append(source_id)

    # 语义一致性：引号内的片段应与对应引用的文档内容相似
    doc = store.get(source_id) if sources else None
    if sources:
        source_id = sources[0]
        if store.exists(source_id):
            doc = store.get(source_id)
            snippets = _QUOTE_RE.findall(answer_text)
            for snippet in snippets:
                sim = cosine_similarity(embed(snippet), embed(doc["text"]))
                if sim < similarity_threshold:
                    report.semantic_mismatches.append({
                        "source_id": source_id,
                        "snippet": snippet,
                        "similarity": round(sim, 3),
                    })
    return report