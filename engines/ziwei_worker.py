"""紫微引擎 worker 进程入口。

独立子进程执行 py-iztro，规避 pythonmonkey 在 Windows 非主线程
调用时的 access violation。启动方式：
    python -m engines.ziwei_worker --worker

行协议（stdin/stdout，UTF-8 JSON，每行一条消息）：
- 请求: {"input": {...}}
- 响应: {"ok": true, "result": {...}} 或 {"ok": false, "error": "..."}
"""

import json
import sys


def worker_main() -> int:
    from engines.ziwei_engine import ZiWeiEngine

    engine = ZiWeiEngine()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            result = engine.calculate(req["input"])
            sys.stdout.write(json.dumps({"ok": True, "result": result},
                                        ensure_ascii=False) + "\n")
        except Exception as exc:  # noqa: BLE001
            sys.stdout.write(json.dumps(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"}) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        raise SystemExit(worker_main())
    print("用法: python -m engines.ziwei_worker --worker")