"""八字引擎单元测试。"""

import pytest

from engines.base import EngineError
from engines.bazi_engine import BaziEngine

VALID = {
    "birth_datetime": "1990-05-01 08:30:00",
    "timezone_offset": 8,
    "calendar": "solar",
}


def test_valid_input():
    result = BaziEngine().calculate(dict(VALID))
    assert result["system"] == "bazi"
    assert result["pillars"]["year"]["stem_index"] == 6  # 庚
    assert result["pillars"]["month"]["branch_index"] == 4  # 辰
    assert "input_echo" in result


@pytest.mark.parametrize(
    "mutate",
    [
        {"birth_datetime": None},
        {"timezone_offset": None},
        {"calendar": "julian"},
        {"birth_datetime": "1990-13-01 08:30:00"},
        {"birth_datetime": "bad-format"},
        {"bazi_subhour_rule": "foo"},
        {"timezone_offset": 99},
    ],
)
def test_invalid_inputs_raise(mutate):
    with pytest.raises(EngineError):
        BaziEngine().calculate({**VALID, **mutate})


def test_deterministic():
    a = BaziEngine().calculate(dict(VALID))
    b = BaziEngine().calculate(dict(VALID))
    assert a == b


def test_year_boundary_lichun():
    # 2024-02-03 立春前仍为癸卯年
    r = BaziEngine().calculate({**VALID, "birth_datetime": "2024-02-03 12:00:00"})
    assert r["pillars"]["year"]["stem"] == "癸"
    # 2024-02-04 立春当天（16:26 后）为甲辰年
    r = BaziEngine().calculate({**VALID, "birth_datetime": "2024-02-04 12:00:00"})
    assert r["pillars"]["year"]["stem"] == "甲"


def test_subhour_rules_differ():
    base = {**VALID, "birth_datetime": "2024-01-01 23:30:00"}
    midnight = BaziEngine().calculate({**base, "bazi_subhour_rule": "midnight"})
    early_zi = BaziEngine().calculate({**base, "bazi_subhour_rule": "early_zi"})
    assert midnight["pillars"]["day"]["stem"] != early_zi["pillars"]["day"]["stem"]


def test_lunar_input_equals_solar():
    lunar = BaziEngine().calculate({
        "birth_datetime": "1990-04-07 08:30:00", "timezone_offset": 8,
        "calendar": "lunar"})
    solar = BaziEngine().calculate({**VALID})
    assert lunar["pillars"] == solar["pillars"]


def test_true_solar_time_changes_hour():
    no_tst = BaziEngine().calculate(dict(VALID))
    tst = BaziEngine().calculate({
        **VALID, "true_solar_time": True, "longitude": 91.5})  # 新疆经度，时差约 -114 分钟
    assert no_tst["pillars"]["hour"]["branch_index"] != tst["pillars"]["hour"]["branch_index"]