"""Prompt 注入防护（Guardrails）。

用户输入在进入 Intent Router 之前先经过注入检测。
RAG 检索回来的古籍/案例文本在拼入 Prompt 前也要做同样检测——
外部知识库同样是不可信输入源。

防护类别：
1. 指令覆盖（忽略/遗忘之前的指令）
2. 系统角色冒充 / 提示词泄露
3. 越狱 / 危险指令
4. 数据外泄（要求输出系统提示词、读取内部文件）
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class GuardResult:
    blocked: bool
    category: str = ""
    reason: str = ""
    matched_patterns: List[str] = field(default_factory=list)


_PATTERNS: List[tuple] = [
    # (category, regex) —— 顺序即优先级，命中即返回该类别
    ("instruction_override", r"(忽略|忘记|遗忘).{0,8}(指令|指示|规则|约束|system\s*prompt)"),
    ("instruction_override", r"ignore\s+(all\s+)?(previous|prior|above).{0,20}(instructions|prompt|rules)"),
    ("instruction_override", r"(forget|disregard).{0,20}(instructions|prompt|rules)"),
    ("system_impersonation", r"(扮演|假装是|你现在是)(系统|system|管理员|admin)"),
    ("system_impersonation", r"pretend\s+(to\s+be\s+)?(the\s+)?system"),
    ("prompt_leak", r"(输出|给出|打印|告诉我|显示|show|reveal).{0,20}(提示词|system\s*prompt|系统指令|prompt)"),
    ("prompt_leak", r"(列出|列举).{0,15}(所有|全部).{0,5}(指令|规则|约束|提示词|prompt)"),
    ("jailbreak", r"(越狱|破解|解锁.*限制|无限制模式|do\s+anything\s+now|DAN\b)"),
    ("data_exfiltration", r"(读取|查看|打开|读取文件).{0,10}(/|\.\\)?.{0,20}(\.env|\.git|secret|key|password|数据库)"),
    ("data_exfiltration", r"(tell|give|share).{0,15}(api\s*key|secret|password|credentials)"),
]


def check(text: str) -> GuardResult:
    """检测文本是否包含注入特征，按优先级返回首个命中的类别。"""
    if not text:
        return GuardResult(blocked=False)
    for category, pattern in _PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return GuardResult(blocked=True, category=category,
                               reason=f"检测到{category}类注入特征",
                               matched_patterns=[pattern])
    return GuardResult(blocked=False)


DISCLAIMER = (
    "以上分析为传统术数文化的知识性推演，不构成医疗、法律、财务或其他专业建议，"
    "仅供文化研究与个人参考使用。用户不应据此做出重大人生决策。"
)


def wrap_disclaimer(text: str) -> str:
    """注入免责声明。"""
    if DISCLAIMER in text:
        return text
    return f"{text}\n\n{'-' * 30}\n{DISCLAIMER}"