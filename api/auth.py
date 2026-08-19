"""鉴权模块。

- API Key 鉴权：请求头 X-API-Key
- 生产环境可将密钥存储于数据库/密钥管理服务；
  本地演示从环境变量 XUANXUE_API_KEYS 读取（逗号分隔），
  未设置时使用默认开发密钥 dev-key-0001。
"""

import os
from typing import Optional

_API_KEYS = set(
    k.strip()
    for k in os.environ.get("XUANXUE_API_KEYS", "dev-key-0001").split(",")
    if k.strip()
)


def _known_keys() -> set:
    return set(_API_KEYS)


def register_key(key: str) -> None:
    _API_KEYS.add(key)


def is_valid_api_key(api_key: Optional[str]) -> bool:
    return bool(api_key and api_key in _known_keys())


def authenticate(api_key: Optional[str]) -> Optional[str]:
    """校验 API Key。合法返回 key，非法返回 None。"""
    if is_valid_api_key(api_key):
        return api_key
    return None