"""Claude LLM 提供商（需环境变量 ANTHROPIC_API_KEY）。"""

import os

from llm.base import BaseLLM, LLMError


class ClaudeLLM(BaseLLM):
    provider = "claude"
    model = "claude-3-5-haiku-latest"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or self.model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise LLMError("缺少 ANTHROPIC_API_KEY")

    def generate(self, system_prompt: str, user_content: str, **kwargs) -> dict:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise LLMError("缺少 anthropic 依赖")
        client = Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 1024),
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        return {
            "content": text,
            "model": response.model,
            "usage": {"prompt_tokens": response.usage.input_tokens if response.usage else 0,
                      "completion_tokens": response.usage.output_tokens if response.usage else 0},
        }