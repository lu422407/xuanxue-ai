"""大六壬引擎测试（基于 dalurenpython）。"""

import pytest

from engines.liuren_engine import LiuRenEngine

INPUT = {
    "birth_datetime": "2018-08-29 13:22:07",
    "timezone_offset": 8,
    "calendar": "solar",
    "gender": "男",
}


@pytest.fixture(scope="module")
def liuren_engine():
    return LiuRenEngine()


def test_liuren_chart_structure(liuren_engine):
    result = liuren_engine.calculate(dict(INPUT))
    assert result["system"] == "liuren"
    # 三传必须有初传/中传/末传
    assert set(result["三传"].keys()) == {"初传", "中传", "末传", "六亲", "遁干"}
    assert result["三传"]["初传"] != result["三传"]["末传"]
    # 四课四门齐全
    assert set(result["四课"].keys()) == {"一课", "二课", "三课", "四课"}
    for key in ("一课", "二课", "三课", "四课"):
        assert len(result["四课"][key]) == 2
    # 天地盘覆盖十二支
    assert len(result["天地盘"]) == 12
    # 月将/占时/空亡存在
    assert result["月将"] in "子丑寅卯辰巳午未申酉戌亥"
    assert result["占时"] in "子丑寅卯辰巳午未申酉戌亥"
    assert len(result["空亡"]) == 2


def test_liuren_deterministic(liuren_engine):
    a = liuren_engine.calculate(dict(INPUT))
    b = liuren_engine.calculate(dict(INPUT))
    assert a == b


def test_liuren_divination_datetime_override(liuren_engine):
    inp = dict(INPUT)
    inp["divination_datetime"] = "2019-01-15 20:30:00"
    result = liuren_engine.calculate(inp)
    assert result["divination_time"] == "2019-01-15 20:30:00"
    assert result["system"] == "liuren"


def test_liuren_rejects_missing_input(liuren_engine):
    with pytest.raises(Exception):
        liuren_engine.calculate({})