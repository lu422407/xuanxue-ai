# 铁板神数条文库（tiaowen）数据结构规范

> 版本：v0.1.0
> 定位：`knowledge/tieban/tiaowen/` 下的条文数据，由 `engines/tieban_engine.py` 加载。
> 设计原则：**数据驱动、与算法解耦、向前可扩展**。本文件只定义数据结构，不修改引擎算法。

---

## 1. 文件组织约定

```
knowledge/tieban/tiaowen/
├── SCHEMA.md                  # 本规范
├── tiaowen_sample.json        # 示例条文（占位，非真实流传本）
├── tiaowen_<主题>.json        # 后续按主题拆分的真实条文集（建议每个文件一个数组）
└── (可选) kefen_traits.json   # ⚠️ 见 §5 约束，切勿与本目录条文混放
```

- 每个 `.json` 文件的内容**要么是条文数组 `[ ... ]`，要么是一条单独条文对象 `{ ... }`**。
  `TieBanEngine._load_tiaowen` 两种形态都兼容。
- 文件名自由，但只识别 `*.json`。`SCHEMA.md` / `*.md` 不会被加载。
- 建议按主题/卷册拆分文件（如 `tiaowen_parents.json`、`tiaowen_siblings.json`），
  便于多人协作与增量更新，避免单文件过大。

---

## 2. 单条条文（tiaowen entry）字段

### 2.1 必需字段（引擎硬性依赖）

| 字段 | 类型 | 取值 | 说明 |
|------|------|------|------|
| `id` | string | 唯一，如 `"TB-0001"` | 条文唯一标识，用于去重与溯源 |
| `ke` | int | `0..7` | 刻。0=初刻,1=一刻,…,7=七刻（见 `tieban_engine._KE_NAMES`） |
| `fen` | int | `0..9` | 分。每刻 10 分 |
| `category` | string | 见 §3 | 分类，决定 `interpret_life` 归组 |
| `text` | string | 非空 | 条文正文（面向用户的解释文本） |

### 2.2 可选字段（事实匹配 / 元数据）

| 字段 | 类型 | 说明 |
|------|------|------|
| `father_zodiac` | string | 父生肖（如 `"龙"`）。用于 `verify_kefen` 直接检索降级匹配 |
| `mother_zodiac` | string | 母生肖 |
| `siblings` | string | 兄弟姐妹数（字符串，如 `"3"`） |
| `self_rank` | string | 自身排行（如 `"2"`） |
| `meta` | object | 扩展元数据，引擎原样透传、不参与计算（见 §4） |

> `ke`/`fen` 是 `TieBanEngine._query_tiaowen_by_kefen` 的主键：
> 考刻定分后按 `(ke, fen)` 精确检索条文。
> `father_zodiac` 等字段仅供紫微排盘失败时的 `_fallback_direct_query` 做顶层键匹配。

---

## 3. category 枚举

`interpret_life` 预置分组键（未知分类会落入 `其他`）：

```
父母 | 兄弟 | 夫妻 | 子女 | 自身 | 流年 | 其他
```

新增分类时，直接写入上述任一值即可；若使用枚举外的值，会归入 `其他`，
**不会报错**，但建议优先使用上述标准分类。

---

## 4. `meta` 扩展块（推荐）

引擎忽略 `meta` 内部字段，但建议统一结构以便工具链消费：

```json
"meta": {
  "source": "条文来源（古籍卷册 / 样本集 / 社区贡献）",
  "verified": false,
  "confidence": "示例 | 高 | 中 | 低",
  "tags": ["父母", "属相", "示例"],
  "note": "补充说明（可空）"
}
```

- `verified=false` 表示未经人工核验，仅为占位/示例。
- 真实条文入册后应将 `verified` 置 `true` 并补全 `source`。

---

## 5. ⚠️ 重要约束（来自引擎实现，请勿违反）

1. **`kefen_traits.json` 不要放在本目录。**
   `TieBanEngine._load_tiaowen` 会 `glob("*.json")` 把所有 json 当作条文加载；
   而 `_load_kefen_traits` 又从同一目录读取 `kefen_traits.json`。
   若二者同目录，`kefen_traits.json` 会被误判为一条缺 `ke/fen/category` 的畸形条文。
   → 若需使用该特征文件，请置于 `knowledge/tieban/`（上一级），或改名避免被 glob 命中。

2. **不要修改 `engines/tieban_engine.py`。**
   本结构是纯数据层；算法（考刻定分、`predict_by_kefen` 偏移推算）保持不变。
   扩充条文只需新增 `.json` 文件，引擎在 `__init__` 时自动加载。

3. **`ke`/`fen` 范围** 必须落在 `0..7` / `0..9`，否则不会被任何考刻结果命中。

4. **`id` 全局唯一**：跨文件 `id` 重复会导致溯源歧义（测试会校验唯一性）。

---

## 6. 扩展性说明

- **新增字段**：直接在条文顶层或 `meta` 内新增键即可，引擎原样透传，零侵入。
- **新增条文**：新增 `.json` 文件，`TieBanEngine` 启动即加载，无需改代码。
- **运行时扩充**：`TieBanEngine.add_tiaowen(tw)` 会追加并写回 `tiaowen_db.json`。
- **多术数综合**：条文可与 `engines/liuren_engine`、`engines/ziwei_engine` 输出
  在 AI Orchestrator 层做交叉印证（见 `docs/AI_ORCHESTRATOR_DESIGN.md`）。

---

## 7. 示例（单条）

```json
{
  "id": "TB-0001",
  "ke": 0,
  "fen": 0,
  "category": "父母",
  "text": "父生肖龙，母生肖蛇，父母康宁。",
  "father_zodiac": "龙",
  "mother_zodiac": "蛇",
  "siblings": "3",
  "self_rank": "2",
  "meta": {
    "source": "示例占位（非真实流传条文）",
    "verified": false,
    "confidence": "示例",
    "tags": ["父母", "属相", "示例"],
    "note": "仅为数据结构占位"
  }
}
```
