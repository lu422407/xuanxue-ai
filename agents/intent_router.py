"""Intent Router。

不使用关键词匹配，使用 LLM 分类 + 结构化输出。
confidence 低于阈值（如 0.6）时，Orchestrator 应主动追问用户澄清，
而不是强行猜测执行。

design: detect(question, classifier) 中的 classifier 为可调用对象，
接收 question 返回 {"type":..., "need":[...], "confidence":...}。
生产环境使用 LLM 结构化输出；测试可使用 FakeClassifier。
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.6

INTENT_TYPES = {"career", "wealth", "relationship", "life", "chart", "general"}

_NEED_BY_TYPE = {
    "career": ["bazi", "ziwei"],
    "wealth": ["bazi", "ziwei"],
    "relationship": ["ziwei"],
    "life": ["bazi", "ziwei"],
    "chart": ["ziwei"],
    "general": [],
}

_HEURISTIC_KEYWORDS = [
    ("career", ["事业", "工作", "职业", "升职", "创业", "财运不佳", "跳槽"]),
    ("wealth", ["财运", "财富", "赚钱", "投资", "股票"]),
    ("relationship", ["感情", "婚姻", "恋爱", "姻缘", "另一半"]),
    ("life", ["运势", "流年", "健康", "大运", "总体"]),
    ("chart", ["排盘", "命盘", "看盘", "紫微盘", "八字盘"]),
]


@dataclass
class IntentResult:
    type: str
    need: List[str]
    confidence: float
    from_llm: bool = False


class IntentRouter:
    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold

    def detect(self, question: str, classifier: Optional[Callable[[str], Dict[str, Any]]] = None) -> IntentResult:
        if classifier is not None:
            try:
                data = classifier(question)
                intent_type = data.get("type")
                if intent_type in INTENT_TYPES:
                    confidence = float(data.get("confidence", 1.0))
                    need = data.get("need") or _NEED_BY_TYPE.get(intent_type, [])
                    return IntentResult(intent_type, need, confidence, from_llm=True)
            except Exception as exc:
                logger.warning("LLM 意图分类失败，回退启发式: %s", exc)
        return self._heuristic_detect(question)

    def needs_clarification(self, intent: IntentResult) -> bool:
        return intent.confidence < self.confidence_threshold

    def _heuristic_detect(self, question: str) -> IntentResult:
        for intent_type, keywords in _HEURISTIC_KEYWORDS:
            hits = sum(1 for kw in keywords if kw in question)
            if hits:
                confidence = min(0.5 + 0.15 * hits, 0.9)
                return IntentResult(intent_type, _NEED_BY_TYPE[intent_type], confidence)
        return IntentResult("general", [], 0.4)