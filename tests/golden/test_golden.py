"""黄金测试集运行器。

每个 fixtures/*.json 包含 {system, input, expected}。
任何用例失败 = release blocker（见 v3.2 文档 5.2 节）。
"""

import json
import os

import pytest

from engines.bazi_engine import BaziEngine
from engines.ziwei_engine import ZiWeiEngine

GOLDEN_DIR = os.path.dirname(__file__)

ENGINES = {
    "bazi": BaziEngine,
    "ziwei": ZiWeiEngine,
}


def _discover_cases():
    cases = []
    for fname in sorted(os.listdir(GOLDEN_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(GOLDEN_DIR, fname), encoding="utf-8") as f:
            data = json.load(f)
        cases.append(pytest.param(data, id=fname.rsplit(".", 1)[0]))
    return cases


@pytest.mark.parametrize("case", _discover_cases())
def test_golden_case(case):
    engine_cls = ENGINES[case["system"]]
    result = engine_cls().calculate(dict(case["input"]))
    assert result == case["expected"], (
        f"黄金用例失败: {case['system']} 输出与固化期望不一致"
    )