"""奇门遁甲引擎。

通过 ZhouYiLab CLI 桥接（example_zhouyi_cli.exe）执行奇门遁甲排盘，
CLI 未编译时保持显式错误，禁止静默输出错误结果。
"""

from typing import Any, Dict

from engines.base import BaseEngine, EngineError
from engines import calendar_utils as cu
from engines import zhouyi_bridge


class QiMenEngine(BaseEngine):
    name = "qimen"
    version = "0.1.0"
    system = "qimen"

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = cu.validate_birth_input(input_data)
        solar = cu.resolve_solar_datetime(normalized)
        if not (1900 <= solar.year <= 2100):
            raise EngineError(
                f"奇门遁甲暂支持 1900-2100 年，收到 {solar.year}",
                code="QIMEN_YEAR_OUT_OF_RANGE",
            )
        return normalized

    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self.validate_input(input_data)
        # 奇门以占时起盘：优先 divination_datetime，缺省回落出生时间
        solar = cu.resolve_divination_datetime(normalized)
        try:
            result = zhouyi_bridge.calculate_qi_men({
                "year": solar.year,
                "month": solar.month,
                "day": solar.day,
                "hour": solar.hour,
                "minute": solar.minute,
            })
        except EngineError as exc:
            raise EngineError(
                f"奇门遁甲排盘失败: {exc.message}",
                code=getattr(exc, "code", "QIMEN_CALC_FAILED"),
            )

        pan = result.get("pan", {})
        input_echo = {
            "birth_datetime": normalized["birth_datetime"],
            "timezone_offset": normalized.get("timezone_offset", 8.0),
            "calendar": normalized.get("calendar", "solar"),
            "gender": normalized.get("gender", "男"),
        }
        if normalized.get("divination_datetime"):
            input_echo["divination_datetime"] = normalized["divination_datetime"]
        return {
            "input_echo": input_echo,
            "system": self.system,
            "dun": pan.get("dun"),
            "dun_zh": pan.get("dun_zh"),
            "ju": pan.get("ju"),
            "yuan": pan.get("yuan"),
            "yuan_zh": pan.get("yuan_zh"),
            "solar_term": pan.get("solar_term"),
            "zhi_fu_star": pan.get("zhi_fu_star"),
            "zhi_shi_gate": pan.get("zhi_shi_gate"),
            "zhi_fu_palace": pan.get("zhi_fu_palace"),
            "solar_date": pan.get("solar_date"),
            "lunar_date": pan.get("lunar_date"),
            "ba_zi": pan.get("ba_zi"),
            "palaces": pan.get("palaces"),
            "description": result.get("description"),
        }

    def health_check(self) -> bool:
        return zhouyi_bridge.cli_available()