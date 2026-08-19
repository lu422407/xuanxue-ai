"""知识库加载器：把 knowledge/ 下的 JSON 文档加载进 Retriever。

文件格式：[{source_id, category, title, text, reference}]
"""

import json
import os
from typing import List, Optional

from rag.retriever import Retriever

KNOWLEDGE_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge")
DIRECTORIES = {
    "classics": os.path.join(KNOWLEDGE_ROOT, "classics"),
    "cases": os.path.join(KNOWLEDGE_ROOT, "cases"),
    "rules": os.path.join(KNOWLEDGE_ROOT, "rules"),
    "feedback": os.path.join(KNOWLEDGE_ROOT, "feedback"),
}


def load_knowledge(retriever: Retriever, categories: Optional[List[str]] = None) -> int:
    """加载指定类别的知识文档，返回加载数量。"""
    count = 0
    for category, directory in DIRECTORIES.items():
        if categories and category not in categories:
            continue
        if not os.path.isdir(directory):
            continue
        for fname in sorted(os.listdir(directory)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(directory, fname), encoding="utf-8") as f:
                docs = json.load(f)
            for doc in docs:
                retriever.add_knowledge(
                    doc["source_id"], doc["text"],
                    metadata={"category": category, "title": doc.get("title", ""),
                              "reference": doc.get("reference", "")})
                count += 1
    return count