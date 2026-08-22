"""黄金测试集运行器。

每个 fixtures/*.json 包含 {system, input, expected}，铁板考刻用例额外含 {known_facts}。
任何用例失败 = release blocker（见 v3.2 文档 5.2 节）。

奇门/六爻依赖 ZhouYiLab C++ CLI：未编译的环境自动 skip
（CI 的 cpp-cli job 会真实执行并禁止 skip，见 .github/workflows/ci.yml）。
"""

import json
import os

import pytest

from engines import zhouyi_bridge
from engines.bazi_engine import BaziEngine
from engines.liuren_engine import LiuRenEngine
from engines.liuyao_engine import LiuYaoEngine
from engines.qimen_engine import QiMenEngine
from engines.tieban_engine import TieBanEngine
from engines.ziwei_engine import ZiWeiEngine

GOLDEN_DIR = os.path.dirname(__file__)

ENGINES = {
    "bazi": BaziEngine,
    "ziwei": ZiWeiEngine,
    "qimen": QiMenEngine,
    "liuyao": LiuYaoEngine,
    "liuren": LiuRenEngine,
    "tieban": TieBanEngine,
}

# 依赖 ZhouYiLab C++ CLI 的系统
CLI_SYSTEMS = {"qimen", "liuyao"}


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
    if case["system"] in CLI_SYSTEMS and not zhouyi_bridge.cli_available():
        pytest.skip("ZhouYiLab CLI 未编译，奇门/六爻黄金用例跳过（CI cpp-cli job 强制执行）")
    engine_cls = ENGINES[case["system"]]
    known_facts = case.get("known_facts")
    if known_facts:
        # 铁板考刻路径：黄金用例同时固化 verify_kefen 输出
        result = engine_cls().verify_kefen(dict(case["input"]), known_facts)
    else:
        result = engine_cls().calculate(dict(case["input"]))
    assert result == case["expected"], (
        f"黄金用例失败: {case['system']} 输出与固化期望不一致"
    )
