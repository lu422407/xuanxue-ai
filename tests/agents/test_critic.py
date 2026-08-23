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


# ---- check_hallucination / check_safety 做实 ----

def test_check_hallucination_flags_fabricated_source():
    issues = Critic().check_hallucination(
        "古籍有云……[source:classic_fake_999]",
        citations=["紫微斗数全书（卷一）[source:classic_real_001]"])
    assert any("classic_fake_999" in i for i in issues)


def test_check_hallucination_allows_retrieved_source():
    issues = Critic().check_hallucination(
        "见[source:classic_real_001]所载",
        citations=["紫微斗数全书（卷一）[source:classic_real_001]"])
    assert issues == []


def test_check_hallucination_store_fallback():
    class FakeStore:
        def exists(self, doc_id):
            return doc_id == "kb_001"

    critic = Critic()
    assert critic.check_hallucination("[source:kb_001]", store=FakeStore()) == []
    assert critic.check_hallucination("[source:kb_bad]", store=FakeStore())


def test_check_hallucination_no_basis_no_issue():
    # 无 citations 且无 store：没有事实基准，不得臆断
    assert Critic().check_hallucination("[source:anything]") == []


def test_safety_domain_expansion():
    critic = Critic()
    for text in ("可以停药，照此方调理即可",
                 "这场官司必胜诉，放心",
                 "该产品零风险，明年必涨",
                 "老师保证无罪，案件必赢"):
        assert critic.check_safety(text), text


def test_safety_cultural_disclaimer_not_flagged():
    critic = Critic()
    assert critic.check_safety("以上为传统文化推演，不构成医疗或投资建议。") == []

# ---- 奇门 / 六爻 / 六壬声称校验 ----

QM_BIRTH = {
    "birth_datetime": "2024-03-05 10:00:00",
    "timezone_offset": 8, "calendar": "solar", "gender": "男",
}


def _qimen_chart():
    from engines.qimen_engine import QiMenEngine
    from engines import zhouyi_bridge
    if not zhouyi_bridge.cli_available():
        return None
    return QiMenEngine().calculate(dict(QM_BIRTH))


def test_detects_fake_qimen_star_and_gate():
    chart = _qimen_chart()
    if chart is None:
        import pytest
        pytest.skip("ZhouYiLab CLI 未编译")
    # 2024-03-05 盘面实际有天英/休门（北宫），天禽不临宫、开门在西北
    actual_stars = {p["star"] for p in chart["palaces"]}
    fake_star = next(s for s in ("天禽", "天辅", "天冲") if s not in actual_stars)
    draft = f"本盘{fake_star}临宫，且开门大吉，宜行动。"
    # 开门是否在盘中需动态判断，星曜断言是主目标
    report = Critic().validate(draft, {"qimen": chart})
    assert not report.passed
    assert any(fake_star in i and "不符" in i for i in report.issues)


def test_qimen_consistent_text_passes():
    chart = _qimen_chart()
    if chart is None:
        import pytest
        pytest.skip("ZhouYiLab CLI 未编译")
    palace = chart["palaces"][0]
    draft = f"本盘{palace['palace_name']}方{palace['star']}星、{palace['gate']}门。"
    report = Critic().validate(draft, {"qimen": chart})
    assert report.passed, report.issues


def _liuyao_chart():
    from engines.liuyao_engine import LiuYaoEngine
    from engines import zhouyi_bridge
    if not zhouyi_bridge.cli_available():
        return None
    inp = dict(QM_BIRTH)
    inp["main_hexagram_code"] = "111111"
    return LiuYaoEngine().calculate(inp)


def test_detects_fake_liuyao_spirit_and_relative():
    chart = _liuyao_chart()
    if chart is None:
        import pytest
        pytest.skip("ZhouYiLab CLI 未编译")
    # 人为注入错误：初爻实际临勾陈，声称初爻临青龙（六神按爻位轮排，须校验位置对应）
    actual_first = chart["yao"][0]["spirit"]
    fake_spirit = next(s for s in ("青龙", "朱雀", "白虎", "螣蛇") if s != actual_first)
    draft = f"初爻{fake_spirit}持世，动而有变。"
    report = Critic().validate(draft, {"liuyao": chart})
    assert not report.passed
    assert any(fake_spirit in i and "六神" in i for i in report.issues)


