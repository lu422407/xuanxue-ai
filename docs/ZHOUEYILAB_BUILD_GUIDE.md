# ZhouYiLab 编译与接入指南（奇门遁甲 / 六爻）

> 版本：v0.1.0（准备 + 接入规划，**本阶段不安装任何环境、不执行编译**）
> 日期：2026-08-19
> 对象：`third_party/ZhouYiLab`（C++23 Modules 多术数算法库）
> 目标：说明当前缺什么、Windows 如何准备、编译后如何接入 `engines/qimen_engine.py` / `liuyao_engine.py`

---

## 0. 当前状态（已确认）

| 项目 | 状态 |
|------|------|
| `third_party/ZhouYiLab` 子模块 | ✅ 已克隆，锁定提交 `1e53b2c` |
| C++ 工具链（CMake / g++ / cl） | ❌ 本机未安装（见 §1） |
| ZhouYiLab 嵌套子模块（fmt / nlohmann_json / magic_enum / tyme4cpp） | ❌ 尚未初始化（`3rdparty/*` 为空目录） |
| `engines/qimen_engine.py` / `liuyao_engine.py` | ⚠️ 显式 `NotImplementedError` + 编译指引（按项目「禁止静默错误」原则） |
| `build/` 目录 | ❌ 不存在（尚未编译） |

> 设计约束：在 C++ 工具链就绪前，`qimen`/`liuyao` **必须**保持 `NotImplementedError`，
> 由 AI Orchestrator（见 `docs/AI_ORCHESTRATOR_DESIGN.md` §3.2 `systems_skipped`）优雅降级，
> **绝不能**改成假实现。

---

## 1. 当前缺失清单（Checklist）

- [ ] **CMake ≥ 3.30**（最小 3.28；推荐 4.1.2+，C++ modules 的 `import std` 更稳定）
- [ ] **支持 C++23 modules 的编译器** 之一：
  - [ ] MSVC 2022 **17.10+**（标准库模块为「实验性」）
  - [ ] GCC **14+**
  - [ ] Clang **18+**
- [ ] **ZhouYiLab 嵌套子模块**初始化（fmt / nlohmann_json / magic_enum / tyme4cpp）
- [ ] （可选）vcpkg —— 仅当走 `cmake/curt_vcpkg.cmake` / `cmake/vs.toolchain.cmake` 路线时需要；主路径用 `add_subdirectory(3rdparty/*)`，不强制 vcpkg
- [ ] （Windows）网络库 `ws2_32` / `mswsock` —— 由 CMake 自动链接，无需手动处理

**先决条件自检命令**（在准备环境后运行）：
```powershell
cmake --version          # 期望 >= 3.30
gcc --version            # 或 clang --version / cl（MSVC）
```

---

## 2. Windows 环境准备（三条路线）

> ZhouYiLab 使用 **C++23 Modules（`import std;`）**，对编译器要求高。
> MSVC 的标准库模块支持仍属「实验性」，GCC/Clang 对 modules 支持更干净。
> **推荐路线 B（MSYS2 + GCC/Clang）** 用于实际编译；路线 A（MSVC）适合已装 VS2022 17.10+ 的环境。

### 路线 A：MSVC 2022 17.10+（已装 Visual Studio 场景）

1. 安装/升级 **Visual Studio 2022 ≥ 17.10**（勾选「使用 C++ 的桌面开发」）。
2. 单独安装 **CMake ≥ 3.30**（VS 自带 CMake 通常较旧，建议从 cmake.org 装最新并加入 PATH）。
3. 打开 **"Developer Command Prompt for VS 2022"**（确保 `cl` / `cmake` 在 PATH）。
4. 注意：CMakeLists 已自动加 `/utf-8` 与 `/EHsc`，无需手动设置。

### 路线 B（推荐）：MSYS2 + GCC 14+ / Clang 18+

```bash
# 1. 安装 MSYS2（https://www.msys2.org），然后打开 "MSYS2 MINGW64" 终端
pacman -Syu
# GCC 路线
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-make
# 或 Clang 路线（对 C++20/23 modules 更友好）
pacman -S mingw-w64-x86_64-clang mingw-w64-x86_64-cmake mingw-w64-x86_64-make
```

