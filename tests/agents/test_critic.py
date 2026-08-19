"""Critic(Validator) 测试：检测 LLM 输出与命盘不符的人为注入错误用例。"""

from agents.critic import Critic
from engines.bazi_engine import BaziEngine
from engines.ziwei_engine import ZiWeiEngine

BIRTH = {
    "birth_datetime": "1990-05-01 08:30:00",
    "timezone_offset": 8,
    "calendar": "solar",
    "gender": "男",
}


def _charts():
    return {
        "ziwei": ZiWeiEngine().calculate(dict(BIRTH)),
        "bazi": BaziEngine().calculate(dict(BIRTH)),
    }


def test_detects_fake_star():
    charts = _charts()
    # 人为注入错误：声称"命宫主星紫微"，但实际命盘命宫无主星（紫微在子女宫）
    draft = "您的命宫主星为紫微，代表一生贵气十足。"
    report = Critic().validate(draft, charts)
    assert not report.passed
    assert any("紫微" in i and "不符" in i for i in report.issues)


def test_detects_fake_ganzhi():
    charts = _charts()
    # 人为注入错误：声称八字为"庚午年甲子月"，但实际月柱是庚辰
    draft = "您的八字为庚午年甲子月出生，财官双旺。"
    report = Critic().validate(draft, charts)
    assert not report.passed
    assert any("甲子" in i for i in report.issues)


def test_pass_when_consistent():
    charts = _charts()
    draft = "您的命盘显示命宫位于丑宫，身主为巨门。八字四柱为庚午庚辰丙寅壬辰。"
    report = Critic().validate(draft, charts)
    assert report.passed


def test_safety_absolutism():
    critic = Critic()
    issues = critic.check_safety("我保证您明年一定发财")
    assert issues