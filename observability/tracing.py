"""全链路追踪。

每次用户请求分配唯一 trace_id，贯穿
Intent Router → Planner → Engine → RAG → LLM → Validator 全流程。

支持通过 trace_id 完整回放当次执行链路。
生产环境建议接入 OpenTelemetry，本实现提供内存存储便于测试与回溯。
"""

import threading
import time
import uuid
from typing import Any, Dict, List, Optional


class Span:
    def __init__(self, trace_id: str, name: str):
        self.trace_id = trace_id
        self.name = name
        self.started_at = time.time()
        self.duration_ms: Optional[float] = None
        self.detail: Dict[str, Any] = {}

    def finish(self):
        self.duration_ms = round((time.time() - self.started_at) * 1000, 2)


class Tracer:
    """内存版 Tracer。线程安全。"""

    def __init__(self):
        self._spans: Dict[str, List[Span]] = {}
        self._lock = threading.Lock()

    def new_trace_id(self) -> str:
        return uuid.uuid4().hex

    def start(self, trace_id: str, name: str) -> Span:
        span = Span(trace_id, name)
        with self._lock:
            self._spans.setdefault(trace_id, []).append(span)
        return span

    def end(self, span: Span):
        span.finish()

    def span(self, trace_id: str, name: str):
        """上下文管理器，用于 with tracer.span(...) 语法。"""

        class _Ctx:
            def __enter__(self):
                self.span = self._tracer.start(self._tid, self._name)
                return self.span

            def __exit__(self, exc_type, exc, tb):
                self._tracer.end(self.span)
                return False

        ctx = _Ctx()
        ctx._tracer = self
        ctx._tid = trace_id
        ctx._name = name
        return ctx

    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            spans = self._spans.get(trace_id, [])
        return [
            {"name": s.name, "duration_ms": s.duration_ms, "detail": s.detail}
            for s in spans
        ]

    def reset(self):
        with self._lock:
            self._spans.clear()


tracer = Tracer()