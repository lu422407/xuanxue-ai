"""Embedding。

离线确定性字符 n-gram 哈希向量（用于测试与本地演示）。
生产环境应替换为真实向量模型（如 text-embedding-3-small），
只需实现 embed(text) -> List[float] 接口即可无缝替换。
"""

import hashlib
import math
import re
from typing import List

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _grams(text: str, n: int) -> List[str]:
    return [text[i:i + n] for i in range(len(text) - n + 1)]


def embed(text: str, dim: int = 256) -> List[float]:
    """把文本映射为 L2 归一化的哈希向量。

    使用 2/3 字符 n-gram（跳过单字，单字在中文中区分度低、易碰撞）。
    """
    vec = [0.0] * dim
    tokens = _tokenize(text)
    for token in tokens:
        for n in (2, 3):
            for gram in _grams(token, n):
                h = int(hashlib.md5(gram.encode("utf-8")).hexdigest()[:8], 16) % dim
                vec[h] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError("向量维度不一致")
    dot = sum(x * y for x, y in zip(a, b))
    return float(dot)