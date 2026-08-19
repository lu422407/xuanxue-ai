"""成本追踪。

每次 Orchestrator 运行记录：调用了哪些 Engine、RAG 检索次数、LLM token 消耗。
用于成本审计与限流决策。
"""

import threading
import time
from typing import Any, Dict, List, Optional


class CostTracker:
    def __init__(self):
        self._records: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def record(self, trace_id: str, *, engines: Optional[List[str]] = None,
               rag_searches: int = 0, prompt_tokens: int = 0,
               completion_tokens: int = 0) -> None:
        with self._lock:
            rec = self._records.setdefault(trace_id, {
                "engines": [], "rag_searches": 0, "prompt_tokens": 0,
                "completion_tokens": 0, "llm_calls": 0, "started_at": time.time(),
            })
            rec["engines"] = list(dict.fromkeys(rec["engines"] + (engines or [])))
            rec["rag_searches"] += rag_searches
            rec["prompt_tokens"] += prompt_tokens
            rec["completion_tokens"] += completion_tokens
            rec["llm_calls"] += 1

    def get(self, trace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rec = self._records.get(trace_id)
            return dict(rec) if rec else None

    def total_llm_calls(self, trace_id: str) -> int:
        rec = self.get(trace_id)
        return rec["llm_calls"] if rec else 0

    def reset(self):
        with self._lock:
            self._records.clear()


cost_tracker = CostTracker()