"""Validator 主逻辑（Critic）。

检测 AI 输出与 Engine 实际命盘是否一致，防止 LLM 编造命盘要素。

校验模块：
- Chart Validator：核对 AI 输出中的星曜/干支是否真实存在于命盘
- Logic Validator：结构性逻辑校验
- Citation Validator：引用溯源校验（完整实现见 rag/citation_checker.py）
- Hallucination Validator / Safety Validator：预留扩展
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 紫微斗数十四主星（用于识别文本中的星曜声称）
ZIWEI_MAJOR_STARS = {
    "紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府",
    "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军",
}

BAZI_GAN = "甲乙丙丁戊己庚辛壬癸"
BAZI_ZHI = "子丑寅卯辰巳午未申酉戌亥"


@dataclass
class ValidationReport:
    passed: bool
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"passed": self.passed, "issues": self.issues}


class Critic:
    def validate(self, draft_answer: str, engine_results: Dict[str, Any]) -> ValidationReport:
        issues: List[str] = []
        for system, chart in engine_results.items():
            if system == "ziwei":
                issues += self._check_ziwei(draft_answer, chart)
            elif system == "bazi":
                issues += self._check_bazi(draft_answer, chart)
        return ValidationReport(passed=not issues, issues=issues)

    # ---- Chart Validator ----

    def _check_ziwei(self, text: str, chart: Dict[str, Any]) -> List[str]:
        palace_map = {
            name: set(p.get("major_stars", []))
            for name, p in chart.get("palaces", {}).items()
        }
        chart_stars = set()
        for stars in palace_map.values():
            chart_stars.update(stars)

        issues = []

        # 1) 宫位-星曜位置校验：形如"命宫主星为紫微""夫妻宫见天梁"的声称
        for match in re.finditer(
                r"(命宫|兄弟|夫妻|子女|财帛|疾厄|迁移|仆役|官禄|田宅|福德|父母)"
                r"宫?(?:主星|星曜|见|有|坐|落|在)?[是为有座坐]?[:：，,]?\s*([\u4e00-\u9fff]{1,12})",
                text):
            palace_name, claimed = match.group(1), match.group(2)
            actual = palace_map.get(palace_name, set())
            claimed_stars = [s for s in ZIWEI_MAJOR_STARS if s in claimed]
            if palace_name in palace_map and claimed_stars:
                for star in claimed_stars:
                    if star not in actual:
                        issues.append(
                            f"星曜位置声称不符：'{star}' 并不在{palace_name}宫（实际主星: "
                            + "、".join(sorted(actual)) + "）")

        # 2) 全局存在性校验：声称的星曜在命盘中不存在
        for star in ZIWEI_MAJOR_STARS:
            if star in text and star not in chart_stars:
                issues.append(f"星曜声称不符：'{star}' 不存在于本命盘任何宫位主星中")
        return issues

    def _check_bazi(self, text: str, chart: Dict[str, Any]) -> List[str]:
        valid_ganzhi = set()
        for pillar in chart.get("pillars", {}).values():
            valid_ganzhi.add(pillar["stem"] + pillar["branch"])

        issues = []
        matches = re.findall(rf"[{BAZI_GAN}][{BAZI_ZHI}]", text)
        for m in matches:
            if m not in valid_ganzhi:
                issues.append(f"干支声称不符：'{m}' 不在本八字四柱中")
        return issues

    # ---- Logic Validator ----

    def check_logic(self, result: Dict[str, Any]) -> List[str]:
        """结构化结果自身的逻辑一致性。"""
        issues = []
        for system, chart in result.items():
            if system == "ziwei":
                if len(chart.get("palaces", {})) != 12:
                    issues.append("紫微命盘宫位数不是 12")
        return issues

    # ---- 预留：Hallucination / Safety ----

    def check_hallucination(self, draft_answer: str, citations: Optional[List[str]] = None) -> List[str]:
        """占位：结合 citation_checker 实现完整溯源校验（Phase 4）。"""
        return []

    def check_safety(self, draft_answer: str) -> List[str]:
        """占位：安全校验（医疗/法律/财务等敏感承诺检测）。"""
        issues = []
        if re.search(r"(包治|保证.*(发财|治好|离婚)|一定.*(发财|成功))", draft_answer):
            issues.append("检测到绝对化承诺表述，需拒绝或弱化")
        return issues