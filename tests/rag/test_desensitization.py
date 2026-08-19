"""脱敏测试：脱敏前后对比 + 脱敏校验。"""

from rag.desensitization import assert_desensitized, desensitize

RAW_CASE = (
    "张三先生，1988-06-15 08:30:00 出生于广东省深圳市南山区科技园，"
    "联系电话 13812345678，邮箱 zhangsan@example.com。"
    "该命主八字为戊辰年戊午月丙戌日壬辰时。"
)

RAW_FEEDBACK = (
    "李女士反馈：出生时间1992年3月8日 14:00，地点北京市海淀区。"
    "她认为之前的分析很准。身份证号 110101199203081234。"
)


def test_desensitize_removes_contact():
    out = desensitize(RAW_CASE)
    assert "13812345678" not in out
    assert "zhangsan@example.com" not in out
    assert "110101199203081234" not in out


def test_desensitize_masks_birth_and_name():
    out = desensitize(RAW_FEEDBACK)
    assert "1992年3月8日" not in out
    assert "李女士" not in out
    assert "[手机号已删除]" in out or "身份证" not in out


def test_desensitized_assertion_passes():
    out = desensitize(RAW_CASE + RAW_FEEDBACK)
    assert assert_desensitized(out)


def test_raw_not_desensitized():
    assert not assert_desensitized(RAW_CASE)


def test_before_after_differ():
    assert desensitize(RAW_CASE) != RAW_CASE