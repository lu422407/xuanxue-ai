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


# ---- 六壬结构校验 / 亮度表完整性 ----

def test_validate_liuren_structural_ok():
    from src.validator import FactValidator
    chart = {
        "四课": {"一课": ["戌", "戊"], "二课": ["卯", "戌"],
                 "三课": ["酉", "辰"], "四课": ["寅", "酉"]},
        "三传": {"初传": "寅", "中传": "未", "末传": "子"},
        "天地盘": {z: z for z in "子丑寅卯辰巳午未申酉戌亥"},
    }
    ok, errors = FactValidator.validate_liuren(chart)
    assert ok, errors


def test_validate_liuren_detects_structure_errors():
    from src.validator import FactValidator
    bad = {
        "四课": {"一课": ["戌", "戊"]},                      # 缺三课
        "三传": {"初传": "寅", "中传": "未"},                 # 缺末传
        "天地盘": {"子": "巳"},                              # 只有 1 支
    }
    ok, errors = FactValidator.validate_liuren(bad)
    assert not ok
    assert len(errors) == 3


def test_brightness_table_consistency():
    from src.validator import FactValidator
    ok, errors = FactValidator.validate_brightness_table()
    assert ok, errors


def test_brightness_table_detects_conflict(monkeypatch):
    import src.validator as v
    broken = {"紫微": {"庙": ["子"], "旺": ["子"], "陷": []}}  # 子同时庙/旺
    monkeypatch.setattr(v, "ZIWEI_BRIGHTNESS", broken)
    ok, errors = v.FactValidator.validate_brightness_table()
    assert not ok
    assert any("子" in e for e in errors)
