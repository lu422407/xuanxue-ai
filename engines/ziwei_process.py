"""紫微引擎进程代理：API 线程池安全调用层。

通过持久 worker 子进程执行 py-iztro（见 ziwei_worker.py），
避免 pythonmonkey 在 Windows 非主线程崩溃。
进程内单例 + 全局锁串行化访问。
"""

import json
import subprocess
import sys
import threading
from typing import Any, Dict, Optional

from engines.base import EngineError

_TIMEOUT = 60.0

_lock = threading.Lock()
_proc: Optional[subprocess.Popen] = None


def _spawn():
    global _proc
    if _proc is not None and _proc.poll() is None:
        return _proc
    _proc = subprocess.Popen(
        [sys.executable, "-m", "engines.ziwei_worker", "--worker"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    return _proc


def _request(input_data: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        proc = _spawn()
        try:
            proc.stdin.write(json.dumps({"input": input_data}, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
        except (BrokenPipeError, OSError) as exc:
            raise EngineError(f"紫微 worker 进程不可用: {exc}", code="ZIWEI_WORKER_UNAVAILABLE")
        if not line:
            raise EngineError("紫微 worker 进程无响应（已退出）", code="ZIWEI_WORKER_EXITED")
        try:
            resp = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EngineError(f"紫微 worker 响应解析失败: {exc}", code="ZIWEI_WORKER_BAD_RESPONSE")
        if not resp.get("ok"):
            raise EngineError(resp.get("error", "紫微计算失败"), code="ZIWEI_CALC_FAILED")
        return resp["result"]


def calculate_ziwei(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """线程安全的紫微排盘，可在任意线程调用。"""
    return _request(input_data)


class ZiWeiProcessEngine:
    """与 engines.base.BaseEngine 接口兼容的进程代理引擎。"""

    name = "ziwei"
    version = "0.1.0"
    system = "ziwei"

    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return calculate_ziwei(input_data)

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        from engines.ziwei_engine import ZiWeiEngine
        ZiWeiEngine().validate_input(input_data)