"""奇门遁甲引擎。

蓝图方案：封装 ZhouYiLab C++ 奇门模块（third_party/ZhouYiLab）。
需编译：cd third_party/ZhouYiLab && cmake -B build && cmake --build build
生成 build/bin/example_qi_men 后方可使用。

当前环境无 C++ 工具链（未找到 cmake/g++/cl），因此保持显式
NotImplementedError，禁止静默输出错误结果。
"""

from typing import Any, Dict

from engines.base import BaseEngine


class QiMenEngine(BaseEngine):
    name = "qimen"
    version = "0.1.0"
    system = "qimen"

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(
            "奇门遁甲引擎依赖 ZhouYiLab C++ 模块，尚未编译。"
            "请运行: cd third_party/ZhouYiLab && cmake -B build && cmake --build build"
        )