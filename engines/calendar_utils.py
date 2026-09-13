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
    """解析公历 YYYY-MM-DD HH:MM[:SS]，非法日期抛 EngineError。"""
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
    try:
        return datetime(y, mo, d, h, mi, sec)
    except ValueError as exc:
        raise EngineError(f"出生时间非法: {s}（{exc}）", code="INVALID_DATETIME")


def _parse_lunar_datetime_string(s: str) -> Tuple[int, int, int, int, int]:
    """解析农历 YYYY-MM-DD HH:MM[:SS]，返回 (年, 月, 日, 时, 分)。

    **不能复用 `_parse_datetime_string`**：后者以公历 `datetime` 构造，
    而合法农历日可能是公历不存在的日期（如农历二月三十 1981-02-30，
    公历无 2 月 30 日），会被公历月长校验误拒。此处只做范围校验，
    日期是否真实存在交由 `lunar_to_solar` 的往返校验判定。
    """
    s = s.strip()
    # 时间部分可省略（沿用原行为：缺省 12:00）
    match = re.match(
        r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T\s](\d{1,2}):(\d{2})(?::(\d{2}))?)?$", s
    )
    if not match:
        raise EngineError(
            f"birth_datetime 格式必须为 YYYY-MM-DD HH:MM[:SS]，收到: {s}",
            code="INVALID_DATETIME",
        )
    y, mo, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
    h = int(match.group(4)) if match.group(4) else 12
    mi = int(match.group(5)) if match.group(5) else 0
    if not (1 <= mo <= 12 and 0 <= h <= 23 and 0 <= mi <= 59):
        raise EngineError(f"农历日期非法: {s}", code="INVALID_DATETIME")
    if not (1 <= d <= 30):
        raise EngineError(f"农历日期非法: {s}（农历月最多 30 天）", code="INVALID_DATETIME")
    if y < -3000 or y > 3000:
        raise EngineError(
            f"出生年份超出 sxtwl 支持范围 [-3000, 3000]: {y}", code="YEAR_OUT_OF_RANGE"
        )
    return y, mo, d, h, mi


def resolve_solar_datetime(input_data: Dict[str, Any]) -> datetime:
    """把输入解析为本地时区的公历 datetime，并应用可选的真太阳时校正。

    返回的 datetime 是"经真太阳时校正后的本地时间"，
    用于后续确定时辰（因为时辰边界取决于真太阳时）。
    """
    calendar = input_data["calendar"]
    if calendar == "solar":
        dt = _parse_datetime_string(input_data["birth_datetime"])
    else:
        # 农历输入：日期与时间分开解析，且**必须走农历专用解析**
        # （合法农历日可能是公历不存在的日期，用公历 datetime 构造会误拒）。
        # 日期是否真实存在由 lunar_to_solar 的往返校验判定。
        lunar_y, lunar_m, lunar_d, lunar_h, lunar_mi = _parse_lunar_datetime_string(
            input_data["birth_datetime"])
        dt = lunar_to_solar(lunar_y, lunar_m, lunar_d,
                            is_leap=input_data.get("lunar_is_leap", False),
                            hour=lunar_h, minute=lunar_mi)

    if input_data.get("true_solar_time"):
        lon = float(input_data["longitude"])
        correction = true_solar_time_correction(dt, lon)
        dt = dt + correction

    return dt


def resolve_divination_datetime(input_data: Dict[str, Any]) -> datetime:
    """占卜时刻解析：优先 divination_datetime，缺省回落出生时间。

    奇门/六爻等以「占时」起盘的引擎共用。占卜时刻按公历 ISO 串
    解析（与 API 契约一致），真太阳时校正语义与出生时间相同。
    """
    if input_data.get("divination_datetime"):
        data = dict(input_data)
        data["birth_datetime"] = input_data["divination_datetime"]
        data["calendar"] = "solar"
        return resolve_solar_datetime(data)
    return resolve_solar_datetime(input_data)


def lunar_to_solar(lunar_year: int, lunar_month: int, lunar_day: int,
                   is_leap: bool = False, hour: int = 12, minute: int = 0) -> datetime:
    """农历转公历。闰月需显式标注 is_leap=True。

    非法的农历月/日（如某年四月只有 29 天却传 30）必须显式报错：
    `sxtwl.fromLunar` 对这类输入**不报错而是静默回卷**到相邻日期
    （实测 fromLunar(1990,4,30) 返回公历 1990-05-24 并自称农历 5/1），
    等于把用户输入的日期悄悄换成另一天 —— 静默错误比报错更危险。

    校验方式：往返比对（fromLunar 结果再读回农历月/日/闰月是否与输入一致）。
    已在 1900-2100 共 144,720 个 (年,月,日,闰月) 组合上验证：
    合法日期（含闰月）往返全部一致，非法日期全部被识别。
    """
    try:
        day = sxtwl.fromLunar(lunar_year, lunar_month, lunar_day, is_leap)
    except Exception as exc:
        raise EngineError(
            f"农历日期非法: {lunar_year}年{lunar_month}月{lunar_day}日"
            f"{'（闰月）' if is_leap else ''}：{exc}",
            code="INVALID_LUNAR_DATE",
        )

    # 往返校验：sxtwl 会静默回卷非法日期，必须自行拦截
    if (day.getLunarMonth() != lunar_month
            or day.getLunarDay() != lunar_day
            or bool(day.isLunarLeap()) != bool(is_leap)):
        raise EngineError(
            f"农历日期不存在: {lunar_year}年{lunar_month}月{lunar_day}日"
            f"{'（闰月）' if is_leap else ''}"
            f"（该月共 {_lunar_month_days(lunar_year, lunar_month, is_leap)} 天）",
            code="INVALID_LUNAR_DATE",
        )

    return datetime(day.getSolarYear(), day.getSolarMonth(), day.getSolarDay(),
                    hour, minute)


def _lunar_month_days(lunar_year: int, lunar_month: int, is_leap: bool) -> int:
    """该农历月的实际天数（29 或 30），仅用于错误信息。"""
    for days in (30, 29):
        probe = sxtwl.fromLunar(lunar_year, lunar_month, days, is_leap)
        if probe.getLunarMonth() == lunar_month and probe.getLunarDay() == days:
            return days
    return 29


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