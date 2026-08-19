"""Agent Orchestrator（含 Tracing 与 Cost Tracker）。

流程：
    用户问题 → Guardrails → Intent Router → Planner → Executor
    → LLM 生成 → Critic 校验 → Disclaimer → 输出
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents.critic import Critic
from agents.executor import Executor
from agents.guardrails import check as guardrails_check
from agents.guardrails import wrap_disclaimer
from agents.intent_router import IntentRouter
from agents.memory import MemoryAgent
from agents.planner import Planner
from observability.cost_tracker import cost_tracker
from observability.tracing import tracer


@dataclass
class OrchestratorResult:
    answer: str
    trace_id: str
    intent_type: str = ""
    validation: Dict[str, Any] = field(default_factory=dict)
    blocked_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "trace_id": self.trace_id,
            "intent_type": self.intent_type,
            "validation": self.validation,
            "blocked_reason": self.blocked_reason,
        }


class Orchestrator:
    def __init__(self, *, llm, router: Optional[IntentRouter] = None,
                 planner: Optional[Planner] = None, executor: Optional[Executor] = None,
                 critic: Optional[Critic] = None, memory: Optional[MemoryAgent] = None,
                 max_llm_calls: int = 5):
        self.llm = llm
        self.router = router or IntentRouter()
        self.planner = planner or Planner()
        self.executor = executor or Executor()
        self.critic = critic or Critic()
        self.memory = memory or MemoryAgent()
        self.max_llm_calls = max_llm_calls

    def run(self, question: str, user_context: Dict[str, Any],
            trace_id: Optional[str] = None) -> OrchestratorResult:
        trace_id = trace_id or tracer.new_trace_id()
        birth_input = user_context.get("birth_input", {})

        # 1. Guardrails
        with tracer.span(trace_id, "guardrails"):
            guard = guardrails_check(question)
            if guard.blocked:
                return OrchestratorResult(
                    answer=f"抱歉，您的请求包含不安全内容（{guard.category}），已被系统拦截。",
                    trace_id=trace_id, blocked_reason=guard.reason)

        # 2. Intent Router
        with tracer.span(trace_id, "intent_detection"):
            intent = self.router.detect(question, classifier=self.llm.classify if hasattr(self.llm, "classify") else None)
            if self.router.needs_clarification(intent):
                return OrchestratorResult(
                    answer="请补充说明您想了解的方向（例如：事业 / 财运 / 感情 / 排盘），以便给出更精准的分析。",
                    trace_id=trace_id, intent_type=intent.type)

        # 3. Planner
        with tracer.span(trace_id, "planning"):
            plan = self.planner.create(intent)
            if plan.exceeds_limit():
                return OrchestratorResult(
                    answer="执行计划过于复杂，请简化问题。", trace_id=trace_id)

        # 4. Execution（确定性计算）
        with tracer.span(trace_id, "execution"):
            engine_results = self.executor.run(plan, birth_input)
            if not engine_results:
                return OrchestratorResult(
                    answer="未能生成命盘，请确认出生信息完整（出生时间与时区）。",
                    trace_id=trace_id, intent_type=intent.type)

        # 5. LLM 生成（受 cost_tracker 次数上限约束）
        with tracer.span(trace_id, "llm_generation"):
            if cost_tracker.total_llm_calls(trace_id) >= self.max_llm_calls:
                return OrchestratorResult(
                    answer="本次分析已达到推理调用上限，请稍后重试。",
                    trace_id=trace_id, intent_type=intent.type)
            draft_answer = self._llm_generate(intent, engine_results, birth_input, trace_id)

        # 6. Validator
        with tracer.span(trace_id, "validation"):
            report = self.critic.validate(draft_answer, engine_results)
            if not report.passed:
                draft_answer = self._fallback_answer(engine_results, report.issues)

        # 7. Disclaimer + 输出
        final_answer = wrap_disclaimer(draft_answer)
        return OrchestratorResult(
            answer=final_answer, trace_id=trace_id, intent_type=intent.type,
            validation=report.to_dict())

    def _llm_generate(self, intent, engine_results: Dict[str, Any],
                      birth_input: Dict[str, Any], trace_id: str) -> str:
        system_prompt = (
            "你是一位术数文化知识助手。你只能基于给定的命盘结构化数据做解释，"
            "禁止编造或改动任何星曜、宫位、干支信息。"
            "命盘数据以 JSON 形式提供，请直接引用其中的内容。"
        )
        user_content = json.dumps({
            "intent": intent.type,
            "birth_input": birth_input,
            "charts": engine_results,
        }, ensure_ascii=False)
        response = self.llm.generate(system_prompt, user_content)
        cost_tracker.record(trace_id, engines=list(engine_results.keys()),
                            prompt_tokens=response.get("usage", {}).get("prompt_tokens", 0),
                            completion_tokens=response.get("usage", {}).get("completion_tokens", 0))
        return response["content"]

    @staticmethod
    def _fallback_answer(engine_results: Dict[str, Any], issues: List[str]) -> str:
        """校验失败时给出基于命盘数据的保守回答，绝不传播 AI 编造内容。"""
        parts = []
        for system, chart in engine_results.items():
            if system == "bazi":
                p = chart["pillars"]
                parts.append("四柱为 "
                             + " ".join(p[k]["stem"] + p[k]["branch"]
                                        for k in ("year", "month", "day", "hour")))
            elif system == "ziwei":
                soul = chart.get("soul", {})
                parts.append(f"命宫位于{soul.get('palace', '')}宫，主星为"
                             + "、".join(soul.get("star") or []))
        base = "以下命盘信息经核对确认：\n" + "\n".join(parts)
        base += "\n\nAI 分析内容未通过一致性校验，已替换为原始命盘数据供您参考。"
        base += "\n校验发现的问题：" + "；".join(issues)
        return base