"""Executor：执行 Planner 生成的计划。

只做确定性工作：调用 Engine 计算命盘、RAG 检索。
LLM 生成由 Orchestrator 单独调用。
"""

from typing import Any, Dict, List, Optional

from agents.planner import Plan
from engines.bazi_engine import BaziEngine
from engines.ziwei_engine import ZiWeiEngine

ENGINE_REGISTRY = {
    "bazi": BaziEngine,
    "ziwei": ZiWeiEngine,
}


class Executor:
    def __init__(self, engine_registry: Optional[Dict[str, Any]] = None):
        self._registry = engine_registry or ENGINE_REGISTRY

    def run(self, plan: Plan, birth_input: Dict[str, Any]) -> Dict[str, Any]:
        """执行计划，返回 {engine_name: chart_json}。"""
        if plan.exceeds_limit():
            raise RuntimeError(f"计划步骤超出上限 {plan.max_steps}")

        results: Dict[str, Any] = {}
        for step in plan.steps:
            if step.startswith("engine:"):
                name = step.split(":", 1)[1]
                if name in self._registry:
                    engine = self._registry[name]()
                    results[name] = engine.calculate(dict(birth_input))
            # rag_search / llm_generate 步骤在 Orchestrator 中处理
        return results