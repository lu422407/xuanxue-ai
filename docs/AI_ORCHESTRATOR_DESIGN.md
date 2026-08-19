# AI Orchestrator 设计文档（术数 AI 编排层）

> 版本：v0.1.0（设计稿，本阶段**只产出文档，不实现代码**）
> 日期：2026-08-19
> 范围：`xuanxue-ai` 在 `router / engine / validator` 之上新增的「AI 编排层」
> 核心原则：**LLM 不负责计算。LLM 只负责理解问题、选择术数、调用引擎、综合结果、生成解释。**

---

## 0. 为什么需要这一层

现有分层已经具备：

| 层 | 模块 | 职责 |
|----|------|------|
| 路由 | `src/router.py::XuanXueRouter` | 关键词打分识别**术数类型**（紫微/六壬/八字/铁板/奇门/六爻/…） |
| 计算 | `engines/*::BaseEngine.calculate` | **确定性**排盘，纯函数，禁止调用 LLM |
| 校验 | `src/validator.py::FactValidator` | 紫微亮度/四化/六壬等**硬性规则**校验 |
| Agent 原语 | `agents/*`（guardrails / intent_router / planner / executor / critic / memory） | LLM 安全、话题意图、计划、执行、批判 |
| LLM | `llm/*::BaseLLM` | `generate(system_prompt, user_content)` / `classify(question)` |

**缺口**：当前 `agents/orchestrator.py` 的链路是
`Guardrails → IntentRouter(话题意图) → Planner → Executor → LLM → Critic`，
其中 `IntentRouter` 识别的是**话题意图**（career/wealth/relationship/life/chart/general），
`Planner`/`Executor` 的 `ENGINE_REGISTRY` **只覆盖 `bazi`/`ziwei`**。
它**没有**接入 `XuanXueRouter`（术数类型选择），**不支持**六壬/铁板/奇门/六爻，
也**不做多术数综合**。

**AI Orchestrator 的目标**：把「术数类型选择 + 多引擎确定性计算 + 事实校验 + 跨术数综合 + 解释生成」
编排为一个统一、可测试、LLM 不计算的顶层服务。

---

## 1. 架构图

```
                          ┌─────────────────────────────────────────────┐
   用户问题 (自然语言)    │              AI Orchestrator (顶层编排)         │
   ────────────────────► │                                               │
                          │  ① Shield         agents.guardrails.check     │
                          │       │ 拦截注入/越狱/泄露                      │
                          │       ▼                                       │
                          │  ② Understander  LLM 解析                      │
                          │       │ 问题→{原始意图, 出生参数, 已知事实,      │
                          │       │        候选术数, 占卜时刻?}             │
                          │       ▼                                       │
                          │  ③ Selector      XuanXueRouter + LLM 候选      │
                          │       │ 术数类型打分 + 可用性 + setup_hint      │
                          │       │ 支持多术数同时选择                       │
                          │       ▼                                       │
                          │  ④ Dispatcher    engines.*.calculate()        │
                          │       │ ├─ 紫微 / 八字 / 六壬 / 铁板(verify_kefen)│
                          │       │ └─ 奇门 / 六爻 → 未编译则 setup_hint    │
                          │       │ （确定性计算，LLM 不参与）              │
                          │       ▼                                       │
                          │  ⑤ Validator     FactValidator + Critic        │
                          │       │ 引擎输出硬性规则校验 + 文本一致性批判    │
                          │       ▼                                       │
                          │  ⑥ Synthesizer  跨术数交叉印证                  │
                          │       │ 共识 / 分歧 / 引用（不计算，只比对）     │
                          │       ▼                                       │
                          │  ⑦ Explainer     LLM 生成解释（仅叙述引擎数据） │
                          │       │ 受 Critic 约束；失败回退原始命盘         │
                          │       ▼                                       │
                          │  ⑧ Disclaimer    agents.guardrails.wrap_disclaimer
                          └─────────────────────────────────────────────┘
                                       │
                                       ▼
                              结构化响应 (AIOrchestratorResponse)
```

> ①②③属于「理解/选择」，④是「确定性计算」（引擎），⑤⑥是「校验/综合」，
> ⑦是「解释生成」。LLM 只出现在 ②⑦（及 ③的候选精炼），**绝不出现在 ④**。

