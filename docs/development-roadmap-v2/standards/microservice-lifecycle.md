# 微服务项目统一生命周期

## 1. 适用范围

所有Node.js/TypeScript、Python微服务均使用以下S0～S6阶段。阶段文档可以合并书写，但实现和验收顺序不能合并跳过。

## 2. S0：边界和契约

- 确定限界上下文、事实所有权、Aggregate和状态机。
- 列出入站HTTP/Event/Temporal端口与出站Repository/Client/Event端口。
- 定义API、事件、错误码、幂等键和数据新鲜度。
- 写清禁止事项、依赖方向和安全权限。

产物：服务设计、OpenAPI/AsyncAPI草案、数据库草案、ADR。门禁：所有权无冲突，依赖无环。

## 3. S1：可运行骨架

统一目录：

```text
src/
  domain/
  application/
  ports/inbound/
  ports/outbound/
  adapters/inbound/http/
  adapters/inbound/events/
  adapters/outbound/persistence/
  adapters/outbound/events/
  adapters/outbound/clients/
  bootstrap/
tests/unit/
tests/integration/
tests/contract/
migrations/
Dockerfile
```

必须实现配置校验、结构化日志、错误映射、`/live`、`/ready`、`/metrics`、`/version`和空迁移。门禁：独立构建、迁移、启动、停止通过。

## 4. S2：最小纵向切片

选择最简单但真实的Use Case，贯通：

```text
Inbound Adapter -> Application -> Domain -> Repository
                                  -> Outbox -> Event Relay
```

最小切片必须包含事务、幂等、错误返回和测试，禁止先堆满Controller或Repository再补Domain。

## 5. S3：核心领域能力

- 补齐Aggregate、Value Object、Domain Policy和状态转换。
- 实现乐观锁、版本、审计字段和时间语义。
- 优先使用Fake Client，避免未完成上游阻塞本服务开发。
- 每个业务规则必须至少有成功、边界、拒绝测试。

## 6. S4：契约和事件集成

- 只使用生成的OpenAPI Client和AsyncAPI类型。
- 写服务使用Transactional Outbox；消费者使用Inbox/Event ID幂等。
- 至少一次投递下重复、乱序、迟到消息不得产生重复副作用。
- 大对象仅传Artifact引用和Hash。

## 7. S5：生产强化

- 超时、重试、熔断、限流、资源上限和受控降级。
- 最小权限、Secret注入、日志脱敏、审计和供应链检查。
- OpenTelemetry Trace、Metric、告警和Runbook。
- 备份恢复、迁移兼容、故障注入和容量基线。

## 8. S6：独立发布验收

服务必须在不启动Agent、Workflow和其他业务服务的情况下，通过Fake依赖完成：

- 独立Docker Compose启动。
- 独立Database/User迁移。
- OpenAPI和事件契约测试。
- 关键Use Case、故障、幂等和恢复测试。
- 镜像健康、安全扫描和回滚演练。

验收证据包括提交、镜像Digest、迁移版本、测试命令、报告、已知风险和签署人。

