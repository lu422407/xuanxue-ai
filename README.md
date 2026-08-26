# 术数 AI Engine Pro v3.2

术数领域 AI Agent 平台：术数计算系统 + 知识增强系统 + 智能推理 Agent + 用户成长助手。

支持：紫微斗数 / 八字 / 大六壬 / 奇门遁甲 / 六爻 / 铁板神数。

## 产品定位声明

> 本产品输出的所有分析结果均为传统术数文化的知识性推演，**不构成医疗、法律、财务或其他专业建议**，仅供文化研究与个人参考使用。用户不应据此做出重大人生决策。

## 核心设计原则

1. **计算与解释分离**：Engine 是确定性计算（无 LLM 参与），输出标准 JSON 命盘；AI 仅基于结构化数据做解释，禁止编造命盘要素；Validator 核对一致性。
2. **准确性优先于流畅度**：Engine 输出与黄金测试集不一致即视为阻断性缺陷（release blocker），宁可拒绝回答也不能输出错误命盘。
3. **数据安全**：出生时间、地点为强隐私字段。演示版不落盘、数据仅存内存；加密存储与入库脱敏为后续能力，当前未启用。

## 历法与时间处理

由 `engines/calendar_utils.py` 统一处理（各引擎禁止各自实现）：

- 公历 ↔ 农历转换：基于 `sxtwl`（寿星天文历），数据覆盖公元前 3000 年 ~ 公元 3000 年。
- 真太阳时校正：经度时差 + 均时差，是否启用由显式参数 `true_solar_time` 控制，默认关闭。
- 早晚子时：流派可配置项，默认采用"子时不分早晚"（子正换日）流派，可通过 `zi_wei_rule` / `bazi_subhour_rule` 配置。
- 闰月处理：八字按节气定月（无闰月概念）；农历月份标注重节点。

## 目录结构

见 v3.2 文档第 3 节，此处不重复。

## 测试要求

- 单元测试覆盖率 > 80%（必要非充分条件）
- `tests/golden/` 黄金测试集通过率 = 100%（合并硬性门槛）

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest tests/
.venv\Scripts\uvicorn api.main:app
```

## Docker

`docker/docker-compose.yml` 提供服务编排（api / postgres / redis / vector-db / llm-service），部署前需自行安装 Docker Engine。