---

## 2. 模块职责（建议落地位置 `agents/ai_orchestrator.py`）

| 步骤 | 职责 | 复用现有 | 是否调用 LLM | 是否计算 |
|------|------|----------|--------------|----------|
| ① Shield | Prompt 注入/越狱/泄露拦截 | `agents.guardrails.check` | 否 | 否 |
| ② Understander | 自然语言→结构化意图（出生时间/性别/已知事实/占卜时刻/候选术数/业务话题） | `agents.intent_router.IntentRouter` 扩为「术数感知」 | 是（解析） | 否 |
| ③ Selector | 术数类型选择：融合 `XuanXueRouter.route` 关键词分 + ②候选；过滤不可用引擎并附 `setup_hint` | `src/router.py::XuanXueRouter` | 可选（精炼） | 否 |
| ④ Dispatcher | 对所选可用术数逐一 `engine.calculate(input)`；铁板走 `verify_kefen(known_facts)`；六壬用 `divination_datetime` | `engines/*::BaseEngine`、`TieBanEngine.verify_kefen` | 否 | **是（引擎做）** |
| ⑤ Validator | 逐个引擎 `FactValidator.validate_*`；LLM 文本 `Critic.validate` | `src/validator.FactValidator`、`agents.critic.Critic` | 仅批判 | 否 |
| ⑥ Synthesizer | 跨术数交叉印证（如八字日主 vs 紫微命宫主星；铁板六亲 vs 八字十神）；产出 `consensus/divergences` | 新增（纯比对，无 LLM） | 否 | 否 |
| ⑦ Explainer | 基于 ④⑤⑥ 的结构化数据生成自然语言解释 | `agents.orchestrator._llm_generate` 思路 | 是（叙述） | 否 |
| ⑧ Disclaimer | 注入免责声明 | `agents.guardrails.wrap_disclaimer` | 否 | 否 |

**关键约束（与 `engines/base.py` 一致）**：
- 引擎是纯函数，相同输入同输出；非法输入抛 `EngineError`，**禁止静默返回错误结果**。
- LLM 在任何解释中**不得编造/改动**星曜、宫位、干支；`Critic` 负责兜底，失败时回退原始命盘（`Orchestrator._fallback_answer`）。

---

## 3. 输入/输出协议

### 3.1 请求

```jsonc
{
  "question": "我是男，1990年阳历8月16日14:30生，想看事业和父母情况",
  "user_context": {
    "birth_input": {                      // 可选，缺省由 Understander 从 question 抽取
      "birth_datetime": "1990-08-16 14:30:00",
      "timezone_offset": 8,
      "calendar": "solar",
      "gender": "男"
    },
    "divination_datetime": null,         // 六壬占卜时刻，缺省回落 birth_input
    "known_facts": {                      // 铁板考刻已知事实
      "father_zodiac": "龙", "mother_zodiac": "蛇",
      "siblings": "3", "self_rank": "2"
    },
    "preferences": {}                     // 流派偏好（中州派等），来自 MemoryAgent
  },
  "trace_id": null                       // 可空，Observability 链路追踪
}
```

### 3.2 响应

```jsonc
{
  "answer": "（LLM 生成的解释，附免责声明）",
  "trace_id": "tr_xxx",
  "systems_invoked": ["ziwei", "bazi", "tieban"],   // 实际调用的可用引擎
  "systems_skipped": [                                // 不可用（如未编译）
    {"system": "qimen", "reason": "C++ 未编译", "setup_hint": "..."}
  ],
  "engine_results": {                                 // 各引擎原始结构化命盘
    "ziwei": { "...": "..." },
    "bazi":  { "...": "..." },
    "tieban": { "verified_ke": 0, "verified_fen": 3, "predicted_tiaowen": [...] }
  },
  "validation": { "passed": true, "issues": [] },    // FactValidator + Critic
  "synthesis": {                                      // 跨术数综合
    "consensus": ["日主丙火与命宫主星一致"],
    "divergences": [],
    "citations": []
  },
  "blocked_reason": null,
  "disclaimer": "以上分析为传统术数文化的知识性推演……"
}
```

### 3.3 中间数据结构（供测试断言）

