# 阶段08：Agent、工作流、治理和硬风控总设计

## 目标

接通系统的核心决策链：六个Agent、Temporal工作流、风险复核、确定性硬风控和人工审批。

## 前置条件

- 阶段01～07的快照、事件和查询接口稳定。
- 完成模型路由、交易批次、风险复核和人工审批ADR。

## 开发边界

Agent只生成结构化判断；Temporal只编排；`decision-governance-service`拥有建议与审批状态，`portfolio-risk-service`拥有硬风控。任何一层失败都不得默认进入执行。

## 实施要求

- Agent与模型Provider解耦，输出必须通过Zod和证据校验。
- Workflow代码保持确定性，外部调用全部位于Activity。
- 风险复核与硬风控是两层不同能力，均不可跳过。
- HOLD合法；每个组合每天允许0～2个组合调仓批次，一次批次可包含多个证券Leg并由确定性规则执行。
- 六个Agent共用一个agent-service工程和镜像，但以六个容器、Durable Consumer和Task Queue独立部署。
- Agent评估和领域状态变化使用NATS + Outbox/Inbox传播，关键命令仍返回确定性结果。

## 顺序文档

1. [Agent Kernel和多模型网关](./01-agent-kernel-model-gateway.md)
2. [四个专业分析Agent](./02-professional-agents.md)
3. [主决策和风险复核Agent](./03-main-and-risk-review-agents.md)
4. [Temporal核心工作流](./04-temporal-workflows.md)
5. [决策治理、硬风控和人工审批](./05-governance-hard-risk-approval.md)

## 阶段验收

- 替换Provider不修改Agent业务定义。
- 所有结论可追溯证据和版本。
- 风险复核四种分支正确，修订循环有上限。
- 每日第3个组合调仓批次被硬规则拒绝，同批次多Leg和部分成交不重复计数。
- Worker重启后工作流继续，重复审批不产生重复指令。
- 任一Agent部署故障不拖垮其他Agent；重复事件不创建重复Proposal。
