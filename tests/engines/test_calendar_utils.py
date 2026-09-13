"""历法与时间处理统一层单元测试。"""

from datetime import timedelta

import pytest

from engines import calendar_utils as cu
from engines.base import EngineError


def test_hour_index():
    assert cu.hour_index_from_datetime(cu._parse_datetime_string("2024-01-01 00:30:00")) == 0
    assert cu.hour_index_from_datetime(cu._parse_datetime_string("2024-01-01 23:30:00")) == 0
    assert cu.hour_index_from_datetime(cu._parse_datetime_string("2024-01-01 08:30:00")) == 4
    assert cu.hour_index_from_datetime(cu._parse_datetime_string("2024-01-01 12:00:00")) == 6


def test_true_solar_time_longitude():
    # 经度 91.5E vs 标准 120E：时差 = (91.5-120)*4 = -114 分钟
    dt = cu._parse_datetime_string("2024-06-01 12:00:00")
    corr = cu.true_solar_time_correction(dt, 91.5)
    # 均时差在 -15~+17 分钟内，因此总时差应在 [-129, -97] 分钟区间
    assert timedelta(minutes=-129) <= corr <= timedelta(minutes=-97)


def test_lunar_conversion():
    solar = cu.lunar_to_solar(1990, 4, 7)
    assert (solar.year, solar.month, solar.day) == (1990, 5, 1)


def test_lunar_info():
    info = cu.get_lunar_info(cu._parse_datetime_string("2024-02-10 00:00:00"))  # 2024 春节
    assert info["lunar_month"] == 1
    assert info["lunar_day"] == 1


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"birth_datetime": "1990-01-01 12:00:00"},
        {"birth_datetime": "1990-01-01 12:00:00", "timezone_offset": 8, "calendar": "solar",
         "true_solar_time": True},
    ],
)
def test_validation_errors(bad):
    with pytest.raises(EngineError):
        cu.validate_birth_input(bad)

# ---- 占卜时刻解析（奇门/六爻占时起盘） ----

_BASE = {"birth_datetime": "1990-05-01 08:30:00", "timezone_offset": 8, "calendar": "solar"}


def test_divination_datetime_takes_priority():
    dt = cu.resolve_divination_datetime(dict(_BASE, divination_datetime="2026-08-29 10:00:00"))
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 8, 29, 10, 0)


def test_divination_datetime_falls_back_to_birth():
    dt = cu.resolve_divination_datetime(dict(_BASE))
    assert (dt.year, dt.month, dt.day) == (1990, 5, 1)


def test_divination_datetime_with_true_solar_time_applied():
    # 真太阳时校正语义同样适用于占卜时刻（经度 120 以东为正修正）
    raw = cu.resolve_divination_datetime(dict(_BASE, divination_datetime="2026-08-29 10:00:00"))
    corrected = cu.resolve_divination_datetime(dict(
        _BASE, divination_datetime="2026-08-29 10:00:00",
        true_solar_time=True, longitude=121.47))
    assert corrected != raw


# ---- 农历日期合法性（sxtwl 会静默回卷非法日期，必须自行拦截） ----
#
# sxtwl.fromLunar 对不存在的农历日**不报错而是回卷**：
# 实测 fromLunar(1990, 4, 30)（该年四月仅 29 天）返回公历 1990-05-24
# 并自称农历 5/1 —— 等于把用户输入的日期悄悄换成另一天。


@pytest.mark.parametrize("bad", [
    "1990-04-30 10:00:00",  # 该年四月仅 29 天
    "1990-04-31 10:00:00",  # 农历月最多 30 天
    "1990-13-01 10:00:00",  # 无 13 月
    "1990-00-01 10:00:00",  # 无 0 月
    "1990-04-00 10:00:00",  # 无 0 日
])
def test_invalid_lunar_date_rejected(bad):
    """非法农历日期必须抛 EngineError，禁止静默回卷到相邻日期。"""
    with pytest.raises(EngineError):
        cu.lunar_to_solar(*(int(x) for x in bad.split(" ")[0].split("-")))


@pytest.mark.parametrize("lunar_date,solar_date", [
    ("1981-02-30", (1981, 4, 4)),   # 农历二月三十：公历无 2 月 30 日，但农历合法
    ("1990-02-30", (1990, 3, 26)),
    ("1985-02-30", (1985, 4, 19)),
])
def test_valid_lunar_thirtieth_accepted(lunar_date, solar_date):
    """合法农历三十（公历不存在的日期）必须能起盘，不得被公历月长校验误拒。"""
    y, m, d = (int(x) for x in lunar_date.split("-"))
    solar = cu.lunar_to_solar(y, m, d)
    assert (solar.year, solar.month, solar.day) == solar_date


def test_lunar_thirtieth_via_resolve_solar_datetime():
    """经 resolve_solar_datetime 走完整字符串路径也应接受合法农历三十。"""
    dt = cu.resolve_solar_datetime({
        "birth_datetime": "1981-02-30 10:00:00",
        "calendar": "lunar", "timezone_offset": 8})
    assert (dt.year, dt.month, dt.day, dt.hour) == (1981, 4, 4, 10)


def test_lunar_leap_month_roundtrip():
    """闰月日期往返一致（往返校验不得误伤合法闰月）。"""
    solar = cu.lunar_to_solar(2023, 2, 15, is_leap=True)
    info = cu.get_lunar_info(solar)
    assert info["lunar_month"] == 2
    assert info["lunar_day"] == 15
    assert info["is_lunar_leap"] is True


def test_lunar_time_optional():
    """农历输入的时间部分可省略（沿用原行为：缺省 12:00）。"""
    dt = cu.resolve_solar_datetime({
        "birth_datetime": "1990-04-07", "calendar": "lunar", "timezone_offset": 8})
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (1990, 5, 1, 12, 0)


def test_solar_invalid_date_still_rejected():
    """公历路径的非法日期仍必须拒绝（本次改动不得放宽公历校验）。"""
    with pytest.raises(EngineError):
        cu.resolve_solar_datetime({
            "birth_datetime": "2024-02-30 10:00:00",
            "calendar": "solar", "timezone_offset": 8})
