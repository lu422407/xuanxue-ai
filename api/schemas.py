"""API 请求/响应 Schema。"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BirthInput(BaseModel):
    birth_datetime: str = Field(..., description="出生时间 YYYY-MM-DD HH:MM[:SS]")
    timezone_offset: float = Field(..., ge=-12, le=14, description="时区（相对 UTC 小时）")
    calendar: str = Field("solar", pattern="^(solar|lunar)$")
    gender: str = Field("男", description="性别（紫微引擎需要）")
    true_solar_time: bool = False
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    school: str = Field("zhongzhou")
    bazi_subhour_rule: str = Field("midnight", pattern="^(midnight|early_zi)$")


class ChartRequest(BaseModel):
    birth_input: BirthInput


class ChartResponse(BaseModel):
    system: str
    chart: Dict[str, Any]


class ChatRequest(BaseModel):
    question: str
    birth_input: Optional[BirthInput] = None


class ChatResponse(BaseModel):
    answer: str
    trace_id: str
    intent_type: str = ""
    validation: Dict[str, Any] = {}


class TraceResponse(BaseModel):
    trace_id: str
    spans: List[Dict[str, Any]]
    cost: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None


class OrchestrateRequest(BaseModel):
    """多术数 AI 编排请求（对应 agents.ai_orchestrator.AIOrchestrator）。"""

    question: str = Field(..., description="用户自然语言问题")
    user_context: Optional[Dict[str, Any]] = Field(
        None, description="可选上下文：birth_input / known_facts / preferences"
    )
    trace_id: Optional[str] = Field(None, description="可空，链路追踪 ID")


class EngineQueryRequest(BaseModel):
    """单术数查询请求（对应 agents.ai_orchestrator.AIOrchestrator.run_single）。"""

    birth_datetime: str = Field(..., description="出生时间 YYYY-MM-DD HH:MM[:SS]")
    timezone_offset: float = Field(8.0, ge=-12, le=14)
    calendar: str = Field("solar", pattern="^(solar|lunar)$")
    gender: str = Field("男")
    divination_datetime: Optional[str] = Field(
        None, description="占卜时刻（六壬用），缺省回落 birth_datetime"
    )
    known_facts: Optional[Dict[str, str]] = Field(
        None, description="已知事实（铁板考刻用，如 father_zodiac/mother_zodiac）"
    )


class OrchestrateResponse(BaseModel):
    """多术数编排响应（对应 AIOrchestratorResponse）。"""

    answer: str
    trace_id: Optional[str] = None
    systems_invoked: List[str] = []
    systems_skipped: List[Dict[str, Any]] = []
    engine_results: Dict[str, Any] = {}
    validation: Dict[str, Any] = {}
    synthesis: Dict[str, Any] = {}
    blocked_reason: Optional[str] = None
    disclaimer: str = ""


class EngineQueryResponse(BaseModel):
    """单术数查询响应。"""

    system: str
    available: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None