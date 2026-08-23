# 底线妥协清单（COMPROMISES）

> 2026-08-22 全面审计产出。记录项目在"红线声明 vs 实际执行"上的所有已知差距，
> 分为四档：**本轮已解决 / 可解决待做 / 需要决策 / 受约束暂不可解决**。
> 原则：占位数据不得标记真实、降级必须可见、红线要么执行要么改声明。

---

## 一、本轮已解决（2026-08-22 第三批 · 2026-08-23 Windows 接手续做）

| # | 原问题 | 解决方式 |
|---|--------|----------|
| 0 | 铁板神数无真实条文（原列四档"需素材"） | **素材已在 GitHub 找到并全量导入**：12,000 条清代公版条文（溯源链 xaminxan→Nanphy→tbss-ts-lib，锁定 commit），`knowledge/tieban/tiaowen/tiaowen_real_*.json`，溯源与许可见该目录 SOURCES.md。**注意：①CC BY-NC 4.0 禁止商用；②ke/fen 为本项目自建索引（规则见 SCHEMA.md §1），非传统考刻取数；③分类为关键词自动归类** |
| 1 | 黄金测试只盖 bazi/ziwei（2/6 引擎），"准确性红线"对其余引擎为空 | 补齐 qimen×2 / liuyao×2 / liuren×1 / tieban×1 黄金用例（奇门用例与 demo 程序输出交叉验证一致：阳遁9局/天蓬/休）；qimen/liuyao 无 CLI 时 skip，CI cpp job 强制真跑 |
| 2 | Critic 防幻觉只护紫微+八字，四系统编造不被抓 | 扩展 `_check_qimen`（九星/八门/八神）、`_check_liuyao`（爻位-六神对应/六亲爻/纳甲干支）、`_check_liuren`（月将）；注意六神按爻位轮排全覆盖，全局存在性校验无意义，已用位置校验 |
| 3 | 新编排链路零 trace，Phase F"8 span"名存实亡 | `ai_orchestrator.run()` 全部 8 阶段接 `tracer.span()`，trace_id 缺省自动生成；`cost_tracker` 记录 engines / rag_searches / llm_calls（仅 LLM 真实成功时计） |
| 4 | LLM 解释失败静默回退、无日志 | 回退时 `logger.warning`，运维可见 |
| 5 | `_extract_birth_params` / intent_router 两处 `except: pass` | 均加 `logger.warning` |
| 6 | 未设 `XUANXUE_API_KEYS` 时默认密钥静默生效 | 启动时显著告警"生产环境必须配置独立密钥" |
| 7 | `validate_liuren` 是空骨架 | 结构层校验：四课 4 项、三传 3 传、天地盘 12 支 |
| 8 | 亮度表数据无自检（validate_ziwei 字符串契约下空转问题的一半） | 新增 `validate_brightness_table()`：宫位不得同时列两个亮度档（现有 4 星数据通过；扩表时 CI 兜底） |
| 9 | （前一批）CI 不编 C++、奇门链路静默 skip | cpp-cli job：Linux clang-20/libc++ 编译并真跑全量，"出现 skip 即失败" |
| 10 | Critic 补 tieban（原二档 #2） | `_check_tieban`：条文号（"条文5001"/"第5001条"/TB-R 编号）与引文（引号内 ≥4 字，支持片段）必须来自本盘考刻实际命中的条文（predicted_tiaowen/details），防 LLM 编造；引擎降级无条文时不误报 |
| 11 | RAG 首条偏置（原二档 #3） | `_collect_citations` 按 category 轮转交错（类内保分数序、类别序 sorted 确定性），classics/rules/cases 各占一席后再按分补齐，缓解 `classic_ziwei_001` 类霸榜 |
| 12 | （2026-08-23）Windows 无 VS/MSYS2，ZhouYiLab CLI 编译路径不通 | WinLibs GCC 16.1 + CMake 4.4（`CMAKE_CXX_MODULE_STD` + experimental UUID）编译成功；fork 三处修复：magic_enum 模块在 GCC 下走 header 模式（purview 文本包含 mingw CRT 头与 import std 冲突）、补 `<format>` 头、链接 `stdc++exp` + `-static`（CLI 自包含，免疫 DLL 地狱） |

## 二、可解决待做（技术无障碍，按价值排序）

1. **validate_ziwei 亮度校验对字符串契约生效**：需要引擎输出亮度字段（py-iztro 原始数据里有 `brightness`，`ziwei_engine.py` 目前丢弃了）或改为查表比对。改引擎输出会破坏 10 个紫微黄金用例，需同步再固化。
2. **Docker 镜像内编译 ZhouYiLab CLI**（多阶段构建，builder 用 Linux LLVM 镜像）；工程量大，CI 已验证 Linux 可编，配方现成。
3. **critic.check_hallucination / check_safety 做实**：前者可接 citation_checker（模块现成），后者目前只有一条正则。

## 三、需要决策（做不做/怎么做取决于产品形态）

1. **数据安全红线落地**：README 承诺"出生时间加密存储、案例入库脱敏"，但 `database/`（含 encryption.py）是死代码、`rag/desensitization.py` 无调用方。两条路二选一：
   - 做实：API 接 sqlalchemy 持久层 + 加密 + 删除接口落库（docker-compose 已有 postgres 服务定义）；
   - 降级：README 改为"演示版不落盘，数据仅存内存"，删除误导性承诺。
   **当前状态危险点：代码看起来实现了安全要求，实际没有任何数据经过它。**
2. **限流/tracing/cost_tracker 多副本共享**：现为进程内存版，重启清零、多实例不共享；docker-compose 已定义 redis 服务，接不接需引入 redis 依赖的决策。
3. **LLM 生产接入**：provider 壳（openai/claude/deepseek）0% 覆盖率、未实测；接入哪个、API key 管理方式需决策。

## 四、受约束暂不可解决

1. **铁板神数真实条文的"传统考刻取数"接入**：真实条文已入库（见一档 #0），但 (ke,fen)→条文 的映射仍为自建索引；实现真实取数需按十四考取数表重写引擎路径（受"不修改 tieban_engine 核心算法"约束，需单独决策），取数表与文献已在溯源上游备齐。
2. **RAG 真语义向量**：离线确定性红线与本地 embedding 模型依赖冲突；哈希向量 + bigram 是当前约束下的设计取舍，知识库扩大后检索质量会受限。
3. **Apple Silicon pythonmonkey**：无 arm64 机器可验证；紫微链路在该平台可能不可用，需备选方案。
4. ~~CI 首轮运行的环境注入抖动~~ **已根治（2026-08-22 第四批）**：CLI 发现改为文件系统探测（CI 编译目录固定为 `build/`，即 bridge 第一候选路径），不再依赖 `ZHOUYILAB_CLI` 环境变量注入；另加 CLI 冒烟前置断言。同轮修复 `_load_tiaowen` 的 glob 不排序问题（跨文件系统加载顺序不定，曾致 tieban 黄金用例跨平台失败）。

---

## 维护约定

- 新增妥协时必须登记到本清单对应档位，写明原因与触发条件；
- 二、三档条目解决后移入一档并注明方式；
- README 的红线声明与本清单冲突时，要么补实现、要么改声明，不允许长期分叉。
