"""事实校验器测试：星曜亮度、四化映射、六壬骨架。"""

from src.validator import FactValidator, SIHUA, ZIWEI_BRIGHTNESS


def test_valid_ziwei_brightness():
    chart = {
        "palaces": {
            "命宫": {"position": "午", "major_stars": [
                {"name": "紫微", "brightness": "庙", "type": "主星"}]},
        }
    }
    passed, errors = FactValidator.validate_ziwei(chart)
    assert passed is True
    assert errors == []


def test_invalid_ziwei_brightness_zhou_miao():
    # 紫微在丑宫为陷，不应标庙
    chart = {
        "palaces": {
            "命宫": {"position": "丑", "major_stars": [
                {"name": "紫微", "brightness": "庙", "type": "主星"}]},
        }
    }
    passed, errors = FactValidator.validate_ziwei(chart)
    assert passed is False
    assert any("紫微在丑不能为庙" in e for e in errors)


def test_unknown_star_ignored():
    chart = {
        "palaces": {
            "命宫": {"position": "午", "major_stars": [
                {"name": "天魁", "brightness": "庙", "type": "辅星"}]},
        }
    }
    passed, errors = FactValidator.validate_ziwei(chart)
    assert passed is True


def test_sihua_mapping():
    assert FactValidator.validate_sihua("甲", "禄", "廉贞") is True
    assert FactValidator.validate_sihua("甲", "忌", "太阳") is True
    assert FactValidator.validate_sihua("甲", "禄", "紫微") is False
    assert FactValidator.validate_sihua("乙", "科", "紫微") is True


def test_sihua_unknown_gan():
    assert FactValidator.validate_sihua("?", "禄", "廉贞") is False


def test_brightness_tables_are_complete():
    # 每个已登记主星至少有一个庙位（防退化配置）
    for star, rules in ZIWEI_BRIGHTNESS.items():
        assert rules["庙"] or rules["旺"], f"{star} 缺庙/旺配置"


def test_sihua_table_covers_ten_gan():
    assert set(SIHUA.keys()) == set("甲乙丙丁戊己庚辛壬癸")


def test_liuren_skeleton():
    passed, errors = FactValidator.validate_liuren({})
    assert passed is True
    assert errors == []
