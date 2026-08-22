# xuanxue-ai 交接总结（2026-08-22 更新）

> 接手人：下一台机器 / 下一位协作者
> 当前所在机器：Mac Intel x86_64（用户在 P 盘 `/Volumes/mac p/xuanxue-ai` 工作中）
> 仓库源：`https://github.com/lu422407/xuanxue-ai`（分支 `master`）
> ZhouYiLab 使用 fork：`https://github.com/lu422407/ZhouYiLab`（上游为 banderzhm/ZhouYiLab）

---

## 0. 一句话结论

六个引擎（八字/紫微/六壬/铁板/奇门/六爻）**全部接入完毕并可运行**；编排层 Phase A–F 已完成（五行交叉印证、RAG 引用溯源、全链路 trace）；黄金测试覆盖 6/6 引擎，全量 pytest **202 个测试全绿**，覆盖率 **84.7%**（红线 >80%，CI 双 job 强制执行：纯 Python + Linux 编译 C++ 真跑奇门/六爻）。剩余工作见 `docs/COMPROMISES.md` 二/三/四档（真实条文库需素材、数据安全红线需决策、validator 亮度校验等）。

---

## 1. 奇门/六爻链路的正确认知（2026-08-22 勘误）

旧版文档在此处有系统性误导，接手人请以本节为准：

1. **Python 引擎早已接入**（提交 `ea982d5`）：`engines/qimen_engine.py` / `liuyao_engine.py` 通过 `engines/zhouyi_bridge.py` 子进程调用 C++ CLI，不存在 NotImplementedError 门控。
2. **需要的二进制是 `example_zhouyi_cli`**，不是 `example_qi_men` / `example_liu_yao`（后两者是无参数演示程序，输出中文表格文本，与 Python 链路无关）。
3. CLI 用法：`example_zhouyi_cli qi_men <年 月 日 时 分>` 和 `liu_yao <六位0/1卦码> <年 月 日 时 分> [动爻...]`，输出 JSON（`{ok, system, pan, ...}`）。
4. bridge 探测路径（`engines/zhouyi_bridge.py`）：环境变量 `ZHOUYILAB_CLI` → `third_party/ZhouYiLab/build/examples/` → `build_llvm/examples/` → 仓库根 `bin/`。
5. fork 修复记录：`example_zhouyi_cli.cpp` 曾缺 `import ZhouYi.BaZiBase;`（LiuYaoController 对 BaZiBase 是非导出式 import，clang 严格拒绝），修复提交 `c528744`。

---

## 2. 路径与文件清单

| 路径 | 用途 |
|------|------|
| `/Volumes/mac p/xuanxue-ai/` | 工作根目录（Mac P 盘） |
| `/Volumes/mac p/xuanxue-ai/.venv/` | Python 3.11 venv（依赖装齐） |
| `/Volumes/mac p/xuanxue-ai/third_party/` | 8 个 submodule |
| `third_party/ZhouYiLab/build_llvm/examples/example_zhouyi_cli` | 奇门/六爻桥接 CLI（已编译验证） |
| `AUDIT_AND_FIX_REPORT.md` | 2026-08-21 审计报告（末尾附 08-22 勘误） |
| `ZHOUEYILAB_COMPILE_RESULT.md` | ZhouYiLab 编译技术笔记（早期 GCC 路线失败记录） |
| `HANDOVER.md` | 本文件 |

---

## 3. 环境复现步骤（新机器上重建用）

### 3.1 macOS Intel（已验证）

```bash
# 1. 克隆
git clone https://github.com/lu422407/xuanxue-ai.git
cd xuanxue-ai
git submodule update --init --recursive

# 2. Python 依赖
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install git+https://github.com/wlhyl/ganzhiwuxinForPython.git
.venv/bin/pip install astropy
# pythonmonkey==1.1.0、py-iztro==0.1.5、sxtwl==2.0.7、eacal 等均有预编译 wheel

# 3. C++ 工具链 + 编译（也可直接跑 scripts/setup_submodules.sh，已含本步骤）
brew install cmake ninja llvm
cd third_party/ZhouYiLab
CC=/usr/local/opt/llvm/bin/clang \
CXX=/usr/local/opt/llvm/bin/clang++ \
cmake -B build_llvm -G Ninja \
  -DCMAKE_CXX_COMPILER=/usr/local/opt/llvm/bin/clang++ \
  -DCMAKE_C_COMPILER=/usr/local/opt/llvm/bin/clang \
  -DBUILD_EXAMPLES=ON \
  -DZHOUYILAB_MODULE_MODE=LOCAL \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build_llvm --target example_zhouyi_cli   # 只需这一个目标

# 4. 测试
cd ../..
.venv/bin/pytest -q                    # 期望 202 passed（未编译 CLI 时 qimen/liuyao 相关用例自动 skip）
.venv/bin/pytest --cov --cov-fail-under=80   # 覆盖率红线（CI 同款命令）
```

### 3.2 Windows（用户原开发机）

参照 `docs/ZHOUEYILAB_BUILD_GUIDE.md`，注意编译目录用默认 `build/`（bridge 也会探测该路径）。

### 3.3 macOS Apple Silicon（未验证）

`scripts/setup_submodules.sh` 已自动探测 `/opt/homebrew/opt/llvm`。pythonmonkey 在 arm64 上编译风险较高，需先验证紫微链路。

---

## 4. 关键发现（避免接手人重复踩坑）

### 4.1 ZhouYiLab 编译只能走 libc++/Clang 路线
- GCC 14（libstdc++ 无 std 模块）、Apple Clang（不支持 C++23 模块依赖图发现）均失败
- **成功路线：Homebrew LLVM clang++ + libc++ + `ZHOUYILAB_MODULE_MODE=LOCAL`**
- 另外：MSVC 对模块传递可见性较宽松——曾在 Windows 编译通过、在 clang 下失败的代码是真实风险（`example_zhouyi_cli.cpp` 的 BaZi import 即此案例）

