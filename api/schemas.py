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