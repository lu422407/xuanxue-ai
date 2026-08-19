"""大六壬引擎（基于 dalurenpython）。

整合开源项目：
- dalurenpython（主引擎，Python 完整排盘：天地盘/四课/三传/天将/神煞/格局）
- chinese-metaphysics-skills（六壬 SKILL.md 知识库，作断课参考）
- daliuren-web-engine（可视化参考）

注意：大六壬为占卜术，起课时间应是「占卜时刻」。本引擎在
input_data 中优先读取 divination_datetime，缺省回落 birth_datetime。
"""

import logging
from pathlib import Path
from typing import Any, Dict

from engines.base import BaseEngine, EngineError
from engines import calendar_utils as cu

logger = logging.getLogger(__name__)

_THIRD_PARTY = Path(__file__).resolve().parent.parent / "third_party"
_DALURENPYTHON = _THIRD_PARTY / "dalurenpython"

if str(_DALURENPYTHON) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_DALURENPYTHON))

try:
    from common import GetLi, GetShiChen
    from shipan.shipan import ShiPan
    from ganzhiwuxin import 支 as _dzhi
    HAS_DALUREN = True
except ImportError as exc:
    logger.warning("dalurenpython 不可用: %s", exc)
    HAS_DALUREN = False


def _lazy_daluren():
    if not HAS_DALUREN:
        raise EngineError(
            "大六壬引擎不可用：需先 git submodule update --init third_party/dalurenpython "
            "并 pip install eacal ganzhiwuxin regex prettytable",
            code="LIUREN_DEP_MISSING",
        )
    return GetLi, GetShiChen, ShiPan


class LiuRenEngine(BaseEngine):
    name = "liuren"
    version = "1.0.0"
    system = "liuren"

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = cu.validate_birth_input(input_data)
        return normalized

    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self.validate_input(input_data)
        GetLi, GetShiChen, ShiPan = _lazy_daluren()

        # 占卜时间：优先 divination_datetime，缺省回落出生时间
        divination = normalized.get("divination_datetime") or normalized.get("birth_datetime")
        solar = cu._parse_datetime_string(divination)

        try:
            li = GetLi(solar.year, solar.month, solar.day,
                       solar.hour, solar.minute, solar.second)
            year_gz, month_gz, day_gz, hour_gz, yuejiang, jie, qi = li
        except Exception as exc:
            raise EngineError(f"六壬历法数据计算失败: {exc}", code="LIUREN_CALC_FAILED")

        月将 = str(yuejiang)
        占时 = str(GetShiChen(solar.hour))
        gender = normalized.get("gender", "男")
        birth_year = int(str(normalized.get("divination_birth_year") or "") or solar.year)

        try:
            pan = ShiPan(
                solar.year, solar.month, solar.day,
                solar.hour, solar.minute, solar.second,
                月将, 占时, True,
                normalized.get("question", ""),
                0 if gender == "男" else 1,
                birth_year,
            )
        except Exception as exc:
            raise EngineError(f"六壬排盘失败: {exc}", code="LIUREN_CALC_FAILED")

        si_ke = pan.四课
        san_chuan = pan.三传

        return {
            "system": self.system,
            "engine_version": self.version,
            "engine_source": "dalurenpython",
            "input_echo": cu.build_input_echo(
                normalized, solar,
                {"divination_time": divination, "lunar": cu.get_lunar_info(solar)}),
            "divination_time": divination,
            "pillars": {
                "year": f"{year_gz}",
                "month": f"{month_gz}",
                "day": f"{day_gz}",
                "hour": f"{hour_gz}",
            },
            "solar_terms": {"jie": jie, "qi": qi},
            "月将": 月将,
            "占时": 占时,
            "空亡": [str(x) for x in pan.空亡],
            "天地盘": {str(z): str(pan.天盘[_dzhi(z)]) for z in cu.ZHI},
            "四课": {
                "一课": [str(x) for x in si_ke.一课],
                "二课": [str(x) for x in si_ke.二课],
                "三课": [str(x) for x in si_ke.三课],
                "四课": [str(x) for x in si_ke.四课],
            },
            "三传": {
                "初传": str(san_chuan.初),
                "中传": str(san_chuan.中),
                "末传": str(san_chuan.末),
                "六亲": list(san_chuan.六亲),
                "遁干": [str(x) for x in san_chuan.遁干],
            },
            "天将": {
                "初传": str(pan.tianJiang[san_chuan.初]),
                "中传": str(pan.tianJiang[san_chuan.中]),
                "末传": str(pan.tianJiang[san_chuan.末]),
            },
            "格局": list(pan.格局),
        }