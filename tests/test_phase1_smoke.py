"""Phase 1 验收：基础架构冒烟测试。"""

from engines.base import BaseEngine, EngineError
from llm.base import BaseLLM, LLMError


def test_base_engine_abstract():
    """BaseEngine 是抽象类，不能直接实例化。"""
    try:
        BaseEngine()
        raise AssertionError("BaseEngine 应不可实例化")
    except TypeError:
        pass


def test_engine_error_message():
    err = EngineError("出生时间缺失时区", code="INVALID_INPUT")
    assert err.message == "出生时间缺失时区"
    assert err.code == "INVALID_INPUT"


def test_base_llm_abstract():
    try:
        BaseLLM()
        raise AssertionError("BaseLLM 应不可实例化")
    except TypeError:
        pass


def test_llm_error():
    err = LLMError("上游超时")
    assert str(err) == "上游超时"