#!/usr/bin/env python3
"""导入真实铁板神数条文（12,000 条，清代公版古籍数字化转录）。

数据源（锁定 tbss-ts-lib commit 738116066194）：
  https://github.com/hackninety/tbss-ts-lib → docs/corpus/verses/tiaowen.csv
  上游链路：xaminxan/tiebanshenshu（原始录入 e17f30cb65b7）
          → Nanphy/TiebanshenshuOS（UTF-8 整理 785dc871d523）
          → tbss-ts-lib（结构化汇编，CC BY-NC 4.0）

刻分（ke/fen）归属规则：本项目自建索引，非传统考刻取数——
  idx = 条文号 - 1001
  ke  = idx % 8          （0..7，每刻 10 分）
  fen = (idx // 8) % 10  （0..9）
每个 (ke, fen) 槽位恰好 150 条，确定性可复现。
实现真实取数算法（十四考取数表已在 tbss-ts-lib 提供位）后可替换该索引。

分类规则（关键词优先级）：父母 > 兄弟 > 夫妻 > 子女 > 流年（带年龄注记）> 自身。

用法：
  python scripts/import_tiaowen_real.py --input /path/to/tiaowen.csv   # 本地 CSV
  python scripts/import_tiaowen_real.py                                # 从锁定 URL 拉取
"""

import argparse
import csv
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "knowledge" / "tieban" / "tiaowen"

PINNED_URL = (
    "https://raw.githubusercontent.com/hackninety/tbss-ts-lib/"
    "738116066194/docs/corpus/verses/tiaowen.csv"
)

SOURCE_CHAIN = (
    "清代公版《铁板神数》条文社区数字化转录："
    "xaminxan/tiebanshenshu 原始录入(e17f30cb65b7) → "
    "Nanphy/TiebanshenshuOS UTF-8 整理(785dc871d523) → "
    "hackninety/tbss-ts-lib 结构化汇编(738116066194, CC BY-NC 4.0)"
)

VOLUME_PINYIN = {
    "子集": "zi", "丑集": "chou", "寅集": "yin", "卯集": "mao",
    "辰集": "chen", "巳集": "si", "午集": "wu", "未集": "wei",
    "申集": "shen", "酉集": "you", "戌集": "xu", "亥集": "hai",
}

# 关键词按优先级排列；命中即归类，全部未命中且无年龄注记 → 自身
CATEGORY_KEYWORDS = [
    ("父母", ["父", "母", "椿萱", "双亲", "庭闱"]),
    ("兄弟", ["兄弟", "兄", "弟", "姐妹", "手足", "昆仲"]),
    ("夫妻", ["妻", "夫", "婚", "姻缘", "配偶", "夫妇"]),
    ("子女", ["子息", "儿孙", "后嗣", "子女", "兰桂", "麟儿", "无嗣"]),
]


def classify(text: str, ages: str) -> str:
    for category, keywords in CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return category
    if ages:
        return "流年"
    return "自身"


def kefen(verse_no: int):
    idx = verse_no - 1001
    return idx % 8, (idx // 8) % 10


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="本地 tiaowen.csv 路径（缺省从锁定 URL 拉取）")
    args = parser.parse_args()

    if args.input:
        raw = Path(args.input).read_text(encoding="utf-8")
    else:
        print(f"拉取 {PINNED_URL} ...")
        raw = urllib.request.urlopen(PINNED_URL, timeout=30).read().decode("utf-8")

    rows = list(csv.reader(raw.splitlines()))
    header, data_rows = rows[0], rows[1:]
    if header[:2] != ["集", "条文数"]:
        print(f"表头异常: {header}", file=sys.stderr)
        return 1

    by_volume: dict = {}
    slots: dict = {}
    for row in data_rows:
        if len(row) < 4 or not row[1].strip():
            continue
        volume, verse_no_s, ages, text = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
        if not text:
            continue
        verse_no = int(verse_no_s)
        ke, fen = kefen(verse_no)
        category = classify(text, ages)
        entry = {
            "id": f"TB-R-{verse_no:05d}",
            "ke": ke,
            "fen": fen,
            "category": category,
            "text": text,
            "verse_no": verse_no,
            "volume": volume,
            "ages": ages,
            "meta": {
                "source": SOURCE_CHAIN,
                "verified": True,
                "confidence": "中（第三方整理转录，未与刊本逐字校勘）",
                "tags": ["真实条文", category, volume],
                "note": "ke/fen 为本项目自建确定性索引（规则见脚本头部），非传统考刻取数；"
                        "商用禁止（CC BY-NC 4.0），溯源见 SOURCES.md",
            },
        }
        by_volume.setdefault(volume, []).append(entry)
        slots[(ke, fen)] = slots.get((ke, fen), 0) + 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    counts = {}
    for volume, entries in by_volume.items():
        pinyin = VOLUME_PINYIN.get(volume, volume)
        out = OUT_DIR / f"tiaowen_real_{pinyin}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=1)
        counts[volume] = len(entries)

    total = sum(counts.values())
    slot_sizes = set(slots.values())
    print(f"共导入 {total} 条，{len(counts)} 个集卷文件")
    print(f"(ke,fen) 槽位数: {len(slots)}，每槽条数: {sorted(slot_sizes)}")
    for vol, n in counts.items():
        print(f"  {vol}({VOLUME_PINYIN[vol]}): {n} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
