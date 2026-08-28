# 阶段03：RD-Agent研究通道总设计

## 目标

建立独立Docker项目`research-automation-service`，封装自动因子/模型研究通道，让RD-Agent只能提出和初步验证候选产物。

## 开发边界

RD-Agent没有`quant-research-service`数据库写权限、券商密钥和生产模型密钥；它只产生PromotionRequest。候选必须由quant-research独立复验并经人工批准才能成为ACTIVE。

## 实施要求

- 候选代码只在限制资源的独立容器执行。
- 输入只读，产物按Hash不可变保存。
- 门禁阈值由生产配置拥有，不由RD-Agent决定。
- 任何状态变化记录操作人和理由。
- 服务拥有独立Dockerfile、Database/User、Outbox/Inbox、API和事件契约，可单独部署和停机。

## 顺序文档

1. [隔离沙箱与实验流水线](./01-sandbox-experiment-pipeline.md)
2. [因子准入、批准、回滚和审计](./02-factor-promotion-governance.md)

## 阶段验收

- 任意候选代码只在受限容器运行。
- 未来数据、样本外、稳定性和成本门禁可自动执行。
- 未批准候选无法被每日生产通道加载。
- research-automation-service停机不影响每日生产量化任务。
- ACTIVE版本可以回滚，历史快照不被覆盖。