### 4.2 pythonmonkey 是紫微引擎的关键依赖
- 紫微走子进程代理（`engines/ziwei_process.py` → `ziwei_worker.py`），规避 pythonmonkey 在非主线程的崩溃
- Intel Mac 有预编译 wheel；Apple Silicon 经常编译失败，需备选方案

### 4.3 测试与引擎契约
- 真实紫微引擎 `major_stars` 输出**字符串列表**；`src/validator.py` 已做 isinstance 兼容
- 注意：字符串契约下亮度默认"平"，`validate_ziwei` 的庙/陷检查实际不触发——真正生效需引擎输出亮度或改为查表校验（待办）
- 奇门/六爻 API 测试带 `skipif`：无 CLI 时自动 skip，不会假失败

### 4.4 引擎链路当前可运行状态（全部实测通过）

| 引擎 | 文件 | 状态 |
|------|------|------|
| 八字 | `engines/bazi_engine.py` | ✅ 黄金测试 12 例 |
| 紫微 | `engines/ziwei_engine.py`（子进程代理） | ✅ 黄金测试 10 例 |
| 六壬 | `engines/liuren_engine.py` | ✅（需 astropy） |
| 铁板 | `engines/tieban_engine.py` | ✅ 骨架可用 |
| 奇门 | `engines/qimen_engine.py` → zhouyi_bridge → CLI | ✅ 2026-08-22 打通 |
| 六爻 | `engines/liuyao_engine.py` → zhouyi_bridge → CLI | ✅ 2026-08-22 打通 |

---

## 5. 接手人下一步行动（按优先级）

### 🟢 优先级 1：Phase C 真实条文扩充
`knowledge/tieban/tiaowen/` 仍是占位样本。**2026-08-22 决定：占位条文的 `verified:true` 翻转已 revert**——占位数据不得标记为"已验证传统文献"，扩充时须逐条核对真实流传本并补 `source`。**此步需要真实素材输入，不得由 AI 编造条文内容。**

### 🟢 优先级 2：validator 强化
- `validate_ziwei` 亮度校验在字符串契约下空转（见 §4.3）
- `validate_liuren` 仍是骨架（四课三传规则未实现）

### 🟢 优先级 3：LLM 真实接入 + 用户成长助手
`llm/` 四个 provider 壳齐备但生产入口用 RuleBasedLLM；README 定位的"用户成长助手"仅有 memory 骨架。

### 🟢 优先级 4：其他待办
- Docker 镜像未包含 ZhouYiLab CLI，奇门/六爻在容器内不可用（其余功能正常）
- `src/router.py` `_extract_params` 的 hour 提取顺序问题（审计报告遗留，低风险）

### 已完成（2026-08-22 第三批，详见 docs/COMPROMISES.md）
- ✅ 黄金测试补齐 6/6 引擎（qimen/liuyao/liuren/tieban 各有用例；奇门与 demo 输出交叉验证；Linux/macOS 跨平台一致已由 CI 证实）
- ✅ Critic 防幻觉扩展至奇门（九星/八门/八神）、六爻（爻位-六神/六亲爻/纳甲）、六壬（月将）
- ✅ Phase F 真接线：编排 8 阶段 span + cost_tracker；LLM/抽参/意图分类降级全部有日志；默认 API key 启动告警
- ✅ validator 六壬结构校验 + 亮度表完整性自检
- ✅ 测试基线 186 → **202**，覆盖率 83% → **84.7%**

### 已完成（2026-08-22 第二批）
- ✅ Phase B：八字日主↔紫微命宫五行生克交叉印证（`cross_validate_bazi_ziwei` 纯函数 + 单测）
- ✅ Phase E：RAG 溯源接入编排层（`synthesis.citations` 填充可校验的 `[source:id]` 引用，附于答案）
- ✅ coverage 工具（`.coveragerc` + pytest-cov）与 GitHub Actions CI（`.github/workflows/ci.yml`，覆盖率红线 80%）
- ✅ CI 双 job：`cpp-cli` 在 Linux（clang-20 + libc++）编译 ZhouYiLab 并真实执行奇门/六爻链路（186 测试 0 skip；job 内置"出现 skip 即失败"保险）。ZhouYiLab 的 CMake 已内置 Linux libc++ 路径探测（`cmake/DetectStdLibModulePaths.cmake`），Linux 编译开箱即用

---

## 6. 项目核心约束（任何修改必须遵守）

1. **不删除/削弱任何现有测试**（当前 202 测试基线不可退化）
2. **LLM 不负责计算**（只在 Explain 阶段使用，所有排盘由 `engines/*` 确定性完成）
3. **不引入不可追踪的大型依赖**（仅用已锁定的 requirements.txt + submodule）
4. **不修改 tieban_engine 核心算法**（条文库是数据驱动，与算法解耦）
5. **占位/示例数据不得标记 `verified:true`**（数据血统必须真实）
6. **引擎不可用时必须优雅降级**（skip/skipped 记录 + setup_hint，而非静默错误）

---

## 7. 参考文档

- `README.md`：产品定位与原则
- `PROJECT_NEXT_PHASE_REPORT.md`：原作者的下一阶段报告
- `COMPLETION_SUMMARY_ultimate_integration.md`：v1.0 集成里程碑总结
- `docs/AI_ORCHESTRATOR_DESIGN.md`：AI Orchestrator 架构设计稿（Phase A-F 路线）
- `docs/ZHOUEYILAB_BUILD_GUIDE.md`：奇门/六爻编译与接入指南
