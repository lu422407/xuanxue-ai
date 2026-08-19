"""FastAPI 应用。

鉴权 + 限流 + Tracing + Cost Tracker + 数据主权（删除命盘）。
"""

from typing import Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException

from agents.critic import Critic
from agents.executor import Executor
from agents.memory import MemoryAgent
from agents.orchestrator import Orchestrator
from api.auth import authenticate
from api.rate_limit import default_limiter
from api.schemas import (
    ChartRequest,
    ChartResponse,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    TraceResponse,
)
from engines.base import EngineError
from engines.bazi_engine import BaziEngine
from engines.ziwei_process import ZiWeiProcessEngine, calculate_ziwei
from llm.local import RuleBasedLLM
from observability.cost_tracker import cost_tracker
from observability.tracing import tracer

app = FastAPI(title="术数 AI Engine Pro", version="0.1.0")


def _require_auth(x_api_key: Optional[str] = Header(None)) -> str:
    """鉴权依赖：未提供/非法 API Key 直接 401。"""
    key = authenticate(x_api_key)
    if key is None:
        raise HTTPException(status_code=401, detail="未授权：请提供有效的 X-API-Key")
    return key


def _check_rate_limit(api_key: str) -> None:
    if not default_limiter.check(api_key):
        raise HTTPException(
            status_code=429,
            detail={"code": "rate_limit_exceeded",
                    "message": "请求过于频繁，请稍后重试"},
        )


def _build_orchestrator() -> Orchestrator:
    # API 线程池中使用进程代理引擎，规避 pythonmonkey 非主线程崩溃
    executor = Executor(engine_registry={"bazi": BaziEngine, "ziwei": ZiWeiProcessEngine})
    return Orchestrator(llm=RuleBasedLLM(), critic=Critic(),
                        executor=executor, memory=MemoryAgent())


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "xuanxue-ai"}


@app.post("/api/chart", response_model=ChartResponse)
def create_chart(req: ChartRequest, api_key: str = Depends(_require_auth)):
    """创建命盘（确定性计算，无 LLM）。"""
    _check_rate_limit(api_key)
    birth = req.birth_input.model_dump()
    charts: Dict[str, dict] = {}
    try:
        charts["bazi"] = BaziEngine().calculate({
            k: birth[k] for k in ("birth_datetime", "timezone_offset", "calendar",
                                  "true_solar_time", "longitude", "bazi_subhour_rule")
            if birth.get(k) is not None})
        charts["ziwei"] = calculate_ziwei({
            k: birth[k] for k in ("birth_datetime", "timezone_offset", "calendar",
                                  "true_solar_time", "longitude", "school", "gender")
            if birth.get(k) is not None})
    except EngineError as exc:
        raise HTTPException(status_code=422, detail=ErrorResponse(
            code=exc.code, message=exc.message).model_dump())
    return {"system": "ziwei+bazi", "chart": charts}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, api_key: str = Depends(_require_auth)):
    """对话分析：Guardrails → Intent → Engine → LLM → Validator。"""
    _check_rate_limit(api_key)
    orch = _build_orchestrator()
    birth = req.birth_input.model_dump() if req.birth_input else {}
    result = orch.run(req.question, {"birth_input": birth})
    return {"answer": result.answer, "trace_id": result.trace_id,
            "intent_type": result.intent_type, "validation": result.validation}


@app.get("/api/analyze/{trace_id}", response_model=TraceResponse)
def get_trace(trace_id: str, api_key: str = Depends(_require_auth)):
    """按 trace_id 追溯完整执行链路。"""
    spans = tracer.get_trace(trace_id)
    if not spans:
        raise HTTPException(status_code=404, detail="trace_id 不存在")
    return {"trace_id": trace_id, "spans": spans,
            "cost": cost_tracker.get(trace_id)}


@app.delete("/api/chart/{chart_id}")
def delete_chart(chart_id: int, api_key: str = Depends(_require_auth)):
    """数据主权：用户删除自己的命盘（内存版实现）。"""
    orch = _build_orchestrator()
    # 生产环境：校验归属后级联删除数据库记录与 Memory 记录
    orch.memory.delete_user(api_key)
    return {"deleted": True, "chart_id": chart_id}