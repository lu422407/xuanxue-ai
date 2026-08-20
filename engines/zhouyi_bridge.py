"""ZhouYiLab CLI 桥接层：奇门/六爻引擎的进程调用封装。

通过子进程调用已编译的 ZhouYiLab CLI（example_zhouyi_cli.exe），
返回结构化 JSON。若 CLI 不可用则抛出 EngineError。
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from engines.base import EngineError

_BINARY_NAME = "example_zhouyi_cli.exe" if os.name == "nt" else "example_zhouyi_cli"

_DEFAULT_BINARY = Path(__file__).resolve().parent.parent / "third_party" / "ZhouYiLab" / "build" / "examples" / _BINARY_NAME

_TIMEOUT = 30.0


def _resolve_binary() -> Path:
    override = os.environ.get("ZHOUYILAB_CLI")
    if override:
        return Path(override)
    if _DEFAULT_BINARY.exists():
        return _DEFAULT_BINARY
    for candidate in [
        Path(__file__).resolve().parent.parent / "third_party" / "ZhouYiLab" / "build" / "examples",
        Path(__file__).resolve().parent.parent / "bin",
    ]:
        p = candidate / _BINARY_NAME
        if p.exists():
            return p
    raise EngineError(
        "ZhouYiLab CLI 未找到，请先编译：cd third_party/ZhouYiLab && cmake -B build && cmake --build build --target example_zhouyi_cli",
        code="ZHOUYILAB_CLI_NOT_FOUND",
    )


def _run(args: list[str]) -> Dict[str, Any]:
    binary = _resolve_binary()
    try:
        proc = subprocess.run(
            [str(binary)] + args,
            capture_output=True,
            timeout=_TIMEOUT,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise EngineError(f"ZhouYiLab CLI 无法执行: {exc}", code="ZHOUYILAB_CLI_EXEC_FAILED")
    except subprocess.TimeoutExpired:
        raise EngineError(f"ZhouYiLab CLI 计算超时（>{_TIMEOUT:.0f}s）", code="ZHOUYILAB_CLI_TIMEOUT")
    if proc.returncode != 0:
        raise EngineError(
            f"ZhouYiLab CLI 返回错误: {proc.stderr.strip() or proc.stdout.strip() or f'exit={proc.returncode}'}",
            code="ZHOUYILAB_CLI_FAILED",
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise EngineError(f"ZhouYiLab CLI 输出解析失败: {exc}", code="ZHOUYILAB_CLI_BAD_JSON")
    if not data.get("ok"):
        raise EngineError(data.get("error", "ZhouYiLab 计算失败"), code="ZHOUYILAB_CALC_FAILED")
    return data


def calculate_qi_men(solar: Dict[str, int]) -> Dict[str, Any]:
    """奇门遁甲排盘。solar: {year, month, day, hour, minute}"""
    return _run([
        "qi_men",
        str(solar["year"]), str(solar["month"]), str(solar["day"]),
        str(solar.get("hour", 0)), str(solar.get("minute", 0)),
    ])


def calculate_liu_yao(
    main_hexagram_code: str,
    solar: Dict[str, int],
    changing_lines: list[int] | None = None,
) -> Dict[str, Any]:
    """六爻排盘。main_hexagram_code: 6 位 '0'/'1' 字符串（从下到上）"""
    args = [
        "liu_yao",
        main_hexagram_code,
        str(solar["year"]), str(solar["month"]), str(solar["day"]),
        str(solar.get("hour", 0)), str(solar.get("minute", 0)),
    ]
    for line in (changing_lines or []):
        args.append(str(line))
    return _run(args)


def cli_available() -> bool:
    try:
        _resolve_binary()
        return True
    except EngineError:
        return False