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

# 奇门九星 / 八门 / 八神（宫位 JSON 中 star/gate/spirit 字段的取值域）
QIMEN_STARS = {
    "天蓬", "天芮", "天冲", "天辅", "天禽", "天心", "天柱", "天任", "天英",
}
QIMEN_GATES = {"休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门"}
QIMEN_SPIRITS = {
    "直符", "腾蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天",
}

# 六爻六神 / 六亲（yao 列表 spirit / mainRelative 等字段的取值域）
LIUYAO_SPIRITS = {"青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"}
LIUYAO_RELATIVES = {"兄弟", "子孙", "妻财", "官鬼", "父母"}


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
            elif system == "qimen":
                issues += self._check_qimen(draft_answer, chart)
            elif system == "liuyao":
                issues += self._check_liuyao(draft_answer, chart)
            elif system == "liuren":
                issues += self._check_liuren(draft_answer, chart)
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

    def _check_qimen(self, text: str, chart: Dict[str, Any]) -> List[str]:
        """奇门声称校验：九星 / 八门 / 八神必须真实存在于本盘宫位。"""
        palaces = chart.get("palaces") or []
        actual_stars = {p.get("star") for p in palaces if p.get("star")}
        actual_gates = {p.get("gate") for p in palaces if p.get("gate")}
        actual_spirits = {p.get("spirit") for p in palaces if p.get("spirit")}

        issues: List[str] = []
        for star in QIMEN_STARS:
            if star in text and star not in actual_stars:
                issues.append(f"九星声称不符：'{star}' 不在本奇门盘任何宫位")
        for gate in QIMEN_GATES:
            # 文本通常写"开门"，盘面字段值为单字"开"
            if gate in text and gate[:-1] not in actual_gates:
                issues.append(f"八门声称不符：'{gate}' 不在本奇门盘任何宫位")
        for spirit in QIMEN_SPIRITS:
            if spirit in text and spirit not in actual_spirits:
                issues.append(f"八神声称不符：'{spirit}' 不在本奇门盘任何宫位")
        return issues

    def _check_liuyao(self, text: str, chart: Dict[str, Any]) -> List[str]:
        """六爻声称校验：爻位-六神对应 / 六亲（X爻形式）/ 纳甲干支。

        六神按日干起排且六个爻位轮转覆盖全部六神，全局存在性校验无意义，
        必须校验"X爻临Y"的位置对应关系。
        """
        yaos = chart.get("yao") or []
        if isinstance(yaos, dict):
            yaos = list(yaos.values())

        actual_relatives = set()
        actual_ganzhi = set()
        for y in yaos:
            for rel_key in ("mainRelative", "hiddenRelative", "changedRelative"):
                if y.get(rel_key):
                    actual_relatives.add(y[rel_key])
            for pil_key in ("mainPillar", "hiddenPillar", "changedPillar"):
                pil = y.get(pil_key) or {}
                if pil.get("stem") and pil.get("branch"):
                    actual_ganzhi.add(pil["stem"] + pil["branch"])

        issues: List[str] = []
        # 1) 爻位-六神对应（yao 列表自下而上：初爻→上爻）
        pos_words = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]
        spirits_re = "|".join(sorted(LIUYAO_SPIRITS, key=len, reverse=True))
        for i, pos in enumerate(pos_words):
            m = re.search(rf"{pos}[^。；，！？]*?({spirits_re})", text)
            if m and i < len(yaos):
                actual = yaos[i].get("spirit")
                if actual and m.group(1) != actual:
                    issues.append(
                        f"六神声称不符：{pos}实际临'{actual}'，文中称'{m.group(1)}'"
                    )
        # 2) 六亲：仅校验"父母爻"这类明确指称，避免日常用语误伤
        for rel in LIUYAO_RELATIVES:
            if f"{rel}爻" in text and rel not in actual_relatives:
                issues.append(f"六亲声称不符：本卦没有'{rel}爻'")
        # 3) 纳甲干支
        for m in re.findall(rf"[{BAZI_GAN}][{BAZI_ZHI}]", text):
            if m not in actual_ganzhi:
                issues.append(f"纳甲干支声称不符：'{m}' 不在本卦纳甲中")
        return issues

    def _check_liuren(self, text: str, chart: Dict[str, Any]) -> List[str]:
        """六壬声称校验（轻量）：月将声称必须与本盘一致。"""
        actual_yuejiang = chart.get("月将")
        issues: List[str] = []
        if actual_yuejiang:
            m = re.search(rf"月将[为是]?\s*([{BAZI_ZHI}])", text)
            if m and m.group(1) != actual_yuejiang:
                issues.append(
                    f"月将声称不符：'{m.group(1)}' 与本盘月将 '{actual_yuejiang}' 不一致"
                )
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