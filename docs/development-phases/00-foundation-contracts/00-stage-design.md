# 阶段00：工程与契约基础总设计

## 目标

建立后续所有模块共同依赖的Monorepo、开发基础设施、跨语言契约生成、质量检查和可观测性。该阶段不实现股票业务逻辑。

## 开发边界

负责：目录、Workspace、独立服务容器、按服务隔离的PostgreSQL、Temporal、NATS JetStream、Redis、MinIO、契约源、生成Client、日志和CI。

不负责：行情采集、Qlib、Agent、持仓风控和交易功能。

## 实施要求

- 所有工具版本锁定并可在新环境复现。
- 契约和生成代码只有一个事实来源。
- 本地开发凭据与生产凭据完全分离。
- 基础能力先有测试和CI，再允许领域模块依赖。

## 顺序文档

1. [Monorepo与空应用骨架](./01-monorepo-scaffold.md)
2. [本地基础设施](./02-local-infrastructure.md)
3. [共享契约与代码生成](./03-contract-generation.md)
4. [质量、可观测性与CI](./04-quality-observability-ci.md)

## 阶段产物

- pnpm和Python Workspace。
- web、12个独立微服务项目空入口，以及通用agent-service的六部署配置。
- OpenAPI、AsyncAPI和JSON Schema唯一契约源及生成包。
- Docker Compose基础设施。
- Outbox/Inbox、NATS Stream、Durable Consumer和DLQ模板。
- 统一health、version、correlationId和错误结构。

## 阶段验收

- 新机器按README可以启动全部空服务。
- 所有Readiness通过。
- 每个服务可独立构建镜像、运行迁移、启动和停止，不依赖共享业务表。
- 重复发布测试事件不会重复产生业务效果，事件可按Sequence回放。
- TypeScript和Python契约可重复生成且Git工作区无漂移。
- Lint、类型检查、单测和契约测试进入CI。
- 仓库中没有真实密钥。
