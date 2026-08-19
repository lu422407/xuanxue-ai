"""测试用假 LLM：可编程生成内容与意图分类，便于离线测试。"""

from typing import Any, Dict, List, Optional


class FakeLLM:
    """generate 按预设返回内容；classify 按预设返回意图。"""

    def __init__(self, generate_map: Optional[Dict[str, str]] = None,
                 classify_map: Optional[Dict[str, Dict[str, Any]]] = None,
                 default_generate: str = "您的命盘已生成，四柱为庚午年庚辰月丙寅日壬辰时。"):
        self._generate_map = generate_map or {}
        self._classify_map = classify_map or {}
        self._default = default_generate
        self.calls: List[str] = []

    def classify(self, question: str) -> Dict[str, Any]:
        self.calls.append(f"classify:{question}")
        return self._classify_map.get(question, {
            "type": "general", "need": [], "confidence": 0.4})

    def generate(self, system_prompt: str, user_content: str, **kwargs) -> Dict[str, Any]:
        self.calls.append("generate")
        for key, value in self._generate_map.items():
            if key in user_content:
                return {"content": value, "model": "fake",
                        "usage": {"prompt_tokens": 10, "completion_tokens": 10}}
        return {"content": self._default, "model": "fake",
                "usage": {"prompt_tokens": 10, "completion_tokens": 10}}