# Current State

## Goal

自用研究向的术数 AI 平台：确定性排盘 + AI 编排，把排盘结果解释清楚。
**不对外提供服务**（2026-08-29 决策）。

## Status

API 端到端验收冒烟已通过（2026-08-29，Windows 本机 uvicorn）：
health / chart / orchestrate / liuren / tieban / qimen 六个端点全 200，错误密钥 401 正常，
服务日志零 ERROR。铁板命中 150 条真实条文。

**本机已追平远端**（2026-09-13）：`git pull` 完成，HEAD = `4cfe61f`（快进 33 个提交，
非旧记录所称 5 个），子模块 `third_party/ZhouYiLab` 对齐 `91b03fe`，CLI 二进制在位。
全量测试 **12240 passed / 0 failed / 0 skipped**。

六壬占时语义已对齐 `resolve_divination_datetime`（原二档 #2 → COMPROMISES 一档 #17）：
修复 `calendar="lunar"` 与 `true_solar_time` 两个**静默忽略**缺陷，
六壬黄金用例逐字不变。

**等待用户亲自终验排盘正确性** —— 自动化只能证明接口通，不能证明排得对。

## Blockers

无。（原"本机副本落后远端"已解除。）

## Next

1. 用户终验排盘正确性（进行中，方式：用户亲自判定）
2. **待决策**：非法农历日期静默回卷修复 —— 影响全部 `calendar="lunar"` 输入，
   八字/紫微/六壬三引擎共用路径；`sxtwl.fromLunar(1990,4,30)` 不报错而是回卷成公历
   `1990-05-24`（自称农历 5/1）。修法与影响面见 `docs/COMPROMISES.md` 二档 #2
3. （后续）术数正确性的跨库交叉验证 —— 裁判方式已定，尚未开始

## Updated

2026-09-13
