"""LLM 统一接口：所有模型提供商必须继承 BaseLLM。

安全要求：
- system_prompt 与 user_content 必须分开传递，
  禁止在实现中把二者拼接成一个字符串再整体发送（防 Prompt 注入）。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMError(Exception):
    """LLM 调用异常。"""

    pass


class BaseLLM(ABC):
    provider: str = "base"
    model: str = ""

    @abstractmethod
    def generate(self, system_prompt: str, user_content: str, **kwargs) -> Dict[str, Any]:
        """调用 LLM 生成内容。

        Args:
            system_prompt: 系统提示词，与用户输入严格分离。
            user_content: 用户内容（可能是用户问题或 RAG 检索后的上下文）。

        Returns:
            返回 dict，包含至少:
            {
                "content": str,          # 生成的文本
                "model": str,
                "usage": {"prompt_tokens": int, "completion_tokens": int}
            }
        """
        raise NotImplementedError