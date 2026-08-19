"""融合评分测试：输出档位而非伪精确百分比。"""

import pytest

from engines.base import BaseEngine, EngineError
from engines.liuyao_engine import LiuYaoEngine
from engines.qimen_engine import QiMenEngine
from engines.liuren_engine import LiuRenEngine
from engines.tieban_engine import TieBanEngine
from fusion.career import analyze_career
from fusion.scoring import score_factors


def test_scoring_tier_not_percentage():
    factors = [
        {"source": "bazi", "signal": "财官偏旺", "weight": "正向"},
        {"source": "ziwei", "signal": "官禄见煞", "weight": "中性偏弱"},
    ]
    result = score_factors(factors)
    assert result["tier"] in ("偏积极", "中性", "偏保守")
    # 禁止伪精确百分比
    assert "82%" not in str(result)
    # 必须包含 factors 拆解
    assert len(result["factors"]) == 2
    assert result["basis"]


def test_career_analyzer_shape():
    charts = {
        "bazi": {"pillars": {"month": {"ten_god": "正官"}}},
        "ziwei": {"palaces": {"官禄": {"major_stars": ["天同"]}}},
    }
    result = analyze_career(charts)
    assert result["topic"] == "career"
    assert len(result["factors"]) == 2
    assert "不构成" in result["disclaimer"]


@pytest.mark.parametrize("cls", [QiMenEngine, LiuYaoEngine])
def test_unimplemented_engines_raise(cls):
    engine = cls()
    assert isinstance(engine, BaseEngine)
    with pytest.raises(NotImplementedError):
        engine.calculate({})


@pytest.mark.parametrize("cls", [LiuRenEngine, TieBanEngine])
def test_implemented_engines_reject_empty_input(cls):
    engine = cls()
    assert isinstance(engine, BaseEngine)
    with pytest.raises(EngineError):
        engine.calculate({})