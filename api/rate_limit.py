"""限流模块。

按用户（API Key）维度滑动窗口限流，防止单一账号高频调用耗尽 LLM 成本预算。
超限返回 429 + 明确错误码 rate_limit_exceeded。
"""

import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RateLimitError(Exception):
    status_code: int = 429
    code: str = "rate_limit_exceeded"
    message: str = "请求过于频繁，请稍后重试"


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """记录一次请求。超过阈值返回 False（拒绝）。"""
        now = time.time()
        with self._lock:
            times = self._hits.setdefault(key, [])
            cutoff = now - self.window_seconds
            self._hits[key] = [t for t in times if t > cutoff]
            if len(self._hits[key]) >= self.max_requests:
                return False
            self._hits[key].append(now)
            return True

    def reset(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key:
                self._hits.pop(key, None)
            else:
                self._hits.clear()


default_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60.0)


def rate_limit(key: str) -> bool:
    return default_limiter.check(key)