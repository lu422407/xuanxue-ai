"""AI Orchestrator（术数 AI 编排层，Phase A 实现）。

定位：在 `router / engine / validator` 之上的顶层编排。
核心原则：**LLM 不负责计算**。LLM 只负责理解问题、选择术数、调用引擎、
综合结果、生成解释。确定性排盘全部由 `engines.*` 完成。

本模块严格贯彻 docs/AI_ORCHESTRATOR_DESIGN.md 的设计：
- 复用 `src.router.XuanXueRouter`（术数类型选择，不重写）
- 复用 `src.validator.FactValidator`（硬性规则校验，不重写）
- 复用 `agents.guardrails`（注入拦截 + 免责声明）
- 复用 `agents.critic.Critic`（LLM 文本 vs 命盘一致性）
- 复用 `agents.intent_router.IntentRouter`（话题意图）

LLM 为可选项（默认 None）：无 LLM 时 Explainer 走确定性文本摘要，
保证离线、可测试、不编造命盘要素。
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from agents.critic import Critic, ValidationReport
from agents.guardrails import check as guardrails_check
from agents.guardrails import DISCLAIMER, wrap_disclaimer
from agents.intent_router import IntentRouter
from engines import (
    BaziEngine,
    LiuRenEngine,
    LiuYaoEngine,
    QiMenEngine,
    TieBanEngine,
)
from engines.base import EngineError
from engines.ziwei_process import ZiWeiProcessEngine
from rag.knowledge_loader import load_knowledge
from rag.retriever import Retriever, _bigrams
from src.router import XuanXueRouter
from src.validator import FactValidator

logger = logging.getLogger(__name__)

# 路由中文术数名 → 引擎 system key
_METHOD_TO_SYSTEM = {
    "紫微斗数": "ziwei",
    "大六壬": "liuren",
    "八字": "bazi",
    "铁板神数": "tieban",
    "奇门遁甲": "qimen",
    "六爻": "liuyao",
    "风水": None,
    "太乙神数": None,
}

# 引擎 system key → 引擎类
# ziwei 用进程代理引擎（ZiWeiProcessEngine），规避 pythonmonkey 在
# Windows 非主线程（API 线程池 / TestClient）下的崩溃。
_SYSTEM_TO_ENGINE = {
    "ziwei": ZiWeiProcessEngine,
    "liuren": LiuRenEngine,
    "bazi": BaziEngine,
    "tieban": TieBanEngine,
    "qimen": QiMenEngine,
    "liuyao": LiuYaoEngine,
}

# 时辰名 → 起始小时（用于自然语言时辰解析）
_HOUR_MAP = {
    "子时": 0, "丑时": 2, "寅时": 4, "卯时": 6, "辰时": 8, "巳时": 10,
    "午时": 12, "未时": 14, "申时": 16, "酉时": 18, "戌时": 20, "亥时": 22,
}

# ---- Phase B：五行生克映射（纯函数，供八字↔紫微交叉印证） ----

TIAN_GAN_WUXING: Dict[str, str] = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
DI_ZHI_WUXING: Dict[str, str] = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
# 十四主星五行（通行归属，《紫微斗数全书》）
MAJOR_STAR_WUXING: Dict[str, str] = {
    "紫微": "土", "天机": "木", "太阳": "火", "武曲": "金", "天同": "水",
    "廉贞": "火", "天府": "土", "太阴": "水", "贪狼": "木", "巨门": "土",
    "天相": "水", "天梁": "土", "七杀": "金", "破军": "水",
}
WUXING_SHENG: Dict[str, str] = {
    "木": "火", "火": "土", "土": "金", "金": "水", "水": "木",
}
WUXING_KE: Dict[str, str] = {
    "木": "土", "土": "水", "水": "火", "火": "金", "金": "木",
}


def wuxing_relation(a: str, b: str) -> str:
    """a 对 b 的五行关系描述（比和 / 相生 / 相克）。"""
    if a == b:
        return "比和"
    if WUXING_SHENG.get(a) == b:
        return f"{a}生{b}"
    if WUXING_SHENG.get(b) == a:
        return f"{b}生{a}"
    if WUXING_KE.get(a) == b:
        return f"{a}克{b}"
    return f"{b}克{a}"


def cross_validate_bazi_ziwei(
    bazi_chart: Dict[str, Any], ziwei_chart: Dict[str, Any]
) -> tuple:
    """八字日主 ↔ 紫微命宫交叉印证（纯比对）。

    仅陈述两系统间的五行生克事实，不下吉凶结论——
    判断留给人 / LLM 解释层，编排层保证事实可复核。
    """
    consensus: List[str] = []
    day_stem = ((bazi_chart.get("pillars") or {}).get("day") or {}).get("stem")
    ming = (ziwei_chart.get("palaces") or {}).get("命宫") or {}
    position = ming.get("position")
    stars = ming.get("major_stars") or []
    if not day_stem or not position:
        return consensus
    day_wx = TIAN_GAN_WUXING.get(day_stem)
    palace_wx = DI_ZHI_WUXING.get(position)
    if day_wx and palace_wx:
        consensus.append(
            f"八字日主{day_stem}属{day_wx}，紫微命宫居{position}属{palace_wx}，"
            f"五行关系：{wuxing_relation(day_wx, palace_wx)}"
        )
    if stars and day_wx:
        star = stars[0] if isinstance(stars[0], str) else stars[0].get("name", "")
        star_wx = MAJOR_STAR_WUXING.get(star)
        if star_wx:
            consensus.append(
                f"日主{day_stem}({day_wx})与命宫主星{star}({star_wx})，"
                f"五行关系：{wuxing_relation(day_wx, star_wx)}"
            )
    return consensus


@dataclass
class EngineCall:
    """单次引擎调用记录（供测试断言与可观测性）。"""

    system: str
    input: Dict[str, Any]
    available: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class SynthesisResult:
    """跨术数综合结果（纯比对，无 LLM，不计算）。"""

    consensus: List[str] = field(default_factory=list)
    divergences: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consensus": self.consensus,
            "divergences": self.divergences,
            "citations": self.citations,
        }


@dataclass
class OrchestratorRequest:
    """编排层请求。"""

    question: str
    user_context: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None


@dataclass
class AIOrchestratorResponse:
    """编排层响应（结构化，前端 / API 可直接序列化）。"""

    answer: str
    trace_id: Optional[str]
    systems_invoked: List[str]
    systems_skipped: List[Dict[str, Any]]
    engine_results: Dict[str, Any]
    validation: Dict[str, Any]
    synthesis: Dict[str, Any]
    blocked_reason: Optional[str]
    disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "trace_id": self.trace_id,
            "systems_invoked": self.systems_invoked,
            "systems_skipped": self.systems_skipped,
            "engine_results": self.engine_results,
            "validation": self.validation,
            "synthesis": self.synthesis,
            "blocked_reason": self.blocked_reason,
            "disclaimer": self.disclaimer,
        }


class AIOrchestrator:
    """跨术数顶层编排器。

    LLM 通过构造参数注入（生产用真实 BaseLLM，测试用 FakeLLM），
    缺省为 None → 离线确定性模式。
    """

    def __init__(
        self,
        llm: Any = None,
        router: Optional[XuanXueRouter] = None,
        guardrails_fn: Optional[Callable[[str], Any]] = None,
        critic: Optional[Critic] = None,
        validator: Optional[FactValidator] = None,
        intent_router: Optional[IntentRouter] = None,
        retriever: Optional[Retriever] = None,
    ) -> None:
        self.llm = llm
        self.router = router or XuanXueRouter()
        self._guard = guardrails_fn or guardrails_check
        self.critic = critic or Critic()
        self.validator = validator or FactValidator()
        self.intent_router = intent_router or IntentRouter()
        # Phase E：RAG 检索器（可注入；缺省懒加载 knowledge/ 知识库）
        self.retriever = retriever

    # ---- 顶层入口 ----

    def run(self, request: Any) -> AIOrchestratorResponse:
        if isinstance(request, dict):
            request = OrchestratorRequest(
                question=request.get("question", ""),
                user_context=request.get("user_context"),
                trace_id=request.get("trace_id"),
            )

        # ① Shield —— 注入拦截
        guard = self._guard(request.question)
        if guard.blocked:
            return self._blocked_response(guard, request)

        # ② Understander —— 题意识别 + 参数抽取（无 LLM 计算）
        intent = self.intent_router.detect(request.question)
        parsed_params = self._extract_birth_params(request)
        known_facts = self._collect_known_facts(request, parsed_params)

        # ③ Selector —— 术数类型选择（融合路由 + 话题意图）
        selected = self._select(request.question, intent)

        # ④ Dispatcher —— 确定性引擎计算（LLM 不参与）
        calls = self._dispatch(selected, parsed_params, known_facts)
        engine_results = {c.system: c.result for c in calls if c.result is not None}
        skipped = [
            {"system": c.system, "reason": c.error}
            for c in calls
            if c.result is None
        ]

        # ⑤ Validator —— 硬性规则校验
        validation = self._validate(engine_results)

        # ⑥ Synthesizer —— 跨术数交叉印证（纯比对）
        synthesis = self._synthesize(engine_results)

        # ⑥.5 Phase E：RAG 溯源 —— 填充可校验的古籍引用（增强信息，失败不阻断）
        try:
            synthesis.citations.extend(
                self._collect_citations(request.question, engine_results)
            )
        except Exception as exc:
            logger.warning("RAG 引用收集失败（不影响主链路）: %s", exc)

        # ⑦ Explainer —— LLM 生成解释（失败回退原始命盘）
        answer = self._explain(engine_results, synthesis, validation)

        # 引用附于 Critic 校验之后：引用来自知识库本身，可由 citation_checker 复核
        if synthesis.citations:
            answer += "\n参考：\n" + "\n".join(
                f"- {c}" for c in synthesis.citations
            )

        # ⑧ Disclaimer —— 注入免责声明
        answer = wrap_disclaimer(answer)

        return AIOrchestratorResponse(
            answer=answer,
            trace_id=request.trace_id,
            systems_invoked=list(engine_results.keys()),
            systems_skipped=skipped,
            engine_results=engine_results,
            validation=validation,
            synthesis=synthesis.to_dict(),
            blocked_reason=None,
            disclaimer=DISCLAIMER,
        )

    # ---- ② Understander 辅助 ----

    def _extract_birth_params(self, request: OrchestratorRequest) -> Dict[str, Any]:
        """宽容抽取出生参数（兼容 router 原逻辑，并补齐其未覆盖的格式）。

        不修改 src/router.py：这里在编排层叠加一层更鲁棒的解析，
        支持「YYYY年阳历/阴历M月D日」年/月夹字、点位/时辰，
        并允许 user_context.birth_input 显式覆盖。
        """
        params: Dict[str, Any] = {}
        text = request.question or ""

        # 1) 兼容 router 既有抽取
        try:
            params.update(self.router._extract_params(text))
        except Exception:
            pass

        # 2) 补抽：YYYY年(阳历|阴历|农历)?M月D日
        if "year" not in params:
            m = re.search(
                r"(\d{4})\s*年\s*(阳历|阴历|农历)?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text
            )
            if m:
                params["year"] = int(m.group(1))
                params["month"] = int(m.group(3))
                params["day"] = int(m.group(4))
                params["date_type"] = "lunar" if m.group(2) in ("农历", "阴历") else "solar"

        # 3) 时辰 / 点位
        if "hour" not in params:
            hm = re.search(r"(\d{1,2}):(\d{2})", text)
            if hm:
                params["hour"] = int(hm.group(1))
            else:
                hm2 = re.search(r"(\d{1,2})\s*点", text)
                if hm2:
                    params["hour"] = int(hm2.group(1))
                else:
                    for name, hour in _HOUR_MAP.items():
                        if name in text:
                            params["hour"] = hour
                            break

        # 4) 性别
        if "gender" not in params:
            if "男" in text:
                params["gender"] = "男"
            elif "女" in text:
                params["gender"] = "女"

        # 5) user_context.birth_input 覆盖（设计稿请求协议支持）
        ctx = request.user_context or {}
        bi = ctx.get("birth_input")
        if isinstance(bi, dict):
            for k in ("year", "month", "day", "hour", "gender", "calendar",
                      "timezone_offset", "divination_datetime"):
                if bi.get(k) is not None:
                    params[k] = bi[k]
            if bi.get("calendar"):
                params["date_type"] = bi["calendar"]

        # 6) user_context 顶层 divination_datetime（设计稿请求协议 3.1）
        if params.get("divination_datetime") is None and ctx.get("divination_datetime"):
            params["divination_datetime"] = ctx["divination_datetime"]

        return params

    def _collect_known_facts(
        self, request: OrchestratorRequest, parsed_params: Dict[str, Any]
    ) -> Dict[str, str]:
        facts: Dict[str, str] = {}
        ctx = request.user_context or {}
        if isinstance(ctx.get("known_facts"), dict):
            facts.update({k: str(v) for k, v in ctx["known_facts"].items()})
        if isinstance(parsed_params.get("known_facts"), dict):
            facts.update({k: str(v) for k, v in parsed_params["known_facts"].items()})
        return facts

    # ---- ③ Selector ----

    def _select(self, question: str, intent: Any) -> List[str]:
        systems: List[str] = []
        routed = self.router.route(question)
        method = routed.get("method")
        if method and method != "unknown":
            sys_key = _METHOD_TO_SYSTEM.get(method)
            if sys_key:
                systems.append(sys_key)
        # 融合话题意图所需术数（career/wealth/... → bazi/ziwei）
        for need in getattr(intent, "need", []) or []:
            if need not in systems:
                systems.append(need)
        # 去重保序
        seen: set = set()
        out: List[str] = []
        for s in systems:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    # ---- ④ Dispatcher ----

    def _dispatch(
        self, systems: List[str], parsed_params: Dict[str, Any], known_facts: Dict[str, str]
    ) -> List[EngineCall]:
        calls: List[EngineCall] = []
        for system in systems:
            engine_cls = _SYSTEM_TO_ENGINE.get(system)
            if engine_cls is None:
                calls.append(
                    EngineCall(
                        system=system, input={}, available=False,
                        error="该术数暂未接入引擎",
                    )
                )
                continue
            try:
                engine_input = self.router.build_input(parsed_params)
            except ValueError as ve:
                calls.append(
                    EngineCall(
                        system=system, input={}, available=False,
                        error=f"缺少出生日期参数：{ve}",
                    )
                )
                continue
            # 六壬：占卜时刻由 divination_datetime 决定（缺省回落 birth_datetime）
            if system == "liuren" and parsed_params.get("divination_datetime"):
                engine_input = dict(engine_input)
                engine_input["divination_datetime"] = parsed_params["divination_datetime"]
            try:
                engine = engine_cls()
                if system == "tieban" and known_facts:
                    result = engine.verify_kefen(engine_input, known_facts)
                else:
                    result = engine.calculate(engine_input)
                calls.append(
                    EngineCall(system=system, input=engine_input, available=True, result=result)
                )
            except EngineError as ee:
                # 引擎不可用（如奇门/六爻 CLI 未编译）→ 优雅降级
                calls.append(
                    EngineCall(
                        system=system, input=engine_input, available=False,
                        error=f"引擎计算失败：{ee.message}",
                    )
                )
            except Exception as exc:  # 其他异常同样不向上抛，记录为跳过
                calls.append(
                    EngineCall(
                        system=system, input=engine_input, available=False,
                        error=f"引擎异常：{exc}",
                    )
                )
        return calls

    # ---- ⑤ Validator ----

    def _validate(self, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[str] = []
        internal_errors: List[str] = []
        for system, chart in engine_results.items():
            try:
                if system == "ziwei":
                    ok, errs = self.validator.validate_ziwei(chart)
                    issues += [f"[ziwei] {e}" for e in errs]
                elif system == "liuren":
                    ok, errs = self.validator.validate_liuren(chart)
                    issues += [f"[liuren] {e}" for e in errs]
            except Exception as exc:
                # 校验子系统异常不应中断编排；单独记录，便于后续修复
                internal_errors.append(f"[{system}] validator 异常：{exc}")
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "internal_errors": internal_errors,
        }

    # ---- ⑥ Synthesizer ----

    def _synthesize(self, engine_results: Dict[str, Any]) -> SynthesisResult:
        consensus: List[str] = []
        divergences: List[str] = []
        citations: List[str] = []

        # 跨术数输入出生时间一致性比对（真实可验证）
        echoes: Dict[str, str] = {}
        for system, chart in engine_results.items():
            echo = chart.get("input_echo") or (chart.get("base_chart") or {}).get("input_echo") or {}
            dt = echo.get("birth_datetime")
            if dt:
                echoes[system] = dt
        if len(echoes) >= 2:
            if len(set(echoes.values())) == 1:
                consensus.append(f"各术数输入出生时间一致：{next(iter(echoes.values()))}")
            else:
                divergences.append(f"术数间出生时间不一致：{echoes}")

        # 各术数已生成命盘（事实声明，非结论）
        for system in engine_results:
            consensus.append(f"已生成 {system} 命盘")

        # 交叉印证：八字日主 ↔ 紫微命宫五行生克（Phase B，纯比对事实）
        bazi_chart = engine_results.get("bazi")
        ziwei_chart = engine_results.get("ziwei")
        if bazi_chart and ziwei_chart:
            consensus.extend(cross_validate_bazi_ziwei(bazi_chart, ziwei_chart))
        elif bazi_chart or ziwei_chart:
            consensus.append("跨术数交叉印证数据部分可用（部分缺失）")

        return SynthesisResult(consensus=consensus, divergences=divergences, citations=citations)

    # ---- ⑥.5 RAG 溯源（Phase E） ----

    def _ensure_retriever(self) -> Optional[Retriever]:
        if self.retriever is None:
            retriever = Retriever()
            load_knowledge(retriever)
            self.retriever = retriever
        return self.retriever

    def _collect_citations(
        self,
        question: str,
        engine_results: Dict[str, Any],
        top_k: int = 3,
        min_score: float = 0.12,
    ) -> List[str]:
        """检索古籍/规则知识，返回带 [source:id] 的引用串（可被 citation_checker 校验）。

        过滤策略：哈希向量存在 ~0.1 的噪声基线，故要求文档与查询
        有字面 bigram 重叠且总分达到阈值，避免无关问题引出"古籍"。
        """
        retriever = self._ensure_retriever()
        if retriever is None:
            return []

        zh_names = {
            "bazi": "八字", "ziwei": "紫微斗数", "liuren": "大六壬",
            "tieban": "铁板神数", "qimen": "奇门遁甲", "liuyao": "六爻",
        }
        parts: List[str] = [question]
        parts += [zh_names[s] for s in engine_results if s in zh_names]
        ziwei = engine_results.get("ziwei") or {}
        stars = ((ziwei.get("palaces") or {}).get("命宫") or {}).get("major_stars") or []
        if stars:
            first = stars[0] if isinstance(stars[0], str) else stars[0].get("name", "")
            if first:
                parts.append(first)
        bazi = engine_results.get("bazi") or {}
        day_stem = ((bazi.get("pillars") or {}).get("day") or {}).get("stem")
        if day_stem:
            parts.append(day_stem)
        query = " ".join(parts)

        query_bigrams = _bigrams(query)
        if not query_bigrams:
            return []
        citations: List[str] = []
        for hit in retriever.retrieve(query, top_k=8):
            if hit["score"] < min_score:
                continue
            if not (query_bigrams & _bigrams(hit["text"])):
                continue
            meta = hit.get("metadata") or {}
            title = meta.get("title") or hit["doc_id"]
            reference = meta.get("reference") or ""
            ref_part = f"（{reference}）" if reference else ""
            citations.append(f"{title}{ref_part}[source:{hit['doc_id']}]")
            if len(citations) >= top_k:
                break
        return citations

    # ---- ⑦ Explainer ----

    def _explain(
        self,
        engine_results: Dict[str, Any],
        synthesis: SynthesisResult,
        validation: Dict[str, Any],
    ) -> str:
        if self.llm is not None:
            try:
                text = self._llm_explain(engine_results, synthesis)
            except Exception:
                text = self._text_summary(engine_results, synthesis)
        else:
            text = self._text_summary(engine_results, synthesis)

        # Critic：若 LLM 文本与命盘不符，回退原始命盘摘要（绝不传播编造内容）
        report: ValidationReport = self.critic.validate(text, engine_results)
        if not report.passed and self.llm is not None:
            text = self._text_summary(engine_results, synthesis)
        return text

    def _llm_explain(self, engine_results: Dict[str, Any], synthesis: SynthesisResult) -> str:
        system_prompt = (
            "你是传统术数文化研究助手。仅依据下方各引擎输出的结构化命盘数据，"
            "用自然语言归纳用户关心的要点。严禁编造星曜、宫位、干支或结论。"
        )
        user_content = (
            f"综合结果：{synthesis.to_dict()}\n"
            f"各引擎命盘数据：{engine_results}"
        )
        resp = self.llm.generate(system_prompt, user_content)
        return resp.get("content", "")

    @staticmethod
    def _text_summary(engine_results: Dict[str, Any], synthesis: SynthesisResult) -> str:
        """确定性文本摘要：只回显引擎真实字段，不编造。"""
        lines: List[str] = []
        for system, chart in engine_results.items():
            lines.append(f"【{system}】")
            if system == "ziwei":
                ming = chart.get("palaces", {}).get("命宫", {})
                stars = ming.get("major_stars", [])
                lines.append(f"命宫主星：{', '.join(stars) if stars else '无'}")
            elif system == "bazi":
                pillars = chart.get("pillars", {})
                if pillars:
                    parts = [f"{k}:{v.get('stem', '')}{v.get('branch', '')}" for k, v in pillars.items()]
                    lines.append("四柱：" + " ".join(parts))
            elif system == "tieban":
                vk = chart.get("verified_ke")
                if vk is not None:
                    lines.append(
                        f"考刻定分：{chart.get('kefen_string', '')}"
                        f"（匹配事实：{chart.get('matched_facts')}）"
                    )
                else:
                    lines.append(f"可用条文数：{chart.get('tiaowen_count')}")
            elif system == "liuren":
                lines.append("已生成六壬四课三传。")
            else:
                lines.append("已生成命盘。")

        if synthesis.consensus:
            lines.append("综合：" + "；".join(synthesis.consensus))
        if synthesis.divergences:
            lines.append("分歧：" + "；".join(synthesis.divergences))
        return "\n".join(lines)

    # ---- 单术数入口（供 API 层复用） ----

    def run_single(
        self, system: str, input_data: Dict[str, Any], known_facts: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """单术数调用：返回 {available, result?, error?}。

        与 Dispatcher 逻辑一致，供 API /api/engine/{system} 复用，
        对 EngineError（未编译/参数缺失等）做优雅降级。
        """
        engine_cls = _SYSTEM_TO_ENGINE.get(system)
        if engine_cls is None:
            return {"available": False, "error": "该术数暂未接入引擎"}
        try:
            engine = engine_cls()
            if system == "tieban" and known_facts:
                result = engine.verify_kefen(input_data, known_facts)
            else:
                result = engine.calculate(input_data)
            return {"available": True, "result": result}
        except EngineError as ee:
            return {"available": False, "error": f"引擎计算失败：{ee.message}"}
        except Exception as exc:
            return {"available": False, "error": f"引擎异常：{exc}"}

    # ---- ① 拦截响应 ----

    def _blocked_response(self, guard: Any, request: OrchestratorRequest) -> AIOrchestratorResponse:
        msg = f"请求被安全策略拦截（{guard.category}）：{guard.reason}"
        return AIOrchestratorResponse(
            answer=wrap_disclaimer(msg),
            trace_id=request.trace_id,
            systems_invoked=[],
            systems_skipped=[],
            engine_results={},
            validation={"passed": True, "issues": []},
            synthesis=SynthesisResult().to_dict(),
            blocked_reason=msg,
            disclaimer=DISCLAIMER,
        )
