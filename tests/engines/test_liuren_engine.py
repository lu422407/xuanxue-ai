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


# ---- 占时语义：与 calendar_utils.resolve_divination_datetime 对齐（COMPROMISES 二档 #2） ----
#
# 历史缺陷（两个静默错误，均因引擎内自行 _parse_datetime_string 绕过 calendar_utils）：
#   ① calendar="lunar" 被静默忽略 → 按公历起课，日柱错
#   ② true_solar_time 被静默忽略 → 占时不校正，且 input_echo 回显未校正值
#     却仍标 true_solar_time_applied=true（回显撒谎）


def test_liuren_lunar_calendar_converted(liuren_engine):
    """农历输入必须换算为公历起课（禁止静默按公历解读）。"""
    from engines.bazi_engine import BaziEngine

    lunar_input = {
        "birth_datetime": "1990-04-07 10:00:00",  # 农历 1990-04-07 = 公历 1990-05-01
        "calendar": "lunar",
        "timezone_offset": 8,
        "gender": "男",
    }
    result = liuren_engine.calculate(dict(lunar_input))
    bazi = BaziEngine().calculate(dict(lunar_input))
    expected = {k: v["stem"] + v["branch"] for k, v in bazi["pillars"].items()}
    assert result["pillars"] == expected
    # 回显必须是换算后的农历（而非输入串原样回读）
    assert result["input_echo"]["lunar"]["lunar_month"] == 4
    assert result["input_echo"]["lunar"]["lunar_day"] == 7


def test_liuren_true_solar_time_shifts_occupation_hour(liuren_engine):
    """真太阳时校正必须作用于占时（经度 91.5E 应约 −114 分钟，巳时退到辰时）。"""
    base = {"birth_datetime": "2024-03-05 10:00:00", "calendar": "solar",
            "timezone_offset": 8, "gender": "男"}
    raw = liuren_engine.calculate(dict(base))
    corrected = liuren_engine.calculate(dict(
        base, true_solar_time=True, longitude=91.5))

    assert raw["占时"] == "巳"
    assert corrected["占时"] == "辰"  # 校正后落到辰时


def test_liuren_input_echo_reflects_corrected_time(liuren_engine):
    """回显不得撒谎：标了 applied=true 就必须回显真正用于起课的时刻。"""
    base = {"birth_datetime": "2024-03-05 10:00:00", "calendar": "solar",
            "timezone_offset": 8, "gender": "男"}
    result = liuren_engine.calculate(dict(
        base, true_solar_time=True, longitude=91.5))

    echo = result["input_echo"]
    assert echo["true_solar_time_applied"] is True
    assert echo["longitude"] == 91.5
    # 校正后时刻 ≠ 原始时刻，且与占时相符（07:53 属辰时 07:00-09:00）
    assert echo["solar_datetime_after_correction"] != echo["birth_datetime"]
    assert echo["solar_datetime_after_correction"].startswith("2024-03-05 07:5")
    # 未启用校正时不出现该字段
    assert "solar_datetime_after_correction" not in liuren_engine.calculate(dict(base))["input_echo"]


def test_liuren_divination_datetime_ignores_birth_calendar(liuren_engine):
    """占时按公历 ISO 串解析（与 API 契约一致），不受 birth 的 calendar 影响。"""
    result = liuren_engine.calculate({
        "birth_datetime": "1990-04-07 10:00:00",  # 农历出生
        "calendar": "lunar",
        "divination_datetime": "2026-08-29 10:00:00",
        "timezone_offset": 8,
        "gender": "男",
    })
    assert result["divination_time"] == "2026-08-29 10:00:00"
    # 起课用占时 2026-08-29，而非出生时间换算结果
    assert result["input_echo"]["lunar"]["lunar_year"] == 2026