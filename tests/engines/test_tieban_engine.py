"""铁板神数引擎测试（考刻定分）。"""

import pytest

from engines.tieban_engine import TieBanEngine

INPUT = {
    "birth_datetime": "1990-08-16 14:30:00",
    "timezone_offset": 8,
    "calendar": "solar",
    "gender": "男",
}

KNOWN_FACTS = {
    "father_zodiac": "龙",
    "mother_zodiac": "蛇",
    "siblings": "3",
    "self_rank": "2",
}


@pytest.fixture(scope="module")
def tieban_engine():
    return TieBanEngine()


def test_verify_kefen_shape(tieban_engine):
    result = tieban_engine.verify_kefen(dict(INPUT), dict(KNOWN_FACTS))
    assert result["method"] == "考刻定分"
    assert "verified_ke" in result
    assert "verified_fen" in result
    assert result["kefen_string"].endswith("分")
    assert "刻" in result["kefen_string"]
    assert 0 <= result["confidence"] <= 1
    assert "matched_facts" in result
    assert "contradictions" in result
    assert len(result["all_candidates"]) == 5
    assert "base_chart" in result


def test_verify_kefen_deterministic(tieban_engine):
    a = tieban_engine.verify_kefen(dict(INPUT), dict(KNOWN_FACTS))
    b = tieban_engine.verify_kefen(dict(INPUT), dict(KNOWN_FACTS))
    assert a["verified_ke"] == b["verified_ke"]
    assert a["verified_fen"] == b["verified_fen"]
    assert a["confidence"] == b["confidence"]


def test_kefen_to_string(tieban_engine):
    assert tieban_engine._kefen_to_string(0, 3) == "初刻3分"
    assert tieban_engine._kefen_to_string(7, 9) == "七刻9分"


def test_compare_facts(tieban_engine):
    predicted = {"father_zodiac": "龙", "mother_zodiac": "蛇", "siblings": "3"}
    known = {"father_zodiac": "龙", "mother_zodiac": "蛇", "siblings": "3"}
    score, matched, contradictions = tieban_engine._compare_facts(predicted, known)
    assert score == 1.0
    assert len(matched) == 3
    assert contradictions == []


def test_compare_facts_mismatch(tieban_engine):
    predicted = {"father_zodiac": "虎", "siblings": "3"}
    known = {"father_zodiac": "龙", "siblings": "3"}
    score, matched, contradictions = tieban_engine._compare_facts(predicted, known)
    assert score == 0.5
    assert len(contradictions) == 1


def test_calculate_basic(tieban_engine):
    result = tieban_engine.calculate(dict(INPUT))
    assert result["system"] == "tieban"
    assert "base_chart" in result
    assert "tiaowen_count" in result


def test_empty_facts(tieban_engine):
    result = tieban_engine.verify_kefen(dict(INPUT), {})
    assert result["confidence"] == 0
    assert result["matched_facts"] == []
    assert result["contradictions"] == []