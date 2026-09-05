# 阶段01：工程框架与全部服务骨架

## 目标

建立两种语言的统一微服务框架，并为全部服务创建可独立构建、迁移、启动和观测的空项目。此阶段不实现领域业务。

## 顺序

1. [Monorepo和服务模板](./01-monorepo-service-templates.md)。
2. [本地基础设施与隔离](./02-local-infrastructure.md)。
3. [契约、事件和Temporal工具链](./03-contract-event-workflow-toolchain.md)。
4. [CI、观测、安全和开发体验](./04-ci-observability-security.md)。
5. [测试计划](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 必须创建的项目

`market-data`、`quant-research`、`research-automation`、`portfolio-risk`、`decision-governance`、`trade-execution`、`news-intelligence`、`market-monitor`、`market-regime`、`platform-api`、`workflow-orchestration`、`agent-service`及`apps/web`。

## 禁止事项

- 不实现股票、因子、新闻、持仓或决策业务。
- 不共享业务数据库或ORM Entity。
- 不让模板框架依赖具体领域模块。


## ADR-020整改增量

遵循[ADR-020](../../architecture/adr/ADR-020-execution-consistency-and-delivery-gates.md)。本地infra/research/manual-services/full-demo分组、配置缺失检查和不覆盖Secret；记录Mac资源实测。 保留服务S0～S6，不变更事实所有权，不开放生产自动交易。前置依赖未具备时明确阻塞对应真实能力；允许独立验证的切片继续执行。
