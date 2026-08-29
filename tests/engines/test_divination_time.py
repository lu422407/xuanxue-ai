"""奇门/六爻占时起盘测试：divination_datetime 优先、缺省回落出生时间。

依赖 ZhouYiLab CLI；未编译环境 skip（CI cpp-cli job 强制执行）。
"""

import pytest

from engines import zhouyi_bridge

_BIRTH = {"birth_datetime": "1990-05-01 08:30:00", "timezone_offset": 8,
          "calendar": "solar", "gender": "男"}
_DIVINATION = "2026-08-29 10:00:00"


def _require_cli():
    if not zhouyi_bridge.cli_available():
        pytest.skip("ZhouYiLab CLI 未编译")


def test_qimen_uses_divination_datetime():
    _require_cli()
    from engines.qimen_engine import QiMenEngine
    with_div = QiMenEngine().calculate(dict(_BIRTH, divination_datetime=_DIVINATION))
    without_div = QiMenEngine().calculate(dict(_BIRTH))
    # 1990-05-01 处谷雨节气；2026-08-29 处处暑、阴遁——占时必须生效
    assert with_div["solar_term"] == "处暑"
    assert with_div["dun_zh"] == "阴遁"
    assert without_div["solar_term"] == "谷雨"
    assert with_div["input_echo"]["divination_datetime"] == _DIVINATION
    assert "divination_datetime" not in without_div["input_echo"]


def test_liuyao_uses_divination_datetime():
    _require_cli()
    from engines.liuyao_engine import LiuYaoEngine
    inp = dict(_BIRTH, main_hexagram_code="111111")
    with_div = LiuYaoEngine().calculate(dict(inp, divination_datetime=_DIVINATION))
    without_div = LiuYaoEngine().calculate(dict(inp))
    # 日辰随占时变化：卦的干支/神煞必须不同
    assert with_div["ba_zi"] != without_div["ba_zi"]
    assert with_div["input_echo"]["divination_datetime"] == _DIVINATION
