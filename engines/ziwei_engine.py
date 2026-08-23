"""紫微斗数引擎。

接入 py-iztro 0.1.5（中州派，内嵌 iztro-2.5.0 JS 引擎）。
输出十二宫、主星、四化、三方四正等结构化数据。
对超出库支持范围的输入抛出 EngineError，禁止静默输出错误结果。
"""

from typing import Any, Dict

from py_iztro import Astro

from engines.base import BaseEngine, EngineError
from engines import calendar_utils as cu

# py-iztro 的 time_index: 0=早子时, 1=丑, 2=寅, ..., 11=亥, 12=晚子时
_TIME_INDEX_BY_HOUR = {
    0: (0, 1),    # 23:00-01:00 早子(0-1点)/晚子(23点) 分别处理
    1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11,
}

# Astro 基于 pythonmonkey 内嵌 JS 引擎，实例化开销大且在 Windows 上多次
# 实例化会导致 Node 子进程泄漏。使用模块级单例，进程内只加载一次。
_ASTRO_SINGLETON = None


def _get_astro():
    global _ASTRO_SINGLETON
    if _ASTRO_SINGLETON is None:
        _ASTRO_SINGLETON = Astro()
    return _ASTRO_SINGLETON


def _hour_to_time_index(dt):
    h = dt.hour
    if h == 23:
        return 12  # 晚子时
    if h in (0, 1):
        return 0   # 早子时
    return (h + 1) // 2


class ZiWeiEngine(BaseEngine):
    name = "ziwei"
    version = "0.1.0"
    system = "ziwei"

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = cu.validate_birth_input(input_data)
        gender = normalized.get("gender")
        if gender not in ("男", "女"):
            raise EngineError("ziwei 引擎必须提供 gender（男/女）", code="MISSING_GENDER")
        school = normalized.get("school", "zhongzhou")
        if school not in ("sanhe", "feixing", "zhongzhou", "qintian"):
            raise EngineError(f"school 非法: {school}", code="INVALID_SCHOOL")
        normalized["school"] = school
        return normalized

    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self.validate_input(input_data)
        solar = cu.resolve_solar_datetime(normalized)

        time_index = _hour_to_time_index(solar)
        try:
            astrolabe = _get_astro().by_solar(
                f"{solar.year}-{solar.month}-{solar.day}",
                time_index,
                normalized["gender"],
                fix_leap=bool(normalized.get("fix_leap", True)),
                language="zh-CN",
            )
        except Exception as exc:  # py-iztro 底层 JS 计算失败
            raise EngineError(
                f"紫微排盘失败（可能超出库支持范围）: {exc}", code="ZIWEI_CALC_FAILED"
            )

        data = astrolabe.model_dump()

        palaces = {}
        for palace in data.get("palaces", []):
            # 保留 py-iztro 的 brightness（庙旺得利平不陷），供 validator 亮度校验
            major = [
                {"name": s["name"], "brightness": s.get("brightness", "")}
                for s in palace.get("major_stars", [])
            ]
            minor = [s["name"] for s in palace.get("minor_stars", [])]
            adopted = [s["name"] for s in palace.get("adjective_stars", [])]
            decadal = palace.get("decadal") or {}
            palaces[palace["name"]] = {
                "position": palace["earthly_branch"],
                "major_stars": major,
                "minor_stars": minor,
                "adopted_stars": adopted,
                "mutagen": decadal.get("mutagen") if isinstance(decadal, dict) else None,
            }

        return {
            "system": self.system,
            "engine_version": self.version,
            "input_echo": cu.build_input_echo(
                normalized, solar,
                {"school": normalized["school"],
                 "gender": normalized["gender"],
                 "lunar": cu.get_lunar_info(solar),
                 "lunar_date": data.get("lunar_date"),
                 "chinese_date": data.get("chinese_date")}),
            "soul": {"star": data.get("soul"), "palace": data.get("earthly_branch_of_soul_palace")},
            "body": {"star": data.get("body"), "palace": data.get("earthly_branch_of_body_palace")},
            "palaces": palaces,
        }