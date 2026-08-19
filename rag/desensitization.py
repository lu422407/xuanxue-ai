"""脱敏工具：案例/反馈入库前必须移除或泛化可识别信息。

处理项：
- 姓名：替换为"某"
- 精确出生时间：泛化为"19XX年X月"（保留月份用于术数校验会引入识别风险，
  因此完全泛化为年），或删除
- 精确地点：泛化为省级/市级（保留到地级市）
- 手机号 / 身份证 / 邮箱等联系方式：删除
"""

import re

_NAME_RE = re.compile(r"[\u4e00-\u9fff]{1,2}(?:先生|女士|小姐|老师|同学)")
_ID_CARD_RE = re.compile(r"\d{17}[\dXx]")
_PHONE_RE = re.compile(r"1[3-9]\d{9}")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_BIRTH_TIME_RE = re.compile(
    r"(?:出生(?:于|时间|日期)?[:：]?)?"
    r"(\d{4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})?[日号]?"
    r"(?:\s+\d{1,2}[:：]\d{2}(?:[:：]\d{2})?)?"
)
_LOCATION_RE = re.compile(r"[\u4e00-\u9fff]{2,6}?(省|市|区|县|镇|乡)")


def desensitize(text: str, keep_city: bool = True) -> str:
    """对文本做脱敏。返回脱敏后的文本。"""
    out = text
    # 联系方式：直接删除
    out = _PHONE_RE.sub("[手机号已删除]", out)
    out = _ID_CARD_RE.sub("[身份证已删除]", out)
    out = _EMAIL_RE.sub("[邮箱已删除]", out)

    # 出生时间：泛化为年份
    def _mask_birth(m):
        return f"出生年份约{m.group(1)}年"
    out = _BIRTH_TIME_RE.sub(_mask_birth, out)

    # 地点：精确到区/县/镇/乡的部分泛化为"某区/某县/某镇/某乡"，保留到地级市
    def _mask_location(m):
        token = m.group(0)
        if token.endswith(("省", "市")):
            return token
        for suffix in ("区", "县", "镇", "乡"):
            if token.endswith(suffix):
                return "某" + suffix
        return token
    out = _LOCATION_RE.sub(_mask_location, out)

    # 姓名：脱敏为"某"
    out = _NAME_RE.sub(lambda m: "某" * len(m.group(0)), out)
    return out


def assert_desensitized(text: str) -> bool:
    """校验文本是否已脱敏：不存在手机号/身份证/邮箱/精确出生日期。"""
    return not (
        _PHONE_RE.search(text) or _ID_CARD_RE.search(text)
        or _EMAIL_RE.search(text)
        or _BIRTH_TIME_RE.search(text)
    )