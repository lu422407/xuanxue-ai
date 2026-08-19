"""可解释加权评分（非伪精确百分比）。

强制要求（v3.2 文档 9.2 节）：
- 禁止输出"创业指数 82%"这类无法解释来源的精确百分比。
- 分数应为区间或档位（偏积极 / 中性 / 偏保守），且必须同时展示 factors 拆解。
- 每个权重必须有注释说明设定依据（来自哪部典籍/哪条规则）。
"""

from typing import Any, Dict, List, Optional


def _signal_value(weight: str) -> int:
    """档位分值：正向=+1，中性=0，偏弱=-1。依据：融合规则规则库 fusion_weight_001。"""
    if weight == "正向":
        return 1
    if weight == "偏弱" or weight == "中性偏弱":
        return -1
    return 0


def score_factors(factors: List[Dict[str, str]],
                  weight_basis: Optional[str] = None) -> Dict[str, Any]:
    """根据 factors 输出档位而非百分比。

    weight_basis: 权重设定依据说明（默认给出通用依据）。
    """
    if not factors:
        return {"tier": "信息不足", "basis": weight_basis}

    total = sum(_signal_value(f.get("weight", "中性")) for f in factors)
    ratio = total / len(factors)

    if ratio > 0.2:
        tier = "偏积极"
    elif ratio < -0.2:
        tier = "偏保守"
    else:
        tier = "中性"

    return {
        "tier": tier,
        "signal_count": {"正向": sum(1 for f in factors if f.get("weight") == "正向"),
                         "中性": sum(1 for f in factors if f.get("weight") == "中性"),
                         "偏弱": sum(1 for f in factors if f.get("weight") == "偏弱")},
        "factors": factors,
        "basis": weight_basis or "档位由各术数信号正负简单投票得出，仅作直观参考，不作精确量化。",
    }