def test_liuyao_consistent_text_passes():
    chart = _liuyao_chart()
    if chart is None:
        import pytest
        pytest.skip("ZhouYiLab CLI 未编译")
    y = chart["yao"][0]
    ganzhi = y["mainPillar"]["stem"] + y["mainPillar"]["branch"]
    draft = f"初爻纳甲{ganzhi}，{y['spirit']}临之。"
    report = Critic().validate(draft, {"liuyao": chart})
    assert report.passed, report.issues


def test_detects_fake_liuren_yuejiang():
    from engines.liuren_engine import LiuRenEngine
    inp = dict(QM_BIRTH)
    inp["divination_datetime"] = "2024-03-05 10:00:00"
    chart = LiuRenEngine().calculate(inp)
    actual = chart["月将"]
    fake = next(z for z in "子丑寅卯辰巳午未申酉戌亥" if z != actual)
    report = Critic().validate(f"本月将为{fake}，课体已定。", {"liuren": chart})
    assert not report.passed
    assert any("月将" in i for i in report.issues)


# ---- 铁板神数声称校验（防 LLM 编造条文号/条文正文） ----

def _tieban_details():
    from engines.tieban_engine import TieBanEngine
    return TieBanEngine().interpret_life(3, 5)["details"]


def _flatten(details):
    return [tw for items in details.values() for tw in items]


def test_detects_fake_tieban_verse_no():
    details = _tieban_details()
    verses = {tw.get("verse_no", 0) for tw in _flatten(details)}
    fake_no = next(n for n in (9999, 8888, 7777, 6666) if n not in verses)
    draft = f"考刻既定，条文{fake_no}明言吉凶。"
    report = Critic().validate(draft, {"tieban": {"details": details}})
    assert not report.passed
    assert any(str(fake_no) in i and "条文号" in i for i in report.issues)


def test_detects_fake_tieban_verse_no_di_form():
    details = _tieban_details()
    verses = {tw.get("verse_no", 0) for tw in _flatten(details)}
    fake_no = next(n for n in (9999, 8888, 7777) if n not in verses)
    report = Critic().validate(f"命书第{fake_no}条言之凿凿。", {"tieban": {"details": details}})
    assert any(str(fake_no) in i and "条文号" in i for i in report.issues)


def test_detects_fake_tieban_id():
    details = _tieban_details()
    report = Critic().validate("命书TB-R-99999条言之凿凿。", {"tieban": {"details": details}})
    assert any("TB-R-99999" in i and "条文编号" in i for i in report.issues)


def test_detects_fake_tieban_quote():
    details = _tieban_details()
    # 人为注入错误：编造一段从未存在于本盘命中条文的正文
    draft = "条文有云：「祖业田庄遍九州，妻贤子孝福无边」。"
    report = Critic().validate(draft, {"tieban": {"details": details}})
    assert not report.passed
    assert any("引文" in i for i in report.issues)


def test_tieban_consistent_quote_and_number_pass():
    details = _tieban_details()
    hit = next(tw for tw in _flatten(details)
               if tw.get("verse_no", 0) >= 100
               and 4 <= len(tw.get("text", "")) <= 40
               and "「" not in tw["text"] and "」" not in tw["text"])
    # 全文引用 + 片段引用（取前 4 字）均应通过
    draft = f"考刻得条文{hit['verse_no']}，云：「{hit['text']}」。又见「{hit['text'][:4]}」之断。"
    report = Critic().validate(draft, {"tieban": {"details": details}})
    assert report.passed, report.issues


def test_tieban_predicted_tiaowen_shape_checked():
    details = _tieban_details()
    hit = next(tw for tw in _flatten(details) if tw.get("verse_no", 0) >= 100)
    draft = f"条文{hit['verse_no']}：「纯属虚构的正文内容」。"
    report = Critic().validate(draft, {"tieban": {"predicted_tiaowen": [hit]}})
    assert any("引文" in i for i in report.issues)
    assert not any("条文号" in i for i in report.issues)


def test_tieban_no_tiaowen_skips_check():
    # 引擎降级（无命中条文）时无事实基准，不产生误报
    report = Critic().validate("条文9999曰：「虚构正文」。", {"tieban": {"tiaowen_count": 0}})
    assert report.passed, report.issues
