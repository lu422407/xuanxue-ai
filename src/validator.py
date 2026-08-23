"""事实校验层。

防止 AI 幻觉：对引擎输出的硬性规则做校验——
- 紫微：星曜亮度合法性（庙/旺/陷 与 宫位是否匹配）
- 四化：天干四化映射
- 宫位顺序等结构性规则

与 agents/critic.py 的区别：
- critic 校验「LLM 文本声称 vs 实际命盘」
- validator 校验「命盘本身是否违反硬性术数规则」
"""

from typing import Dict, List, Set, Tuple

# 十四主星亮度规则 —— 全 14 星 × 12 宫 py-iztro 实测表。
# 数据来源：py-iztro 0.1.5（iztro-2.5.0，中州派）全枚举导出：
# 2 个年干 × 12 农历月 × 30 日 × 13 时辰（1440 盘），(星,宫)→亮度
# 为纯函数、零冲突。该表是 iztro 行为快照（升级 iztro 后由测试锚定
# 回归），不是独立命理考据。空档位省略（如紫微无陷、七杀无陷）。
ZIWEI_BRIGHTNESS: Dict[str, Dict[str, List[str]]] = {
    "紫微": {"庙": ["丑", "午", "未"], "旺": ["寅", "卯", "巳", "申", "酉", "亥"],
             "得": ["辰", "戌"], "平": ["子"]},
    "天机": {"庙": ["子", "午"], "旺": ["卯", "酉"], "得": ["寅", "申"],
             "利": ["辰", "戌"], "平": ["巳", "亥"], "陷": ["丑", "未"]},
    "太阳": {"庙": ["卯"], "旺": ["寅", "辰", "巳", "午"], "得": ["未", "申"],
             "不": ["丑", "戌"], "陷": ["子", "酉", "亥"]},
    "武曲": {"庙": ["丑", "辰", "未", "戌"], "旺": ["子", "午"], "得": ["寅", "申"],
             "利": ["卯", "酉"], "平": ["巳", "亥"]},
    "天同": {"庙": ["巳", "亥"], "旺": ["子", "申"], "利": ["寅"],
             "平": ["卯", "辰", "酉", "戌"], "不": ["丑", "未"], "陷": ["午"]},
    "廉贞": {"庙": ["寅", "申"], "利": ["丑", "辰", "未", "戌"],
             "平": ["子", "卯", "午", "酉"], "陷": ["巳", "亥"]},
    "天府": {"庙": ["子", "丑", "寅", "辰", "未", "戌"], "旺": ["午", "酉"],
             "得": ["巳", "卯", "亥", "申"]},
    "太阴": {"庙": ["亥", "子", "丑"], "旺": ["寅", "戌"],
             "利": ["申"], "不": ["午", "未", "酉"], "陷": ["卯", "辰", "巳"]},
    "贪狼": {"庙": ["丑", "辰", "未", "戌"], "旺": ["子", "午"],
             "利": ["卯", "酉"], "平": ["寅", "申"], "陷": ["巳", "亥"]},
    "巨门": {"庙": ["寅", "卯", "申", "酉"], "旺": ["子", "巳", "午", "亥"],
             "不": ["丑", "未"], "陷": ["辰", "戌"]},
    "天相": {"庙": ["子", "丑", "寅", "午", "申"], "得": ["巳", "辰", "未", "戌", "亥"],
             "陷": ["卯", "酉"]},
    "天梁": {"庙": ["子", "寅", "卯", "辰", "午", "戌"], "旺": ["丑", "未"],
             "得": ["酉"], "陷": ["巳", "申", "亥"]},
    "七杀": {"庙": ["寅", "丑", "辰", "未", "申", "酉", "戌"], "旺": ["子", "卯", "午"],
             "平": ["巳", "亥"]},
    "破军": {"庙": ["子", "午"], "旺": ["丑", "辰", "未", "戌"],
             "得": ["寅", "申"], "平": ["巳", "亥"], "陷": ["卯", "酉"]},
}

# 合法亮度档（空串 = 空宫无主星亮度）
BRIGHTNESS_LEVELS: Set[str] = {"庙", "旺", "得", "利", "平", "不", "陷", ""}

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
        """校验紫微命盘：主星亮度值合法，且与 (星,宫) 实测亮度表一致。

        引擎输出的主星为 {name, brightness} dict；旧字符串形态无亮度
        数据，跳过亮度校验（结构仍由 critic/check_logic 覆盖）。
        """
        errors: List[str] = []
        for palace_name, palace in chart.get("palaces", {}).items():
            position = palace.get("position", "")
            for star in palace.get("major_stars", []):
                if isinstance(star, str):
                    continue
                star_name = star.get("name", "")
                brightness = star.get("brightness", "")
                if brightness not in BRIGHTNESS_LEVELS:
                    errors.append(
                        f"{star_name}亮度值非法：'{brightness}'（合法：庙/旺/得/利/平/不/陷）")
                    continue
                if not brightness or star_name not in ZIWEI_BRIGHTNESS:
                    continue
                if position not in ZIWEI_BRIGHTNESS[star_name].get(brightness, []):
                    expected = cls._get_expected(star_name, position)
                    errors.append(
                        f"{star_name}在{position}不能为{brightness}（应为{expected}）")
        return len(errors) == 0, errors

    @classmethod
    def _get_expected(cls, star: str, position: str) -> str:
        valid = ZIWEI_BRIGHTNESS.get(star, {})
        for brightness, positions in valid.items():
            if position in positions:
                return brightness
        return "平"

    @classmethod
    def validate_brightness_table(cls) -> Tuple[bool, List[str]]:
        """校验亮度表自身的数据完整性：同一星曜同一宫位不得出现在两个亮度档。"""
        errors: List[str] = []
        for star, levels in ZIWEI_BRIGHTNESS.items():
            seen: Dict[str, str] = {}
            for brightness, positions in levels.items():
                for pos in positions:
                    if pos in seen:
                        errors.append(
                            f"亮度表冲突：{star}在{pos}同时列为'{seen[pos]}'与'{brightness}'"
                        )
                    else:
                        seen[pos] = brightness
        return len(errors) == 0, errors

    @classmethod
    def validate_sihua(cls, day_gan: str, mutagen: str, star: str) -> bool:
        """校验四化：给定日干与化曜，星名是否正确。"""
        mapping = SIHUA.get(day_gan)
        if not mapping:
            return False
        return mapping.get(mutagen) == star

    @classmethod
    def validate_liuren(cls, chart: Dict) -> Tuple[bool, List[str]]:
        """六壬硬性校验（结构层）：四课 4 项、三传 3 传、天地盘 12 支。

        课体吉凶等术数层规则后续扩展，此处先保证排盘结构不可能错位。
        """
        errors: List[str] = []
        si_ke = chart.get("四课")
        if isinstance(si_ke, dict) and len(si_ke) != 4:
            errors.append(f"四课应为 4 项，实际 {len(si_ke)} 项")
        san_chuan = chart.get("三传")
        if isinstance(san_chuan, dict):
            for key in ("初传", "中传", "末传"):
                if not san_chuan.get(key):
                    errors.append(f"三传缺少 {key}")
        tian_di_pan = chart.get("天地盘")
        if isinstance(tian_di_pan, dict) and len(tian_di_pan) != 12:
            errors.append(f"天地盘应为 12 地支，实际 {len(tian_di_pan)} 项")
        return len(errors) == 0, errors