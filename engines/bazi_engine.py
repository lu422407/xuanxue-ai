"""八字引擎（子平法）。

确定性计算，基于 sxtwl（寿星天文历）：
- 年柱：立春分界
- 月柱：节气分界（寅月从立春起）
- 日柱：默认子正（0 点）换日，可通过 bazi_subhour_rule 切换为晚子时换日
- 时柱：23:00 起子时，五鼠遁定干
"""

from typing import Any, Dict

import sxtwl

from engines.base import BaseEngine, EngineError
from engines import calendar_utils as cu

GAN = cu.GAN
ZHI = cu.ZHI

_ELEMENT_OF_STEM = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]  # 0木 1火 2土 3金 4水
_ELEMENT_NAMES = ["木", "火", "土", "金", "水"]


def _ten_god(day_stem: int, other_stem: int) -> str:
    """十神。以日主为基准判断与其他天干的关系。"""
    e_day = _ELEMENT_OF_STEM[day_stem]
    e_other = _ELEMENT_OF_STEM[other_stem]
    same_yin = (day_stem % 2) == (other_stem % 2)
    if e_other == e_day:
        return "比肩" if same_yin else "劫财"
    if e_other == (e_day + 1) % 5:
        return "食神" if same_yin else "伤官"
    if e_other == (e_day + 2) % 5:
        return "偏财" if same_yin else "正财"
    if e_other == (e_day + 3) % 5:
        return "七杀" if same_yin else "正官"
    return "偏印" if same_yin else "正印"


class BaziEngine(BaseEngine):
    name = "bazi"
    version = "0.1.0"
    system = "bazi"

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = cu.validate_birth_input(input_data)
        rule = normalized.get("bazi_subhour_rule", "midnight")
        if rule not in ("midnight", "early_zi"):
            raise EngineError(
                f"bazi_subhour_rule 只能为 midnight 或 early_zi，收到: {rule}",
                code="INVALID_SUBHOUR_RULE",
            )
        normalized["bazi_subhour_rule"] = rule
        return normalized

    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self.validate_input(input_data)
        solar = cu.resolve_solar_datetime(normalized)

        day = sxtwl.fromSolar(solar.year, solar.month, solar.day)
        rule = normalized["bazi_subhour_rule"]
        eff_day, hour_branch = cu.apply_subhour_rule(solar, day, rule)

        year_gz = eff_day.getYearGZ()
        month_gz = eff_day.getMonthGZ()
        day_gz = eff_day.getDayGZ()
        hour_gz = eff_day.getHourGZ(solar.hour)

        year_stem, year_branch = year_gz.tg, year_gz.dz
        month_stem, month_branch = month_gz.tg, month_gz.dz
        day_stem, day_branch = day_gz.tg, day_gz.dz
        hour_stem, hour_branch_final = hour_gz.tg, hour_gz.dz

        pillars = {
            "year": {"stem": GAN[year_stem], "branch": ZHI[year_branch],
                     "stem_index": year_stem, "branch_index": year_branch,
                     "ten_god": _ten_god(day_stem, year_stem),
                     "hidden_stems": [{"stem": GAN[s], "index": s,
                                       "ten_god": _ten_god(day_stem, s)}
                                      for s in cu.HIDDEN_STEMS[year_branch]]},
            "month": {"stem": GAN[month_stem], "branch": ZHI[month_branch],
                      "stem_index": month_stem, "branch_index": month_branch,
                      "ten_god": _ten_god(day_stem, month_stem),
                      "hidden_stems": [{"stem": GAN[s], "index": s,
                                        "ten_god": _ten_god(day_stem, s)}
                                       for s in cu.HIDDEN_STEMS[month_branch]]},
            "day": {"stem": GAN[day_stem], "branch": ZHI[day_branch],
                    "stem_index": day_stem, "branch_index": day_branch,
                    "ten_god": "日主",
                    "hidden_stems": [{"stem": GAN[s], "index": s,
                                      "ten_god": _ten_god(day_stem, s)}
                                     for s in cu.HIDDEN_STEMS[day_branch]]},
            "hour": {"stem": GAN[hour_stem], "branch": ZHI[hour_branch_final],
                     "stem_index": hour_stem, "branch_index": hour_branch_final,
                     "ten_god": _ten_god(day_stem, hour_stem),
                     "hidden_stems": [{"stem": GAN[s], "index": s,
                                       "ten_god": _ten_god(day_stem, s)}
                                      for s in cu.HIDDEN_STEMS[hour_branch_final]]},
        }

        # 五行统计（四柱天干 + 地支藏干主气）
        wuxing = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        for key in ("year", "month", "day", "hour"):
            p = pillars[key]
            wuxing[_ELEMENT_NAMES[_ELEMENT_OF_STEM[p["stem_index"]]]] += 1
            main_hidden = p["hidden_stems"][0]
            wuxing[_ELEMENT_NAMES[_ELEMENT_OF_STEM[main_hidden["index"]]]] += 1

        return {
            "system": self.system,
            "engine_version": self.version,
            "input_echo": cu.build_input_echo(
                normalized, solar,
                {"bazi_subhour_rule": rule,
                 "lunar": cu.get_lunar_info(solar)}),
            "day_master": {"stem": GAN[day_stem], "element": ["木", "火", "土", "金", "水"][_ELEMENT_OF_STEM[day_stem]]},
            "pillars": pillars,
            "wuxing": wuxing,
        }