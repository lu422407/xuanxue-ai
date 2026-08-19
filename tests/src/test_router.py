"""统一路由测试：意图识别、参数解析、引擎加载、input 构建。"""

from src.router import XuanXueRouter


def test_route_ziwei():
    router = XuanXueRouter()
    result = router.route("1990-08-16 14:30 男，请排紫微斗数命盘")
    assert result["method"] == "紫微斗数"
    assert result["available"] is True
    assert result["confidence"] > 0
    assert result["engine"] is not None


def test_route_bazi():
    router = XuanXueRouter()
    result = router.route("1990年5月1日8点30分 男，排八字看大运流年")
    assert result["method"] == "八字"
    assert result["available"] is True
    assert result["engine"] is not None


def test_route_liuren_available_state():
    router = XuanXueRouter()
    result = router.route("甲子日卯时占事业，大六壬")
    assert result["method"] == "大六壬"
    # 六壬当前为骨架实现，路由应能识别但不承诺可用
    assert "setup_hint" in result or result["available"]


def test_route_unknown():
    router = XuanXueRouter()
    result = router.route("今天天气怎么样")
    assert result["method"] == "unknown"
    assert result["available"] is False


def test_extract_params_solar_dash():
    router = XuanXueRouter()
    params = router._extract_params("1990-08-16 14:30 男")
    assert params["year"] == 1990
    assert params["month"] == 8
    assert params["day"] == 16
    assert params["hour"] == 14
    assert params["gender"] == "男"
    assert params["date_type"] == "solar"


def test_extract_params_lunar():
    router = XuanXueRouter()
    params = router._extract_params("农历1990年7月3日子时 女")
    assert params["year"] == 1990
    assert params["month"] == 7
    assert params["day"] == 3
    assert params["hour"] == 0
    assert params["gender"] == "女"
    assert params["date_type"] == "lunar"


def test_extract_known_facts():
    router = XuanXueRouter()
    params = router._extract_params("铁板神数考刻，父属龙母属蛇兄弟三人")
    facts = params["known_facts"]
    assert facts["father_zodiac"] == "龙"
    assert facts["mother_zodiac"] == "蛇"


def test_build_input():
    router = XuanXueRouter()
    params = router._extract_params("1990-08-16 14:30 男")
    inp = router.build_input(params)
    assert inp["birth_datetime"] == "1990-08-16 14:00:00"
    assert inp["timezone_offset"] == 8
    assert inp["calendar"] == "solar"
    assert inp["gender"] == "男"


def test_router_engine_compat_with_bazi():
    """路由命中的引擎必须能跑现有 BaseEngine.calculate。"""
    router = XuanXueRouter()
    result = router.route("1990年5月1日8点30分 男，排八字")
    inp = router.build_input(result["parsed_params"])
    chart = result["engine"].calculate(inp)
    assert chart["system"] == "bazi"
    assert set(chart["pillars"].keys()) == {"year", "month", "day", "hour"}
