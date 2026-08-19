"""Engine 统一接口：所有术数引擎必须继承 BaseEngine。

计算与解释分离原则：
- Engine 是确定性计算模块，禁止调用任何 LLM。
- 相同输入必须产生相同输出（纯函数性质）。
- 非法输入必须抛出 EngineError，禁止静默返回错误结果。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class EngineError(Exception):
    """引擎计算异常，包含可读的失败原因。

    当输入非法、超出支持范围或计算无法完成时抛出。
    """

    def __init__(self, message: str, code: str = "ENGINE_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class BaseEngine(ABC):
    """所有术数引擎的抽象基类。"""

    name: str = ""
    version: str = "0.1.0"
    system: str = ""  # ziwei / bazi / liuren / qimen / liuyao / tieban

    @abstractmethod
    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """输入原始出生信息，输出标准结构化命盘 JSON。

        必须是确定性函数：相同输入必须产生相同输出。
        输出的 JSON 必须包含 input_echo 字段，回显引擎实际使用的历法参数。
        """
        raise NotImplementedError

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """校验输入合法性，非法输入直接抛出 EngineError。

        包括但不限于：出生时间范围、时区缺失、农历/公历标记缺失。
        """
        raise NotImplementedError

    def health_check(self) -> bool:
        """健康检查，确认引擎可用。"""
        return True