# 阶段00：架构与开发基线

## 目标

在编写业务代码前冻结第一版限界上下文、数据所有权、服务依赖、契约规则、时间语义和测试门禁。

## 边界

本阶段只修改架构、ADR、契约草案和开发规则，不实现Controller、Repository、Agent或Workflow。

## 顺序

1. [服务边界与所有权](./01-service-boundaries.md)。
2. [依赖、契约和时间语义](./02-dependencies-contracts-time.md)。
3. [开发依赖与Fake替代矩阵](./03-development-dependency-matrix.md)。
4. [测试计划](./90-test-plan.md)。
5. [阶段验收](./99-acceptance.md)。

## 产物

- 服务目录、上下游矩阵和数据库所有权。
- REST、NATS、Temporal使用决策。
- SecurityId、交易日、availableAt、DataVersion等共享语义。
- ADR-001～ADR-018初始结论或明确阻塞状态。
- V2测试与验收标准。

## 退出门禁

任何事实只能有一个写入服务；依赖图无环；跨服务禁止共享表和ORM Entity；下一阶段可以据此生成服务骨架。
