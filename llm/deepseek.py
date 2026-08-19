"""DeepSeek LLM 提供商（OpenAI 兼容协议，需 DEEPSEEK_API_KEY）。"""

import os

from llm.base import BaseLLM, LLMError

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


class DeepSeekLLM(BaseLLM):
    provider = "deepseek"
    model = "deepseek-chat"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        if OpenAI is None:
            raise LLMError("缺少 openai 依赖")
        self.model = model or self.model
        self._client = OpenAI(
            api_key=api_key or os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )

    def generate(self, system_prompt: str, user_content: str, **kwargs) -> dict:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        msg = response.choices[0].message
        usage = response.usage
        return {
            "content": msg.content or "",
            "model": response.model,
            "usage": {"prompt_tokens": usage.prompt_tokens if usage else 0,
                      "completion_tokens": usage.completion_tokens if usage else 0},
        }