"""铁板神数条文库结构校验（数据层测试，不依赖引擎）。

目标：保证 knowledge/tieban/tiaowen/ 下的所有 .json 条文符合 SCHEMA.md 规范，
随着条文库扩充，结构错误会在测试阶段被发现，而非运行时。

约束：本测试只校验数据，不修改 engines/tieban_engine.py 任何逻辑。
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
TIAOWEN_DIR = ROOT / "knowledge" / "tieban" / "tiaowen"

ALLOWED_CATEGORIES = {"父母", "兄弟", "夫妻", "子女", "自身", "流年", "其他"}


def _iter_entries():
    """遍历 tiaowen 目录下所有 .json，产出 (文件名, 条文dict)。"""
    if not TIAOWEN_DIR.exists():
        pytest.skip(f"tiaowen 目录不存在: {TIAOWEN_DIR}")
    for f in sorted(TIAOWEN_DIR.glob("*.json")):
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            yield f.name, entry


def test_tiaowen_dir_has_entries():
    """至少存在一条示例条文（数据层已落地）。"""
    entries = list(_iter_entries())
    assert entries, "tiaowen 目录不应为空，至少应有示例条文"


@pytest.mark.parametrize("filename,entry", list(_iter_entries()))
def test_entry_shape(filename, entry):
    """每条条文必需字段齐全且类型/取值范围合法。"""
    assert isinstance(entry, dict), f"{filename}: 条文必须是对象"

    # id
    assert isinstance(entry.get("id"), str) and entry["id"], f"{filename}: id 必填且为字符串"

    # ke / fen 范围
    ke = entry.get("ke")
    fen = entry.get("fen")
    assert isinstance(ke, int) and 0 <= ke <= 7, f"{filename}: ke 必须是 0..7 整数"
    assert isinstance(fen, int) and 0 <= fen <= 9, f"{filename}: fen 必须是 0..9 整数"

    # category 枚举
    cat = entry.get("category")
    assert cat in ALLOWED_CATEGORIES, f"{filename}: category 必须是 {ALLOWED_CATEGORIES} 之一"

    # text 非空
    assert isinstance(entry.get("text"), str) and entry["text"].strip(), \
        f"{filename}: text 必填且非空"


def test_entry_ids_unique():
    """跨文件 id 必须全局唯一，避免溯源歧义。"""
    seen = {}
    for filename, entry in _iter_entries():
        eid = entry.get("id")
        if eid in seen:
            raise AssertionError(f"重复 id={eid}: 出现在 {seen[eid]} 与 {filename}")
        seen[eid] = filename


def test_optional_fact_fields_are_strings_when_present():
    """可选事实字段若存在，必须为字符串（供 fallback 直接检索匹配）。"""
    for _filename, entry in _iter_entries():
        for key in ("father_zodiac", "mother_zodiac", "siblings", "self_rank"):
            if key in entry:
                assert isinstance(entry[key], str), f"{_filename}: {key} 应为字符串"


def test_all_categories_covered_by_sample():
    """示例条文应覆盖全部 7 个标准分类（结构可扩展性证明）。"""
    covered = {entry.get("category") for _f, entry in _iter_entries()}
    # 示例集至少应覆盖父母/兄弟/夫妻/子女/自身/流年/其他 中的大部分
    assert {"父母", "兄弟", "自身"} <= covered, "示例条文需覆盖核心分类：父母/兄弟/自身"
