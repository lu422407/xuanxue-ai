"""本地离线 LLM：基于命盘 JSON 的确定性回答。

无外部 API 依赖，便于本地演示与测试。
仅输出命盘真实存在的要素，天然通过 Critic 一致性校验。
"""

import json
from typing import Any, Dict

from llm.base import BaseLLM


class RuleBasedLLM(BaseLLM):
    provider = "local"
    model = "rule-based-v1"

    def generate(self, system_prompt: str, user_content: str, **kwargs) -> Dict[str, Any]:
        try:
            payload = json.loads(user_content)
        except json.JSONDecodeError:
            payload = {}

        charts = payload.get("charts", {})
        intent = payload.get("intent", "general")

        lines = []
        if "bazi" in charts:
            bazi = charts["bazi"]
            p = bazi["pillars"]
            lines.append(
                "八字四柱为 "
                + " ".join(p[k]["stem"] + p[k]["branch"]
                           for k in ("year", "month", "day", "hour"))
                + f"，日主为{p['day']['stem']}。")
        if "ziwei" in charts:
            ziwei = charts["ziwei"]
            soul = ziwei.get("soul", {})
            stars = "、".join(soul.get("star") or ["无主星"])
            lines.append(f"紫微命宫位于{soul.get('palace', '')}宫，命宫主星为{stars}。")

        if not lines:
            lines.append("暂无可分析的命盘数据，请先提供完整的出生信息。")

        topic_hint = {
            "career": "事业发展方向可结合日主喜忌与官禄宫综合判断。",
            "wealth": "财运分析可参考财帛宫与日主财星状态。",
            "relationship": "感情分析可参考夫妻宫与天同、天梁等星曜组合。",
            "life": "流年运势需结合大限与流年四化综合判断。",
            "chart": "命盘要素如下。",
        }.get(intent, "")

        content = "\n".join(lines) + ("\n" + topic_hint if topic_hint else "")
        return {
            "content": content,
            "model": self.model,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }