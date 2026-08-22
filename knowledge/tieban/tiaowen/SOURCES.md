# 真实条文来源与许可（SOURCES）

> `tiaowen_real_*.json` 共 12,000 条的完整溯源链。本文件不会被引擎加载（仅识别 `*.json`）。

## 溯源链

| 层级 | 来源 | 锚点 | 说明 |
|------|------|------|------|
| 原文 | 清代刊行《铁板神数》条文 | 已入公版 | 条文正文（断词）为公版古籍内容 |
| 原始录入 | [xaminxan/tiebanshenshu](https://github.com/xaminxan/tiebanshenshu) | commit `e17f30cb65b7` | GB18030 编码 CSV（`数据库/铁板神数-条文断词.csv`），未声明许可证，README 注「仅供学习交流」 |
| UTF-8 整理 | [Nanphy/TiebanshenshuOS](https://github.com/Nanphy/TiebanshenshuOS) | commit `785dc871d523` | `DB/List.csv`，子集~亥集十二卷、号 1001–13000、带年龄注记 |
| 结构化汇编 | [hackninety/tbss-ts-lib](https://github.com/hackninety/tbss-ts-lib) | commit `738116066194` | `docs/corpus/verses/tiaowen.csv`；汇编许可 **CC BY-NC 4.0** |

配套资源（未随本库入库，实现真实考刻算法时取用）：十四考取数表十五张
（`docs/corpus/tables/14-*.csv`）、考刻方法文献（`docs/corpus/method/`）、注解精选 29 条。

## 保真度声明

- 条文文本为社区数字化转录，**未与刊本逐字校勘**（上游自评：第三方整理），故 `meta.confidence = 中`；
- `meta.verified = true` 指的是"正文确为传统流传条文（非本项目编造）"，不表示逐字校勘完成；
- 跨源歧异示例：条文 1004 「行人为难」（本源）vs「行人泥滑」（知乎专栏源），见 tbss-ts-lib `docs/sources.md`。

## 本项目的加工（与原文区分）

1. **刻分（ke/fen）归属为本项目自建索引**，非传统考刻取数结果。规则：`idx = 条文号-1001; ke = idx % 8; fen = (idx//8) % 10`（每槽恰 150 条，确定性可复现）。实现真实取数算法后应整体替换。
2. **category 为关键词自动归类**（父母>兄弟>夫妻>子女>流年>自身），非原文自带分类。
3. 原始字段 `集`/`条文数`/`年龄` 保留为 `volume`/`verse_no`/`ages`。

## 许可约束（重要）

- 汇编许可为 **CC BY-NC 4.0：署名 + 非商业性使用**。使用这些条文必须保留本溯源链；
- **本项目若转商用，必须先移除本数据或另获授权**；
- 上游权利人提出异议时，应按上游同样原则处理（移除或替换）。

## 复现

```bash
python scripts/import_tiaowen_real.py                 # 从锁定 commit 的 URL 拉取
python scripts/import_tiaowen_real.py --input tiaowen.csv   # 本地 CSV
```