### 路线 C：LLVM/Clang（独立安装）

- 从 https://github.com/llvm/llvm-project/releases 安装 LLVM ≥ 18，确保 `clang++` / `clang` / `lld` 在 PATH。
- 配合 Ninja：`pacman -S mingw-w64-x86_64-ninja` 或独立安装 Ninja。

---

## 3. 编译步骤

> ⚠️ 仅记录步骤，**本阶段不执行**。环境就绪后在 `xuanxue-ai` 仓库根目录操作。

### 3.1 初始化 ZhouYiLab 嵌套子模块（必须，否则 `add_subdirectory(3rdparty/*)` 失败）

```bash
cd third_party/ZhouYiLab
git submodule update --init --recursive
# 校验：以下目录应非空
ls 3rdparty/fmt 3rdparty/nlohmann_json 3rdparty/magic_enum 3rdparty/tyme4cpp
```

### 3.2 配置（CMake）

```bash
cd third_party/ZhouYiLab
# 推荐 Ninja + GCC/Clang（modules 编译更快、更稳）
cmake -B build -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DBUILD_EXAMPLES=ON
# 若用 MSVC Developer Command Prompt：
# cmake -B build -DBUILD_EXAMPLES=ON
# 若 std 模块检测失败，可显式指定模块模式（见 §6）：
# cmake -B build -DBUILD_EXAMPLES=ON -DZHOUYILAB_MODULE_MODE=LOCAL
```

> `-DBUILD_EXAMPLES=ON` 才会构建 `example_qi_men` / `example_liu_yao` 等；
> 默认 `BUILD_EXAMPLES=OFF`（目标 `EXCLUDE_FROM_ALL`），需手动 `--target example_qi_men`。

### 3.3 编译（仅编译奇门/六爻示例，省时）

```bash
# 只编需要的示例
cmake --build build --target example_qi_men
cmake --build build --target example_liu_yao
# 或一次性全部示例
cmake --build build --target all_examples
```

### 3.4 验证二进制可用

```bash
./build/examples/example_qi_men --help      # 查看参数（若支持）
./build/examples/example_qi_men             # 直接运行，观察 stdout 输出格式
```

---

## 4. 编译产物位置

由 `examples/CMakeLists.txt` 决定：

```
third_party/ZhouYiLab/build/examples/
├── example_qi_men[.exe]      # 奇门遁甲
├── example_liu_yao[.exe]     # 六爻
├── example_ba_zi[.exe]
├── example_da_liu_ren[.exe]
└── example_zi_wei[.exe]
```

> 多配置生成器（MSVC）下可能为
> `build/examples/Release/example_qi_men.exe`，请以实际为准。
> 注意：旧版 `COMPLETION_SUMMARY_ultimate_integration.md` 写的是 `build/bin/*`，
> **实际 CMake 配置输出到 `build/examples/`**，以本指南为准。

### 输出格式（接入前必须确认）

示例基于 `nlohmann/json`，通常向 stdout 打印 **JSON**。接入前请**实际运行一次**二进制，
确认：
1. 命令行参数（`--help` 或阅读 `examples/example_qi_men.cpp` / `example_liu_yao.cpp`）；
2. stdout 是否为 JSON、字段命名（以便 Python 端 `json.loads` 解析）。

---

## 5. 编译后如何接入 xuanxue-ai

> 目标：把 `engines/qimen_engine.py` / `liuyao_engine.py` 的 `NotImplementedError`
> 替换为「调用本地二进制 + 解析 JSON」的真实实现。**不修改 `BaseEngine` 契约**，
> 不引入新的大型 Python 依赖。

### 5.1 接入方式（推荐：子进程调用，零新依赖）

```
engines/qimen_engine.py
  QiMenEngine.calculate(input_data)
    └─ subprocess.run([QI_MEN_BIN, <args from input_data>], capture_output=True)
       └─ json.loads(proc.stdout)  → 标准结构化命盘
```

- 二进制路径从环境变量读取，例如 `ZHOYILAB_BIN_DIR`
  （默认 `third_party/ZhouYiLab/build/examples`），**不硬编码绝对路径**。
