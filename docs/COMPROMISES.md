# 底线妥协清单（COMPROMISES）

> 2026-08-22 全面审计产出。记录项目在"红线声明 vs 实际执行"上的所有已知差距，
> 分为四档：**本轮已解决 / 可解决待做 / 需要决策 / 受约束暂不可解决**。
> 原则：占位数据不得标记真实、降级必须可见、红线要么执行要么改声明。
>
> 最后更新：2026-09-13（一档新增 #17 六壬占时语义对齐、#18 农历日期合法性、#19 API 参数透传、#20 测试限流耦合）

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
| 17 | （原二档#2）六壬占卜时刻未对齐 `resolve_divination_datetime` | `liuren_engine` 自行 `_parse_datetime_string` 绕过 `calendar_utils`，造成**两个静默错误**：①`calendar="lunar"` 被静默忽略 → 按公历起课（实测农历 1990-04-07 日柱得 `壬寅`，应为 `丙寅`）；②`true_solar_time` 被静默忽略 → 占时不校正，且 `input_echo` 标 `true_solar_time_applied=true` 却回显未校正值（**回显撒谎**）。修复：占时解析改走 `cu.resolve_divination_datetime`，与奇门/六爻同语义。实测经度 91.5E 占时由巳时正确退到辰时；农历路径与 `BaziEngine` 四柱逐字一致。新增 4 测试；六壬黄金用例逐字不变 |
| 18 | 非法农历日期被静默回卷 + 合法农历三十被误拒（排查 #17 时发现，影响**全部** `calendar="lunar"` 输入、三引擎共用路径） | ①`sxtwl.fromLunar` 对不存在的农历日**不报错而是回卷**：实测 `fromLunar(1990, 4, 30)`（该年四月仅 29 天）返回公历 `1990-05-24` 并自称农历 `5/1` —— 用户输入的日期被悄悄换成另一天。②反向缺陷：农历分支复用公历 `datetime` 构造，而合法农历日可能是公历不存在的日期（农历二月三十 `1981-02-30`，公历无 2 月 30 日），此前直接抛 `ValueError` 崩溃。修复：`lunar_to_solar` 加**往返校验**（`fromLunar` 结果再读回农历月/日/闰月比对；已在 1900-2100 共 144,720 个组合验证合法日期含闰月全部往返一致、非法日期全部识别）后抛 `EngineError`；农历字符串解析独立为 `_parse_lunar_datetime_string`，不再经公历 `datetime` 构造。保留农历时间可省略（缺省 12:00）行为 |
| 19 | `/api/engine/{system}` 不暴露真太阳时/闰月参数（端到端复验发现） | `BirthInput`（`/api/chart`）有 `true_solar_time`/`longitude`，但 `EngineQueryRequest` 缺这两个字段且 `query_engine` 未透传 —— 引擎侧已支持而 API 层**不可达**，用户传了也静默无效（与 chart 端点语义不一致）。修复：补 `true_solar_time` / `longitude` / `lunar_is_leap` 字段并透传 |
| 20 | 测试间共享限流配额导致隐式耦合 | `default_limiter` 是进程级单例（10 次/60 秒），`tests/api/test_api.py` 各用例共享同一配额：新增用例挤占配额会让**无关用例**意外收到 429（本次新增 4 个用例即触发）。修复：该文件加 `autouse` fixture 每例前后复位限流器（**未修改产品阈值**） |
| 21 | 编排层丢弃流派 / 校正参数 + `birth_input.birth_datetime` 字符串整体失效（审计同类"静默忽略"缺陷时发现） | ①`_extract_birth_params` 的 `birth_input` 白名单只有 9 个键、`router.build_input` 只产 4 键，导致 `true_solar_time`/`longitude`/`lunar_is_leap`/`bazi_subhour_rule`/`school` **全部被静默丢弃**——实测传 `early_zi` 仍按 `midnight` 起盘、传 `sanhe` 仍按中州派。②设计稿 §3.1 允许 `birth_input` 直接给 `birth_datetime` 字符串，但该写法**整体静默失效**（`build_input` 只认 year/month/day 分量，报"缺少出生日期参数"→ 引擎零调用）。修复：`build_input` 增可选键透传（缺省不写，保持既有 4 键行为与引擎默认值）；编排层白名单补齐 + `user_context` 顶层平铺兼容 + `birth_datetime` 字符串拆分（显式分量优先）；并支持自然语言明确措辞（"用真太阳时，经度91.5度"/"用早子时换日"/"按三合派"）。**防误判**：只认参数化措辞，裸词不认——实测"有没有三合局""想了解飞星是什么""真太阳时是什么"均不再误触发 |

## 一.5、端到端验收（2026-08-29 首次真实 API 冒烟，Windows 本机）

- 环境：uvicorn 127.0.0.1:8000，默认开发密钥（自用定位下可接受）。
- 自验矩阵：health ✓ / chart 200（八字四柱+紫微 12 宫含亮度）/ orchestrate 200（双引擎+3 引用跨 classics/rules/cases 三类+免责声明+8 span trace 可回溯）/ engine·liuren 200（月将巳=处暑，占时生效）/ engine·tieban 200（考刻二刻0分，命中 150 条真实条文）/ engine·qimen 200 / 错误密钥 401 ✓ / 服务日志零 ERROR。
- pythonmonkey 线程崩溃史确认已规避：编排层 ziwei 走 `ZiWeiProcessEngine` 进程代理（`ai_orchestrator.py` ENGINES 表），API 线程池实测无崩溃。
- **用户终验进行中**（验收方式已定：用户亲自判定）；跨库交叉验证（术数正确性裁判）为后续独立工作项。

## 二、可解决待做（技术无障碍，按价值排序）

1. **Docker 镜像内编译 ZhouYiLab CLI**（多阶段构建，builder 用 Linux LLVM 镜像）；工程量大，CI 已验证 Linux 可编，配方现成。**自用定位下降为低优先**（本机无 Docker 无法验证，需配 CI docker-build job 才算闭环）。
2. **提到"风水/太乙神数"会让整个编排静默空转**（2026-09-13 审计时发现，**既有行为**，非本批引入）：`XuanXueRouter.route` 按关键词打分，句中只要出现"风水"就把 `method` 判为风水；而风水/太乙在 `_ENGINE_LOCATIONS` 中模块为 `None`（无引擎），于是 `systems_invoked=[]`，用户拿到的是**只有免责声明和参考条文、没有任何命盘内容**的回答，且无降级提示。对照：同样问句不提"风水"则 `method=unknown`、行为一致但同样无引擎。**待决策**：路由命中无引擎术数时应回落到 `unknown`（附澄清提示），还是给出显式"该术数未接入"降级 —— 两种都会改变既有路由行为，需先定语义。
2. **非法农历日期被静默回卷**（2026-09-13 排查六壬占时时发现，影响**全部** `calendar="lunar"` 输入）：`sxtwl.fromLunar` 对不存在的农历日**不报错而是回卷**——如 `fromLunar(1990, 4, 30)`（该年四月仅 29 天）返回公历 `1990-05-24` 并自称农历 `5/1`，即用户输入的日期被静默换成另一天。八字/紫微/六壬三引擎共用 `calendar_utils` 解析路径，故均受影响。**修法已验证可行**：`lunar_to_solar` 内加往返校验（`fromLunar` 结果再 `getLunarMonth/Day/isLunarLeap` 比对，合法日期含闰月全部往返一致，非法日期 mismatch）后抛 `EngineError`。**待决策**：改动落在共享历法层（被三引擎依赖），且 `calendar_utils` 属"排盘计算内核"范畴，需用户确认后再做。

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
