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
| 13 | validate_ziwei 亮度校验空转（原二档 #1） | ①`ziwei_engine` 主星输出改为 `{name, brightness}`（py-iztro 实测值，不再丢弃）；②亮度表重写为 **py-iztro 全枚举实测表·全 14 主星 × 12 宫**（2 年干×12 农历月×30 日×13 时辰=1440 盘，(星,宫)→亮度 纯函数零冲突；旧简化表多处错误，如紫微实无陷、太阳庙仅卯）——表定位为 iztro 行为快照（升级回归锚点），非独立考据；③validate_ziwei 改为亮度域校验+全档位位置比对；④10 紫微+1 铁板黄金用例重固化（考刻结论断言不变后再生效）；⑤critic/orchestrator/fusion 消费方兼容 dict 星曜；⑥完备性守卫测试（14 星 × 12 宫覆盖恰全集） |
| 14 | check_hallucination / check_safety 是占位（原二档 #3） | ①check_hallucination 接 citation_checker：`[source:id]` 声称须在本次检索结果（或知识库）中存在，无基准不臆断；②check_safety 扩展医疗越界/法律越界/财务保证三域（保留 v1 绝对化承诺原语义）；③两者接线进 `_explain` 回退门（与命盘校验同权：触发即回退确定性摘要+warning 日志），不留死代码 |
| 15 | （2026-08-29 端到端验收发现）奇门/六爻静默无视占卜时刻 | 传了 divination_datetime 时奇门/六爻仍按出生时刻起盘（六壬一直正确）——静默错误结果比报错更危险。修复：`calendar_utils.resolve_divination_datetime()`（优先占时、缺省回落、占时同样适用真太阳时校正），两引擎接入并在 input_echo 回显；编排层 dispatch 占时透传从仅六壬放开至奇门/六爻；schema 描述同步。新增 5 测试（回落逻辑×3 + 引擎级×2，CLI 缺失时 skip）；验收实盘与 CLI 直调锚点逐字一致（处暑/阴遁4局/天冲/伤） |
| 16 | （同日）`/api/orchestrate` 确定性摘要四柱显示英文键名 | 摘要改为 年:庚午 月:庚辰 日:丙寅 时:壬辰（纯展示层，确定性测试仅锚定两轮一致+包含关系，不受影响） |

## 一.5、端到端验收（2026-08-29 首次真实 API 冒烟，Windows 本机）

- 环境：uvicorn 127.0.0.1:8000，默认开发密钥（自用定位下可接受）。
- 自验矩阵：health ✓ / chart 200（八字四柱+紫微 12 宫含亮度）/ orchestrate 200（双引擎+3 引用跨 classics/rules/cases 三类+免责声明+8 span trace 可回溯）/ engine·liuren 200（月将巳=处暑，占时生效）/ engine·tieban 200（考刻二刻0分，命中 150 条真实条文）/ engine·qimen 200 / 错误密钥 401 ✓ / 服务日志零 ERROR。
- pythonmonkey 线程崩溃史确认已规避：编排层 ziwei 走 `ZiWeiProcessEngine` 进程代理（`ai_orchestrator.py` ENGINES 表），API 线程池实测无崩溃。
- **用户终验进行中**（验收方式已定：用户亲自判定）；跨库交叉验证（术数正确性裁判）为后续独立工作项。

## 二、可解决待做（技术无障碍，按价值排序）

1. **Docker 镜像内编译 ZhouYiLab CLI**（多阶段构建，builder 用 Linux LLVM 镜像）；工程量大，CI 已验证 Linux 可编，配方现成。**自用定位下降为低优先**（本机无 Docker 无法验证，需配 CI docker-build job 才算闭环）。
2. **六壬占卜时刻未应用真太阳时校正**：`liuren_engine` 直接 `_parse_datetime_string` 占时（无 true_solar_time/longitude 处理），与新的 `resolve_divination_datetime`（奇门/六爻用）语义不一致；对齐即可，注意六壬黄金用例回归。

## 三、需要决策（做不做/怎么做取决于产品形态）

> **项目定位已决策（2026-08-29）：自用研究/工具，不对外提供服务。**
> 由此推论：①铁板条文 CC BY-NC 4.0 不构成阻塞（商用前必须重审本清单与 SOURCES.md）；
> ②Docker 镜像内编译 CLI 降级为低优先（本机无 Docker，只能写不能测；自用直接本机跑）；
> ③限流/tracing/cost_tracker 的进程内存版对单用户够用，Redis 不引入；
> ④LLM 生产接入可选项（本地 vllm 或云 API 均可，按需再定）。

1. **数据安全红线** —— **已决策（2026-08-26，commit 45147d0）：降级路线。** README 改为「演示版不落盘、数据仅存内存；加密存储与入库脱敏为后续能力，当前未启用」，误导性声明已消除。若未来转为对外服务，重新评估做实方案（sqlalchemy 持久层 + 加密，docker-compose 已有 postgres 定义）。
2. **LLM 生产接入**：provider 壳（openai/claude/deepseek）0% 覆盖率、未实测；自用定位下非必需（确定性路径+RuleBasedLLM 已可演示），接入时再选型。
3. **术数内容正确性的跨库交叉验证**（裁判方式已定：找独立实现对同一批命盘比对，分歧清单交用户裁决；未开始）。candidates：tyme4cpp（已 vendor 在 ZhouYiLab，注意与 iztro 是否同源）、lunar-python 系、其它开源排盘库；比对范围建议从亮度/四化/安星位置开始。

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
