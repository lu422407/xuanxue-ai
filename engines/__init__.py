"""术数引擎统一接口。

整合 8 个 GitHub 开源项目：
- iztro / py-iztro（紫微）
- ziwei-doushu（紫微样本库）
- DeepSeek-Oracle（Prompt 参考）
- chinese-metaphysics-skills（六壬 SKILL.md 知识库）
- ZhouYiLab（C++ 多术数验证层，奇门/六爻待编译）
- dalurenpython / daliuren-web-engine（六壬）
"""

from .ziwei_engine import ZiWeiEngine
from .liuren_engine import LiuRenEngine
from .bazi_engine import BaziEngine
from .tieban_engine import TieBanEngine
from .qimen_engine import QiMenEngine
from .liuyao_engine import LiuYaoEngine

__all__ = [
    "ZiWeiEngine",
    "LiuRenEngine",
    "BaziEngine",
    "TieBanEngine",
    "QiMenEngine",
    "LiuYaoEngine",
]