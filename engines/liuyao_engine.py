"""六爻引擎。

通过 ZhouYiLab CLI 桥接（example_zhouyi_cli.exe）执行六爻排盘。
输入需要 main_hexagram_code（6 位 '0'/'1'，从下到上），
缺失时显式报错，禁止静默输出错误结果。
"""

from typing import Any, Dict

from engines.base import BaseEngine, EngineError
from engines import calendar_utils as cu
from engines import zhouyi_bridge


class LiuYaoEngine(BaseEngine):
    name = "liuyao"
    version = "0.1.0"
    system = "liuyao"

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = cu.validate_birth_input(input_data)
        code = normalized.get("main_hexagram_code") or normalized.get("hexagram_code")
        if not code:
            raise EngineError(
                "六爻起卦需要 main_hexagram_code（6 位 '0'/'1'，从下到上，如 '111111' 表示乾为天）",
                code="LIUYAO_MISSING_HEXAGRAM_CODE",
            )
        code = str(code).strip()
        if len(code) != 6 or any(c not in "01" for c in code):
            raise EngineError(
                f"main_hexagram_code 必须是 6 位 '0'/'1'，收到: {code}",
                code="INVALID_HEXAGRAM_CODE",
            )
        normalized["main_hexagram_code"] = code
        return normalized

    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self.validate_input(input_data)
        # 六爻按占时定日辰/起六神：优先 divination_datetime，缺省回落出生时间
        solar = cu.resolve_divination_datetime(normalized)
        code = normalized["main_hexagram_code"]
        changing_lines = normalized.get("changing_lines") or []
        try:
            result = zhouyi_bridge.calculate_liu_yao(
                code,
                {
                    "year": solar.year,
                    "month": solar.month,
                    "day": solar.day,
                    "hour": solar.hour,
                    "minute": solar.minute,
                },
                [int(x) for x in changing_lines],
            )
        except EngineError as exc:
            raise EngineError(
                f"六爻排盘失败: {exc.message}",
                code=getattr(exc, "code", "LIUYAO_CALC_FAILED"),
            )

        pan = result.get("pan", {})
        input_echo = {
            "birth_datetime": normalized["birth_datetime"],
            "timezone_offset": normalized.get("timezone_offset", 8.0),
            "calendar": normalized.get("calendar", "solar"),
            "gender": normalized.get("gender", "男"),
            "main_hexagram_code": code,
            "changing_lines": changing_lines,
        }
        if normalized.get("divination_datetime"):
            input_echo["divination_datetime"] = normalized["divination_datetime"]
        return {
            "input_echo": input_echo,
            "system": self.system,
            "ben_gua_name": pan.get("ben_gua_name"),
            "ba_zi": pan.get("ba_zi"),
            "shen_sa": pan.get("shen_sa"),
            "yao": pan.get("yao"),
            "ai_read": result.get("ai_read"),
        }

    def health_check(self) -> bool:
        return zhouyi_bridge.cli_available()