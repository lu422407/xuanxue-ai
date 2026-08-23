"""多术融合：Career Analyzer。

输入：八字 / 紫微 / 奇门的结构化结果。
输出：可解释拆解（factors），而非单一伪精确数字（见 v3.2 文档 9.2 节）。
"""

from typing import Any, Dict, List


def analyze_career(charts: Dict[str, Any]) -> Dict[str, Any]:
    """事业融合分析骨架。各引擎信号在此汇总为可解释因素列表。"""
    factors: List[Dict[str, str]] = []
    if "bazi" in charts:
        p = charts["bazi"].get("pillars", {})
        month_god = p.get("month", {}).get("ten_god", "")
        factors.append({
            "source": "bazi",
            "signal": f"月干十神为{month_god}",
            "weight": "中性",
        })
    if "ziwei" in charts:
        career_palace = charts["ziwei"].get("palaces", {}).get("官禄", {})
        stars = career_palace.get("major_stars", [])
        star_names = [s["name"] if isinstance(s, dict) else s for s in stars]
        factors.append({
            "source": "ziwei",
            "signal": "官禄宫主星" + ("、".join(star_names) if star_names else "无主星"),
            "weight": "中性",
        })
    return {
        "topic": "career",
        "factors": factors,
        "summary": "各命盘要素已列出，具体判断需结合完整命盘综合权衡。",
        "disclaimer": "以上为传统术数文化推演，不构成职业决策建议。",
    }