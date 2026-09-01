# 阶段10：Temporal工作流与人工交易E2E

## 目标

实现`workflow-orchestration-service`，把已验收服务和Agent组装成可恢复的低频人工决策闭环。

领域基线见[工作流设计](../../architecture/services/workflow-orchestration-service.md)。

## 顺序

1. [Temporal骨架和Activity](./01-temporal-activities.md)。
2. [领域工作流](./02-domain-workflows.md)。
3. [人工审批、成交和完整E2E](./03-manual-e2e.md)。
4. [可靠性、运维和发布](./04-reliability-operations.md)。
5. [日频与盘中组合调仓联合回放](./05-joint-rebalance-replay.md)。
6. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 边界

Temporal管理时间、顺序、重试和人工等待，不拥有领域事实；Workflow代码不得直接访问数据库、NATS、HTTP SDK、模型、随机数或系统当前时间。

组合调仓批次遵循[ADR-010](../../architecture/adr/ADR-010-rebalance-batch-and-daily-limit.md)。本阶段完成每日0～2批人工闭环和联合历史回放，但不启用自动交易。
