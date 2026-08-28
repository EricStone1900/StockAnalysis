# 测试与验收标准

## 1. 文档要求

每个整体阶段和每个独立微服务都必须有测试计划与验收清单。实现文档中的每个步骤同时写就近测试；`90-test-plan.md`负责完整覆盖，`99-acceptance.md`负责发布门禁。

## 2. 测试层级

1. Domain Unit：业务规则、Value Object、状态机。
2. Application：Use Case、事务、权限和幂等。
3. Repository Integration：真实PostgreSQL、迁移和并发。
4. API Contract：OpenAPI请求、响应、错误和兼容性。
5. Event Contract：AsyncAPI、重复、乱序、迟到、DLQ和回放。
6. Component：服务加真实数据库/消息系统，外部依赖用Fake。
7. E2E：只在阶段总门禁运行真实跨服务链路。
8. Non-functional：安全、性能、故障、恢复和观测。

金融特有测试还包括PIT、未来数据泄漏、时区、交易日、复权、成本、滑点、停牌、涨跌停和样本外验证。

## 3. 验收证据模板

```text
阶段/服务：
代码提交：
镜像Digest：
迁移版本：
契约版本：
测试命令：
测试报告：
覆盖的风险场景：
未完成项：
已知风险：
回滚方案：
验收人/日期：
结论：PASS | CONDITIONAL_PASS | FAIL
```

`CONDITIONAL_PASS`只能用于不影响下一阶段安全边界的非关键项，必须有到期时间；硬风控、时间语义、数据质量、幂等、权限或恢复失败只能判定FAIL。

## 4. 统一测试命令约定

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm test:integration
pnpm test:contract
pnpm test:e2e

uv run ruff check .
uv run mypy src
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/contract
```

实际脚本由阶段01落地，所有CI和人工文档使用同名入口，禁止每个服务发明不一致的命令。

## 5. 退出条件

- 所有硬门禁测试PASS。
- 无未声明破坏性契约变更。
- 重复执行测试结果稳定。
- 关键事件和写命令可追溯correlationId。
- Runbook可以由未参与开发的人按步骤执行。
- `99-acceptance.md`已经记录证据和结论。

