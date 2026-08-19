"""历法与时间处理统一层。

所有引擎必须通过本模块处理时间，禁止各自实现，避免不一致。

- 公历 ↔ 农历转换：基于 sxtwl（寿星天文历），覆盖公元前 3000 年 ~ 公元 3000 年。
- 真太阳时校正：经度时差 + 均时差，是否启用由显式参数 true_solar_time 控制。
- 早晚子时流派：作为可配置项（bazi_subhour_rule），默认"midnight"（子正换日，0 点换日）。
- 闰月处理：八字按节气定月（无闰月概念）；农历月号标注是否闰月。
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import sxtwl

from engines.base import EngineError

GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 地支藏干（子平派标准）
HIDDEN_STEMS = {
    0: [9],            # 子: 癸
    1: [4, 9, 7],      # 丑: 己癸辛
    2: [0, 2, 4],      # 寅: 甲丙戊
    3: [1],            # 卯: 乙
    4: [4, 1, 9],      # 辰: 戊乙癸
    5: [2, 6, 4],      # 巳: 丙庚戊
    6: [3, 5],         # 午: 丁己
    7: [5, 3, 1],      # 未: 己丁乙
    8: [6, 8, 4],      # 申: 庚壬戊
    9: [7],            # 酉: 辛
    10: [4, 7, 3],     # 戌: 戊辛丁
    11: [8, 0],        # 亥: 壬甲
}

# 标准时区：以中国标准时东经 120° 为基准
STD_LONGITUDE = 120.0


def validate_birth_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """通用输入校验。返回规范化后的输入，非法输入抛 EngineError。"""
    if not isinstance(input_data, dict):
        raise EngineError("输入必须是 JSON 对象", code="INVALID_INPUT")

    birth_datetime = input_data.get("birth_datetime")
    if not birth_datetime:
        raise EngineError("缺少出生时间 birth_datetime", code="MISSING_BIRTH_TIME")

    if "timezone_offset" not in input_data:
        raise EngineError("缺少时区 timezone_offset（小时，相对 UTC）", code="MISSING_TIMEZONE")

    calendar = input_data.get("calendar", "solar")
    if calendar not in ("solar", "lunar"):
        raise EngineError(f"calendar 只能为 solar 或 lunar，收到: {calendar}", code="INVALID_CALENDAR")

    try:
        timezone_offset = float(input_data["timezone_offset"])
    except (TypeError, ValueError):
        raise EngineError("timezone_offset 必须是数字（小时）", code="INVALID_TIMEZONE")
    if timezone_offset < -12 or timezone_offset > 14:
        raise EngineError("timezone_offset 超出合理范围 [-12, 14]", code="INVALID_TIMEZONE")

    normalized = dict(input_data)
    normalized["timezone_offset"] = timezone_offset
    normalized["calendar"] = calendar

    if "true_solar_time" not in normalized:
        normalized["true_solar_time"] = False

    if normalized.get("true_solar_time"):
        if "longitude" not in normalized:
            raise EngineError(
                "启用真太阳时校正时必须提供经度 longitude", code="MISSING_LONGITUDE"
            )
        try:
            lon = float(normalized["longitude"])
        except (TypeError, ValueError):
            raise EngineError("longitude 必须是数字", code="INVALID_LONGITUDE")
        if lon < -180 or lon > 180:
            raise EngineError("longitude 超出合理范围 [-180, 180]", code="INVALID_LONGITUDE")
        normalized["longitude"] = lon

    return normalized


def _parse_datetime_string(s: str) -> datetime:
    s = s.strip()
    match = re.match(
        r"^(\d{4})-(\d{1,2})-(\d{1,2})[T\s](\d{1,2}):(\d{2})(?::(\d{2}))?$", s
    )
    if not match:
        raise EngineError(
            f"birth_datetime 格式必须为 YYYY-MM-DD HH:MM[:SS]，收到: {s}",
            code="INVALID_DATETIME",
        )
    y, mo, d, h, mi, sec = (int(g) if g else 0 for g in match.groups())
    if not (1 <= mo <= 12 and 1 <= d <= 31 and 0 <= h <= 23 and 0 <= mi <= 59 and 0 <= sec <= 59):
        raise EngineError(f"出生时间非法: {s}", code="INVALID_DATETIME")
    if y < -3000 or y > 3000:
        raise EngineError(
            f"出生年份超出 sxtwl 支持范围 [-3000, 3000]: {y}", code="YEAR_OUT_OF_RANGE"
        )
    return datetime(y, mo, d, h, mi, sec)


def resolve_solar_datetime(input_data: Dict[str, Any]) -> datetime:
    """把输入解析为本地时区的公历 datetime，并应用可选的真太阳时校正。

    返回的 datetime 是"经真太阳时校正后的本地时间"，
    用于后续确定时辰（因为时辰边界取决于真太阳时）。
    """
    calendar = input_data["calendar"]
    if calendar == "solar":
        dt = _parse_datetime_string(input_data["birth_datetime"])
    else:
        # 农历输入：日期部分 + 时间部分分开解析
        lunar_str = input_data["birth_datetime"]
        parts = lunar_str.split(" ")
        date_part, time_part = parts[0], parts[1] if len(parts) > 1 else "12:00:00"
        lunar_dt = _parse_datetime_string(f"{date_part} {time_part}")
        dt = lunar_to_solar(lunar_dt.year, lunar_dt.month, lunar_dt.day,
                            is_leap=input_data.get("lunar_is_leap", False),
                            hour=lunar_dt.hour, minute=lunar_dt.minute)

    if input_data.get("true_solar_time"):
        lon = float(input_data["longitude"])
        correction = true_solar_time_correction(dt, lon)
        dt = dt + correction

    return dt


def lunar_to_solar(lunar_year: int, lunar_month: int, lunar_day: int,
                   is_leap: bool = False, hour: int = 12, minute: int = 0) -> datetime:
    """农历转公历。闰月需显式标注 is_leap=True。"""
    day = sxtwl.fromLunar(lunar_year, lunar_month, lunar_day, is_leap)
    return datetime(day.getSolarYear(), day.getSolarMonth(), day.getSolarDay(),
                    hour, minute)


def true_solar_time_correction(dt: datetime, longitude: float) -> timedelta:
    """真太阳时校正 = 经度时差 + 均时差。

    经度时差: (经度 - 120) * 4 分钟（东经为正，向西减）。
    均时差: 标准近似公式 EoT = 9.87sin(2B) - 7.53cos(B) - 1.5sin(B)，
            B = 2π(N-81)/364，N 为年内天数。
    """
    import math

    # 经度时差
    lon_minutes = (longitude - STD_LONGITUDE) * 4.0

    # 均时差
    n = dt.timetuple().tm_yday
    b = 2 * math.pi * (n - 81) / 364
    eot_minutes = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    total_minutes = lon_minutes + eot_minutes
    return timedelta(minutes=total_minutes)


def get_lunar_info(dt: datetime) -> Dict[str, Any]:
    """返回公历时间对应的农历信息。"""
    day = sxtwl.fromSolar(dt.year, dt.month, dt.day)
    return {
        "lunar_year": day.getLunarYear(),
        "lunar_month": day.getLunarMonth(),
        "lunar_day": day.getLunarDay(),
        "is_lunar_leap": day.isLunarLeap(),
        "has_jieqi": day.hasJieQi(),
        "jieqi": day.getJieQi() if day.hasJieQi() else None,
    }


def hour_index_from_datetime(dt: datetime) -> int:
    """按 23:00 起子时的时辰分界，返回时辰索引（0=子, 11=亥）。

    子时: 23:00-01:00（索引 0）。
    """
    h = dt.hour
    if h == 23:
        return 0
    return ((h + 1) // 2) % 12


def apply_subhour_rule(solar: datetime, day: "sxtwl.Day", rule: str) -> Tuple["sxtwl.Day", int]:
    """应用早晚子时流派规则，返回 (有效日, 时辰索引)。

    - "midnight": 子正换日（0 点换日），23:00-23:59 的日柱仍用当天，时柱为子时。
    - "early_zi": 晚子时换日（23 点换日），23:00-23:59 的日柱用次日，时柱为子时。
    """
    branch_idx = hour_index_from_datetime(solar)
    if rule == "early_zi" and solar.hour == 23:
        return day.after(1), 0
    return day, branch_idx


def build_input_echo(input_data: Dict[str, Any], solar: datetime,
                     extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """构造 input_echo：回显引擎实际使用的历法参数，便于用户与 Validator 核对。"""
    echo = {
        "birth_datetime": input_data["birth_datetime"],
        "calendar": input_data["calendar"],
        "timezone_offset": input_data["timezone_offset"],
        "true_solar_time_applied": bool(input_data.get("true_solar_time")),
    }
    if input_data.get("true_solar_time"):
        echo["longitude"] = float(input_data["longitude"])
        echo["solar_datetime_after_correction"] = solar.isoformat(sep=" ")
    if extra:
        echo.update(extra)
    return echo