- `EngineCall { system, input, available, result?, error? }`
- `ValidationReport`（复用 `agents/critic.ValidationReport`：`passed`, `issues`）
- `SynthesisResult { consensus: list[str], divergences: list[str], citations: list[str] }`

---

## 4. 与现有组件的边界（避免重复造轮子）

- **不重写 `XuanXueRouter`**：Selector 直接复用其 `route()` / `build_input()` / `available_engines` / `setup_hint`。
- **不重写 `FactValidator`**：⑤ 直接调用 `validate_ziwei / validate_sihua / validate_liuren`。
- **不重写 `Orchestrator`**：AI Orchestrator 是更上层的「多术数」版本；现有 `Orchestrator`（话题意图 + bazi/ziwei）可保留为单术数/轻量入口，或逐步收敛。
- **不重写 `Executor`**：扩展其 `ENGINE_REGISTRY` 以覆盖 `router.available_engines` 的全部可用引擎（含 liuren/tieban）。
- **不引入不可追踪的大型依赖**：仅依赖已锁定的 `requirements.txt` 与子模块；LLM 走 `llm/*` 抽象。

---

## 5. 后续开发路线（编码阶段，不在本设计文档内实现）

| 阶段 | 范围 | 可测试性 |
|------|------|----------|
| A. MVP 单术数贯通 | `agents/ai_orchestrator.py` 骨架 + Selector 接 `XuanXueRouter`；Dispatcher 走 `Executor`（扩 registry）；用 `tests/fake_llm.FakeLLM` 跑通 bazi/ziwei/liuren/tieban 单链路 | 端到端 FakeLLM 测试，断言 `systems_invoked` / `engine_results` 结构 |
| B. 多术数综合 | Synthesizer 实现八字↔紫微交叉印证（日主/命宫一致性）；`SynthesisResult` 协议 | 纯函数单测：给定两份命盘断言 consensus/divergences |
| C. 铁板考刻集成 | Dispatcher 对 tieban 调 `verify_kefen(known_facts)`，串 `knowledge/tieban/tiaowen` 条文 | 断言 `predicted_tiaowen` 来自 tiaowen_db，且 `verify_kefen` 确定性 |
| D. 奇门/六爻门控 | 未编译时 Selector 返回 `systems_skipped` + `setup_hint`（不抛 NotImplementedError 给用户，由 Orchestrator 优雅降级） | 断言 `systems_skipped` 含 qimen/liuyao 与正确 hint |
| E. RAG 溯源 | 接入 `rag/retriever` + `rag/citation_checker` 为解释附古籍引用；`synthesis.citations` 填充 | 断言 citation 命中且可被 citation_checker 校验 |
| F. 可观测性 | 复用 `observability.tracing` / `cost_tracker` 记录每步 span 与 LLM 调用次数上限 | 断言 trace 含 8 个 span |

**验收红线（沿用项目约束）**：
1. 不删除/削弱任何现有测试（当前 153 passed 不可退化）。
2. 不把 `NotImplementedError` 改成假实现；不可用引擎必须显式门控并附 `setup_hint`。
3. LLM 文本若被 `Critic` 判为不一致，必须回退原始命盘，**绝不传播编造内容**。
4. 所有新增模块必须有对应测试（FakeLLM 离线可跑，不依赖真实 API）。

---

## 6. 风险与备注

- **六壬占卜时刻语义**：六壬起课用 `divination_datetime`（占卜时刻），非出生时刻；Dispatcher 须据此区分输入（已在 `engines/liuren_engine.py` docstring 约定）。
- **铁板降级**：紫微排盘失败时 `verify_kefen` 走直接条文检索；Orchestrator 应透传 `method` 字段让用户知晓。
- **kefen_traits.json 位置**：若未来引入考刻特征文件，须置于 `knowledge/tieban/`（上一级），勿与 `tiaowen/*.json` 同目录（见 `knowledge/tieban/tiaowen/SCHEMA.md` §5），否则会被 `_load_tiaowen` 误当条文加载。
- **多术数一致性无权威标准**：Synthesizer 的 consensus/divergence 为「比对呈现」，非「裁判结论」；解释中须标明各术数独立结论，避免合成出伪确定性。
