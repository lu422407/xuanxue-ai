"""Citation Checker 测试：识别伪造来源与语义不一致引用。"""

from rag.citation_checker import check_citations, extract_citations
from rag.knowledge_loader import load_knowledge
from rag.retriever import Retriever


def _make_store():
    r = Retriever()
    load_knowledge(r)
    return r.store


def test_extract_citations():
    text = "根据《子平真诠》[source:rule_bazi_001]所述，正官主贵气。另见[source:fake_999]"
    assert extract_citations(text) == ["rule_bazi_001", "fake_999"]


def test_rejects_fake_source_id():
    store = _make_store()
    answer = "古人云「正官主贵气」[source:rule_bazi_001]，又据某古籍[source:ghost_doc_000]云。"
    report = check_citations(answer, store)
    assert not report.passed
    assert report.invalid_sources == ["ghost_doc_000"]


def test_accepts_valid_citation_with_semantic_match():
    store = _make_store()
    answer = "「正官者，克我而阴阳相异者也，主贵气职务」[source:rule_bazi_001]"
    report = check_citations(answer, store)
    assert report.passed


def test_flags_semantic_mismatch():
    store = _make_store()
    # 引号内容与来源文档语义完全无关
    answer = "「今天的天气很好适合郊游野餐」[source:rule_bazi_001]"
    report = check_citations(answer, store)
    assert report.semantic_mismatches
    assert not report.passed