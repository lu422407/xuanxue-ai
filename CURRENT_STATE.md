# Current State

## Goal

自用研究向的术数 AI 平台：确定性排盘 + AI 编排，把排盘结果解释清楚。
**不对外提供服务**（2026-08-29 决策）。

## Status

**本机已追平远端**（2026-09-13）：`git pull` 完成，HEAD 基线 = `4cfe61f`（快进 33 个提交，
非旧记录所称 5 个），子模块 `third_party/ZhouYiLab` 对齐 `91b03fe`，CLI 二进制在位。

全量测试 **12256 passed / 0 failed / 0 skipped**。
API 端到端复验已通过（2026-09-13，Windows 本机 uvicorn:8078）：
health / chart / orchestrate / liuren / tieban / qimen / liuyao(缺卦码如实报错) 全部符合预期，
鉴权正确（无密钥/错误密钥 401），trace 8 span 可回溯，`/docs` 与 `/acceptance` 正常。
铁板命中 152 条真实条文。

本批次修复（详见 `docs/COMPROMISES.md` 一档 #17–#20）：

- **六壬占时**对齐 `resolve_divination_datetime`（原二档 #2 已解决）：修复
  `calendar="lunar"` 与 `true_solar_time` 两个**静默忽略**缺陷 + 回显撒谎；
  黄金用例逐字不变。经度 91.5E 实测占时由巳时正确退到辰时。
- **农历日期合法性**（排查上述问题时发现，影响全部 lunar 输入、三引擎共用路径）：
  ①非法农历日被 `sxtwl` **静默回卷**成另一天（如 1990-04-30 → 公历 05-24）；
  ②合法农历三十（如 1981-02-30，公历不存在该日）此前被**误拒崩溃**。
  两者均已修（往返校验；已在 144,720 个组合上验证）。
- `/api/engine/{system}` 补齐 `true_solar_time` / `longitude` / `lunar_is_leap` 透传
  （此前引擎支持但 API 不可达，用户传了静默无效）。

**等待用户亲自终验排盘正确性** —— 自动化只能证明接口通，不能证明排得对。

## Blockers

无。

## Next

1. 用户终验排盘正确性（进行中，方式：用户亲自判定）
2. （后续）术数正确性的跨库交叉验证 —— 裁判方式已定，尚未开始
3. 已知未修（非阻塞，待评估）：`liuren` 的日柱在 23:00–23:59 走**晚子时换日**
   （`dalurenpython` 上游行为），与八字默认的"子正换日"流派不一致；
   属上游流派差异，改动会影响六壬黄金用例，需单独决策

## Updated

2026-09-13
