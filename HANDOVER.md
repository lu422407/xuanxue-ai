# xuanxue-ai 交接总结（2026-08-22 · Windows 接手版）

> 接手场景：从 Mac（P 盘）切回 **Windows** 继续开发（原项目本就始于 Windows 开发机）
> 仓库源：`https://github.com/lu422407/xuanxue-ai`（分支 `master`，以下所有工作**已全部推送**，当前 HEAD `e8598b7`）
> ZhouYiLab 使用 fork：`https://github.com/lu422407/ZhouYiLab`（上游 banderzhm/ZhouYiLab；模块可见性修复 `c528744` 已推送）

---

## 0. 一句话结论

**六个引擎全部打通、Phase A–F 编排层完成、12,000 条真实铁板条文已入库、CI 双 job（含 Linux 编译 C++）全绿**。测试基线 **12,202**（未编译 CLI 时 12,192 passed + 10 skipped），覆盖率 **84.7%**（红线 >80% 由 CI 强制）。Windows 上要做的只有：装环境 → 编译 ZhouYiLab CLI → 跑测试确认 → 从 `docs/COMPROMISES.md` 二/三档里挑下一件事。

---

## 1. Windows 快速开始（按顺序）

### 1.1 克隆与依赖

```powershell
# 建议：路径不要含空格/中文（如 C:\dev\xuanxue-ai）
git clone https://github.com/lu422407/xuanxue-ai.git
cd xuanxue-ai
git submodule update --init        # 8 个子模块；ZhouYiLab 的 C++ 依赖已 vendor，无需 recursive

python -m venv .venv               # Python 3.11
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install git+https://github.com/wlhyl/ganzhiwuxinForPython.git
.venv\Scripts\pip install astropy
# 关键依赖 Windows 兼容性均已确认：pythonmonkey/sxtwl/py-iztro/eacal 有 win_amd64 wheel 或纯 Python
```

### 1.2 编译 ZhouYiLab CLI（奇门/六爻依赖，唯一需要 C++ 的一步）

只需要一个目标：**`example_zhouyi_cli`**（`example_qi_men`/`example_liu_yao` 是无参数演示程序，与 Python 链路无关，别编错目标）。

```powershell
# 路线 A：已装 VS2022 17.10+ —— 在 "Developer Command Prompt for VS 2022" 里：
cmake -B build -DBUILD_EXAMPLES=ON -DZHOUYILAB_MODULE_MODE=LOCAL
cmake --build build --target example_zhouyi_cli --config Release
# 产物：build\examples\example_zhouyi_cli.exe —— 这正是 zhouyi_bridge 的第一探测路径，自动发现，无需环境变量

# 路线 B：MSYS2 + Clang 18+/GCC 14+（见 docs/ZHOUEYILAB_BUILD_GUIDE.md §2）
```

注意事项：
- CMake ≥ 3.30（VS 自带的偏旧，从 cmake.org 装新的）；依赖已 vendor 在 `3rdparty/`，**不需要**初始化嵌套子模块（BUILD_GUIDE §0 状态表是旧信息，以本文件为准）
- fork 里的 `import ZhouYi.BaZiBase;` 修复（`c528744`）已解决"MSVC 能编、clang 报错"的模块可见性问题，两条路线现在都应可用
- 验证：`.venv\Scripts\python -c "from engines import zhouyi_bridge; print(zhouyi_bridge.cli_available())"` 应输出 `True`

### 1.3 测试与运行

```powershell
.venv\Scripts\pytest -q                # 期望 12,202 全绿（未编 CLI 时 12,192 passed + 10 skipped，属正常）
.venv\Scripts\pytest --cov --cov-fail-under=80    # 覆盖率红线（CI 同款）
.venv\Scripts\uvicorn api.main:app     # API（默认开发密钥 dev-key-0001，会打告警日志）
```

中文输出乱码时：`chcp 65001` 或设 `PYTHONIOENCODING=utf-8`。

### 1.4 补记（2026-08-23 Windows 接手实际执行）

- **环境**：本机无 VS/MSYS2，实际走 **路线 C：WinLibs GCC 16.1**（winget `BrechtSanders.WinLibs.POSIX.UCRT`，自带 cmake 4.4 / ninja / gcc 16.1，无需另装）；Python 3.11.9 经 winget 安装（3.12 无 sxtwl==2.0.7 wheel，勿用）。
- **配置命令**（注意必须带 experimental UUID，否则 CMake 不给 GCC 开 `import std`）：
  ```powershell
  cmake -B build -G Ninja -DCMAKE_CXX_COMPILER=g++ -DBUILD_EXAMPLES=ON -DZHOUYILAB_MODULE_MODE=LOCAL `
        -DCMAKE_CXX_MODULE_STD=ON `
        -DCMAKE_EXPERIMENTAL_CXX_IMPORT_STD=f35a9ac6-8463-4d38-8eec-5d6008153e7d
  cmake --build build --target example_zhouyi_cli
  ```
