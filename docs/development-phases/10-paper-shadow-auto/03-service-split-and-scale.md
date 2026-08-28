# 10-03 容量扩缩、数据迁移和上线门禁

## 目标

所有限界上下文已经从阶段00开始独立部署；本步骤不再做“从platform-core拆服务”，而是依据真实负载隔离进程、数据库实例和基础设施资源，并完成自动交易上线门禁。

## 扩缩顺序

### 1. Agent独立扩缩

六个Agent继续使用同一`agent-service`镜像，但按Task Queue、NATS Durable Consumer和模型限额独立扩容。新闻或盯盘流量不得挤占main-decision与risk-review资源。

### 2. Worker与API进程隔离

同一限界上下文内可以把API、批处理、事件Consumer拆为不同进程：

- quant-research的API、Qlib生产Worker和回测Worker。
- market-monitor的Gateway、规则Worker与回放Worker。
- market-regime的日频、盘中和API进程。
- research-automation的控制API与不可信Sandbox Job。

它们共享服务所有权和契约，但使用不同启动命令、资源Quota和Service Account。

### 3. 数据基础设施隔离

只有出现容量、安全或恢复目标需求时，才把本地共用的PostgreSQL容器迁移为独立实例。迁移不能改变Database Owner、API、事件Owner和Aggregate语义。

### 4. 事件与工作流容量

- 根据Lag拆分NATS Consumer，不按事件重复创建业务动作。
- 根据保留与恢复目标调整Stream副本、存储和DLQ。
- Temporal Worker按Task Queue扩容；Workflow/Activity版本保持长流程兼容。

## 数据迁移要求

- 使用Outbox和只读复制验证，不直接停机搬表。
- 明确新旧实例写入口切换时间，不允许双主写入。
- 迁移前后执行行数、内容Hash、余额、持仓和事件序列对账。
- 保留回滚窗口；Temporal长工作流使用版本化Activity兼容迁移。
- 事件Consumer以Inbox幂等，回放时禁用真实券商和通知副作用。

## 上线门禁

- Paper和Shadow指标达到ADR阈值。
- P0/P1未解决问题为0。
- 订单、成交、持仓和现金对账稳定。
- NATS、Temporal、数据库和Broker故障演练通过。
- Kill Switch、人工接管和仅减仓模式演练通过。
- 生产监控和交易时段响应责任明确。

## 测试案例

1. 单独扩容financial-news-agent不会增加main-decision消费并发。
2. 同一事件在滚动升级期间被新旧Consumer观察，业务副作用仍只有一次。
3. 数据库迁移前后相同风险Fixture结果一致，持仓和现金Hash一致。
4. NATS重放只重建投影，不重复成交或通知。
5. Worker滚动升级时Temporal长工作流继续。
6. 新执行实例不可用时系统失败关闭，不绕过它下单。

## 完成条件

- 每次容量或实例迁移有ADR、契约测试、回滚方案和对账报告。
- 自动交易只在小额白名单运行，不扩展到未验证账户。
- 扩缩不改变事实所有权、安全边界和低频交易约束。
