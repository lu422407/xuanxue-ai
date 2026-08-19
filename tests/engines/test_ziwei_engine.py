"""紫微引擎单元测试。"""

import pytest

from engines.base import EngineError
from engines.ziwei_engine import ZiWeiEngine

VALID = {
    "birth_datetime": "1990-05-01 08:30:00",
    "timezone_offset": 8,
    "calendar": "solar",
    "gender": "男",
}


def test_valid_input():
    result = ZiWeiEngine().calculate(dict(VALID))
    assert result["system"] == "ziwei"
    assert len(result["palaces"]) == 12
    assert "input_echo" in result


@pytest.mark.parametrize(
    "mutate",
    [
        {"gender": None},
        {"gender": "未知"},
        {"school": "bad_school"},
        {"timezone_offset": None},
    ],
)
def test_invalid_inputs_raise(mutate):
    with pytest.raises(EngineError):
        ZiWeiEngine().calculate({**VALID, **mutate})


def test_deterministic():
    a = ZiWeiEngine().calculate(dict(VALID))
    b = ZiWeiEngine().calculate(dict(VALID))
    assert a == b


def test_soul_same_across_gender():
    male = ZiWeiEngine().calculate({**VALID})
    female = ZiWeiEngine().calculate({**VALID, "gender": "女"})
    # 命宫（魂宫）由生月+时辰决定，与性别无关；性别影响大限顺逆（未在此输出中体现）
    assert male["soul"] == female["soul"]
    assert male["palaces"] == female["palaces"]


def test_twelve_palaces_all_present():
    r = ZiWeiEngine().calculate(dict(VALID))
    names = {"命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "仆役",
             "官禄", "田宅", "福德", "父母"}
    assert set(r["palaces"].keys()) == names