- **fork 新增 3 处构建修复**（`lu422407/ZhouYiLab`，基于 c528744，**尚未推送，本地工作树**）：①`3rdparty/magic_enum/module/magic_enum.cppm` GCC 下强制 header 模式（import std + purview 文本包含 mingw CRT 头会声明冲突）并补 `<format>`；②`CMakeLists.txt` GNU+WIN32 链接 `stdc++exp`（WinLibs 把 `__write_to_terminal` 等放这库）；③同处 `-static` 全静态（免疫系统里 Git-Bash mingw64 的旧 libstdc++-6.dll 抢载）+ `--allow-multiple-definition`（COFF 无 section group，std 模块内联局部静态每 TU 强定义，同一 BMI 实体取首即可）。**下次接手：先把这两处 fork 改动 commit/push 到 `lu422407/ZhouYiLab`，再更新主仓 submodule 指针。**
- 验证结果：`cli_available()=True`，全量 **12,211 passed 0 skipped**（+9 新用例：critic 补 tieban×7、RAG 类别交错×2），覆盖率 **85.3%**（红线 80%）。

---

## 2. 当前项目状态（截至 2026-08-22）

| 模块 | 状态 |
|------|------|
| 六引擎（八字/紫微/六壬/铁板/奇门/六爻） | ✅ 全部可运行 |
| 黄金测试 | ✅ **6/6 引擎**（bazi×12、ziwei×10、qimen×2、liuyao×2、liuren×1、tieban×1；跨平台确定性已验证） |
| AI Orchestrator Phase A–F | ✅ 含五行交叉印证（B）、RAG 引用溯源（E）、全链路 span/cost（F） |
| Critic 防幻觉 | ✅ 覆盖 6 系统（紫微宫位星曜/八字干支/奇门九星八门八神/六爻爻位六神六亲纳甲/六壬月将） |
| 铁板真实条文 | ✅ 12,000 条（清代公版，溯源链见 `knowledge/tieban/tiaowen/SOURCES.md`，**CC BY-NC 4.0 禁商用**） |
| CI | ✅ 双 job：`test`（覆盖率红线 80%）+ `cpp-cli`（Linux clang-20 编译 C++ 真跑奇门/六爻，出现 skip 即失败） |
| 测试/覆盖率 | 12,202 / 84.7% |

---

## 3. 关键认知（避免重复踩坑）

1. **奇门/六爻链路**：Python 引擎（`engines/qimen_engine.py` 等）→ `engines/zhouyi_bridge.py` 子进程调用 `example_zhouyi_cli`（JSON 子命令 CLI）。bridge 探测顺序：环境变量 `ZHOUYILAB_CLI` → `build/examples/` → `build_llvm/examples/` → `bin/`。
2. **铁板条文的三个诚实标注**：①正文真实（verified:true）但转录未校勘（confidence:中）；②(ke,fen) 刻分是**本项目自建索引**（`idx=条文号-1001; ke=idx%8; fen=(idx//8)%10`），非传统考刻取数；③**许可禁止商用**。
3. **确定性教训**：任何"按文件遍历"的加载必须 `sorted()`（APFS/ext4/NTFS 顺序各异，tieban 黄金用例踩过）；引擎输出必须跨平台逐字节一致（CI 已验证）。
4. **LLM 永不参与计算**；引擎不可用必须优雅降级（skip/skipped + setup_hint），禁止静默错误；占位数据禁止 `verified:true`。
5. 所有已知妥协与待办**登记在 `docs/COMPROMISES.md`**（四档：已解决/可解决待做/需决策/受约束），别靠记忆。

---

## 4. 下一步（从 `docs/COMPROMISES.md` 摘要）

**需要你决策的三件**：数据安全红线落地方式（做实加密存储 vs README 降级承诺，当前 database/ 是死代码）；限流/tracing 多副本共享（是否引入 Redis）；LLM 生产接入选型。

**技术无障碍待做**：紫微亮度校验生效（py-iztro 有 brightness 字段，引擎现丢弃）；Critic 补铁板（真实条文已入库，素材不再是阻塞）；RAG 首条偏置缓解；Docker 镜像内编译 CLI（Linux 配方 CI 已验证）；真实考刻取数接入（取数表 15 张已在上游 tbss-ts-lib 备齐，需决策是否动引擎）。

---

## 5. 项目核心约束（任何修改必须遵守）

1. **不删除/削弱任何现有测试**（12,202 基线不可退化）
2. **LLM 不负责计算**（只在 Explain 阶段，排盘全部由 `engines/*` 确定性完成）
3. **不引入不可追踪的大型依赖**（仅锁定版 requirements.txt + submodule）
4. **不修改 tieban_engine 考刻核心算法**（数据层驱动；`sorted(glob)` 是加载顺序确定性修复，非算法变更）
5. **占位/示例数据不得标记 `verified:true`**；真实数据的许可与溯源必须随数据保存（见 SOURCES.md）
6. **引擎不可用时必须优雅降级**，且降级要有日志
7. **README 红线与实现不允许长期分叉**（见 COMPROMISES.md 维护约定）

---

## 6. 参考文档

- `docs/COMPROMISES.md`：妥协清单（最重要的下一件事来源）
- `knowledge/tieban/tiaowen/SOURCES.md`：真实条文溯源与许可
- `docs/ZHOUEYILAB_BUILD_GUIDE.md`：ZhouYiLab 编译细节（§0 状态表已过时，编译路线仍有效）
- `docs/AI_ORCHESTRATOR_DESIGN.md`：编排层设计（Phase A–F）
- `README.md`：产品定位与原则 · `AUDIT_AND_FIX_REPORT.md`：早期审计（附勘误）