- 参数映射：`input_data`（出生时间/性别/时区）转成二进制 CLI 参数。
- 失败处理：二进制不存在 / 非零退出 → 抛 `EngineError`（沿用「禁止静默错误」原则），
  并保留 `setup_hint` 供 AI Orchestrator 优雅降级。

### 5.2 需要的改动清单

| 文件 | 改动 |
|------|------|
| `engines/qimen_engine.py` | `NotImplementedError` → 子进程调用 `example_qi_men` + JSON 解析；保留 `setup_hint` 常量 |
| `engines/liuyao_engine.py` | 同上，调用 `example_liu_yao` |
| `src/router.py` | `_get_setup_hint` 中 qimen/liuyao 提示更新为「设置 `ZHOYILAB_BIN_DIR` 指向 build/examples」 |
| `scripts/setup_submodules.sh` | 增加「初始化 ZhouYiLab 嵌套子模块 + 可选编译示例」步骤 |
| `tests/engines/test_qimen_engine.py` / `test_liuyao_engine.py` | 新增：用 FakeLLM 思路做的**子进程桩测试**（mock 二进制输出，断言 JSON 解析与字段），不依赖真实编译 |

### 5.3 测试策略（满足「所有新增功能必须有测试」）

- **离线**：用 `unittest.mock subprocess.run` 返回预置 JSON，断言 `calculate()` 输出结构与 `EngineError` 分支。
- **真实（可选，CI 外）**：仅在 `ZHOYILAB_BIN_DIR` 指向有效二进制时运行端到端用例。
- **不可破坏现有 153 测试**：接入后原有 bazi/ziwei/liuren/tieban 测试不受影响；qimen/liuyao 由 `NotImplementedError` 变为真实实现，需在 `test_fusion_and_stubs.py` 中把二者从「未实现」分组移到「已实现」分组。

### 5.4 与 AI Orchestrator 的衔接

- 编译就绪 → `router.available_engines["奇门遁甲"/"六爻"]` 变为 `True`；
  AI Orchestrator 的 Selector 即可将其纳入 `systems_invoked`，并在 `systems_skipped` 中移除。
- 未编译 → 保持 `systems_skipped` + `setup_hint`，用户得到清晰指引而非报错。

---

## 6. 风险与约束

1. **C++23 modules 跨编译器兼容性**：MSVC 标准库模块为实验性，可能需
   `-DZHOUYILAB_MODULE_MODE=LOCAL`（CMake 选项，见 `CMakeLists.txt`）或在模块检测失败时回退。
   若 MSVC 编译反复失败，**改用路线 B（GCC/Clang）** 成本更低。
2. **多配置生成器路径**：MSVC 下产物可能在 `build/examples/Release/`，
   接入代码须用 `glob` 或环境变量兼容两种路径。
3. **Windows 网络库**：CMake 已自动链接 `ws2_32` / `mswsock`，一般无需手动处理；
   若报链接错误，确认未刻意剥离这些库。
4. **编码**：MSVC 自动 `/utf-8`；GCC/Clang 源文件为 UTF-8，无需额外处理。
5. **禁止假实现**：编译未完成前，qimen/liuyao **保持 `NotImplementedError`**；
   接入后若二进制缺失仍须抛 `EngineError`，不得返回编造命盘。
6. **依赖可追踪**：ZhouYiLab 及其 4 个嵌套子模块均为 git submodule（已锁定 URL/提交），
   不引入 PyPI 上的不可追踪大型依赖；Python 端仅用标准库 `subprocess` + `json`。
7. **勿动算法**：接入是「外壳调用」，不修改 ZhouYiLab C++ 源码与既有引擎核心算法。

---

## 7. 完成判定（接入后可勾选）

- [ ] `third_party/ZhouYiLab/build/examples/example_qi_men[.exe]` 与 `example_liu_yao[.exe]` 存在且可运行
- [ ] `engines/qimen_engine.py` / `liuyao_engine.py` 不再 `NotImplementedError`，返回标准结构化命盘
- [ ] `tests/engines/test_qimen_engine.py` / `test_liuyao_engine.py` 新增且通过（mock 子进程）
- [ ] 全量 pytest 仍 **≥153 passed**（无回归）
- [ ] `router.available_engines` 中奇门/六爻变为 `True`；AI Orchestrator `systems_skipped` 相应清空
