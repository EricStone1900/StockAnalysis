# 00-04 架构基线详细实施计划

## 目标与边界

本计划将阶段 00 的架构约束转化为可评审、可检查的文档基线。只创建或更新架构、ADR、契约草案、测试与验收文档；禁止创建服务源码、数据库迁移、基础设施配置、Controller、Repository、Agent 或 Workflow。阶段 01 才落地工程与工具链。

## 前置输入与产物

执行前通读阶段总设计、服务设计索引、共享契约、事件架构及 V2 路线图。执行后以下文件共同构成基线：

- [服务目录与事实所有权](./05-service-catalog-baseline.md)。
- [依赖与通信基线](./06-dependency-communication-baseline.md)。
- [共享语义与契约草案](./07-shared-semantics-contract-baseline.md)。
- [ADR 决策登记](../../architecture/adr/ADR-001-018-register.md)。

`90-test-plan.md` 和 `99-acceptance.md` 是本计划的测试和人工签署入口。

## 执行顺序

### 1. 冻结服务与事实边界

按服务目录逐项核对限界上下文、Aggregate、唯一写入服务、数据库、入站/出站端口和禁止写入项。对同一事实出现两个写入方、跨服务共享表、平台服务保存领域可写副本的情况，记录为 P0 并停止后续冻结。

重点是区分“编排/读取”与“拥有事实”：`platform-api-service` 只做 BFF 聚合，`workflow-orchestration-service` 只保存流程状态，`agent-service` 只保存运行与结构化判断；三者均不能写 Portfolio、Risk、Proposal、Order 或 Fill。

### 2. 冻结依赖与通信规则

维护编译、同步、异步和人工流程四张矩阵。编译依赖只允许本服务、共享契约和基础设施抽象；跨服务领域模型只能经生成的 OpenAPI/AsyncAPI 类型访问。发现 A 同步依赖 B 且 B 同步或异步回写 A 时，改为查询投影、领域事件或 Temporal Process Manager。

REST 只用于必须立即获得明确结果的查询和命令，例如硬风控、审批和创建 OrderIntent；NATS JetStream 只传播已经发生的领域事实；Temporal 只承载长流程、重试、人工等待和补偿。三种机制不得互相替代。

### 3. 冻结共享语义和契约草案

执行共享语义基线中的 `SecurityId`、Decimal、时区、交易日、`DataVersion`、`availableAt`、命令、错误和事件规则。其核心是 Point-in-Time：回放时刻 R 只能使用 `availableAt <= R` 的记录；`occurredAt` 不能替代可见时间。任何时间、版本或来源不完整的投资输入必须被拒绝或标记为不可用。

### 4. 处理 ADR 门禁

逐项补全 ADR-001～ADR-018 的背景、候选方案、推荐方案、受影响服务、决策人、结论和生效日期。没有你的明确决定时，状态必须是 `BLOCKED`，并注明阻塞范围。ADR-016、ADR-015 及涉及阶段 01 的工程决策未冻结时，不得启动阶段 01；业务供应商和后续阶段 ADR 可保留阻塞，但必须不破坏阶段 01 的共享边界。

### 5. 验证与签署

按 `90-test-plan.md` 执行文档、边界、依赖、契约和时间语义检查；将命令、检查结果、问题和修复结论写入验收记录。最后由你按 `99-acceptance.md` 完成人工验收。任何 P0/P1、未解释的所有权冲突或未确认的阶段 01 关键 ADR 都使结论为 `FAIL`。

## 完成定义

服务事实均有唯一 Owner，四张依赖矩阵无环，跨服务通信规则无歧义，共享时间和精度语义可用于阶段 01 契约工具链，且 ADR 阻塞状态透明可追溯。通过人工签署前，不得开始阶段 01。
