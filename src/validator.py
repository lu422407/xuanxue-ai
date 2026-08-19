"""事实校验层。

防止 AI 幻觉：对引擎输出的硬性规则做校验——
- 紫微：星曜亮度合法性（庙/旺/陷 与 宫位是否匹配）
- 四化：天干四化映射
- 宫位顺序等结构性规则

与 agents/critic.py 的区别：
- critic 校验「LLM 文本声称 vs 实际命盘」
- validator 校验「命盘本身是否违反硬性术数规则」
"""

from typing import Dict, List, Tuple

# 十四主星亮度规则（简化版：仅列出部分主星做示例，实际可扩展）
ZIWEI_BRIGHTNESS: Dict[str, Dict[str, List[str]]] = {
    "紫微": {"庙": ["子", "午"], "旺": ["卯", "酉"],
             "陷": ["丑", "未", "寅", "申", "辰", "戌", "巳", "亥"]},
    "天机": {"庙": ["子", "午"], "旺": ["寅", "申"],
             "陷": ["丑", "未", "卯", "酉", "辰", "戌", "巳", "亥"]},
    "太阳": {"庙": ["卯", "辰", "巳", "午"], "陷": ["亥", "子", "丑"]},
    "武曲": {"庙": ["辰", "戌", "丑", "未"], "旺": ["子", "午"], "陷": []},
}

SIHUA: Dict[str, Dict[str, str]] = {
    "甲": {"禄": "廉贞", "权": "破军", "科": "武曲", "忌": "太阳"},
    "乙": {"禄": "天机", "权": "天梁", "科": "紫微", "忌": "太阴"},
    "丙": {"禄": "天同", "权": "天机", "科": "文昌", "忌": "廉贞"},
    "丁": {"禄": "太阴", "权": "天同", "科": "天机", "忌": "巨门"},
    "戊": {"禄": "贪狼", "权": "太阴", "科": "右弼", "忌": "天机"},
    "己": {"禄": "武曲", "权": "贪狼", "科": "天梁", "忌": "文曲"},
    "庚": {"禄": "太阳", "权": "武曲", "科": "太阴", "忌": "天同"},
    "辛": {"禄": "巨门", "权": "太阳", "科": "文曲", "忌": "文昌"},
    "壬": {"禄": "天梁", "权": "紫微", "科": "左辅", "忌": "武曲"},
    "癸": {"禄": "破军", "权": "巨门", "科": "太阴", "忌": "贪狼"},
}


class FactValidator:
    """事实校验器。"""

    @classmethod
    def validate_ziwei(cls, chart: Dict) -> Tuple[bool, List[str]]:
        """校验紫微命盘：星曜亮度是否与宫位匹配。"""
        errors: List[str] = []
        for palace_name, palace in chart.get("palaces", {}).items():
            position = palace.get("position", "")
            for star in palace.get("major_stars", []):
                star_name = star.get("name", "")
                brightness = star.get("brightness", "")
                if star_name not in ZIWEI_BRIGHTNESS:
                    continue
                valid = ZIWEI_BRIGHTNESS[star_name]
                if brightness == "庙" and position not in valid.get("庙", []):
                    expected = cls._get_expected(star_name, position)
                    errors.append(
                        f"{star_name}在{position}不能为庙（应为{expected}）")
                elif brightness == "陷" and position not in valid.get("陷", []):
                    expected = cls._get_expected(star_name, position)
                    errors.append(
                        f"{star_name}在{position}不应为陷（应为{expected}）")
        return len(errors) == 0, errors

    @classmethod
    def _get_expected(cls, star: str, position: str) -> str:
        valid = ZIWEI_BRIGHTNESS.get(star, {})
        for brightness, positions in valid.items():
            if position in positions:
                return brightness
        return "平"

    @classmethod
    def validate_sihua(cls, day_gan: str, mutagen: str, star: str) -> bool:
        """校验四化：给定日干与化曜，星名是否正确。"""
        mapping = SIHUA.get(day_gan)
        if not mapping:
            return False
        return mapping.get(mutagen) == star

    @classmethod
    def validate_liuren(cls, chart: Dict) -> Tuple[bool, List[str]]:
        """六壬硬性校验（骨架，后续按四课三传规则扩展）。"""
        return True, []