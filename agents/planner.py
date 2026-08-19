"""Planner：根据 Intent 生成执行计划。

限制单次请求最大步骤数，防止 Planner 规划出无限循环的执行计划
（配合 cost_tracker 的 LLM 调用次数上限）。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

MAX_STEPS = 8


@dataclass
class Plan:
    steps: List[str] = field(default_factory=list)  # 引擎名或 rag_search / llm_generate
    max_steps: int = MAX_STEPS

    def exceeds_limit(self) -> bool:
        return len(self.steps) > self.max_steps


class Planner:
    def __init__(self, max_steps: int = MAX_STEPS):
        self.max_steps = max_steps

    def create(self, intent) -> Plan:
        steps: List[str] = []
        for engine_name in intent.need:
            if engine_name in ("bazi", "ziwei"):
                steps.append(f"engine:{engine_name}")
        if intent.need:
            steps.append("rag_search")
        steps.append("llm_generate")
        return Plan(steps=steps, max_steps=self.max_steps)