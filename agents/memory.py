"""Memory Agent：长期记忆。

保存用户资料、命盘、人生事件、偏好。
支持按用户删除（数据主权，级联清理）。
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UserMemory:
    user_id: str
    profile: Dict[str, Any] = field(default_factory=dict)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    life_events: List[Dict[str, Any]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)


class MemoryAgent:
    def __init__(self):
        self._store: Dict[str, UserMemory] = {}
        # 使用可重入锁：save_* 会先加锁再调用 self.get()（内部也加锁）
        self._lock = threading.RLock()

    def get(self, user_id: str) -> UserMemory:
        with self._lock:
            mem = self._store.get(user_id)
            if mem is None:
                mem = UserMemory(user_id=user_id)
                self._store[user_id] = mem
            return mem

    def save_chart(self, user_id: str, chart: Dict[str, Any]) -> None:
        with self._lock:
            self.get(user_id).charts.append(chart)

    def save_preference(self, user_id: str, key: str, value: Any) -> None:
        with self._lock:
            self.get(user_id).preferences[key] = value

    def add_life_event(self, user_id: str, event: Dict[str, Any]) -> None:
        with self._lock:
            self.get(user_id).life_events.append(event)

    def delete_user(self, user_id: str) -> None:
        """删除用户全部记忆（数据主权，级联清理）。"""
        with self._lock:
            self._store.pop(user_id, None)