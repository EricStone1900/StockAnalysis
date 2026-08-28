# 阶段01：市场数据总设计

## 目标

在独立`services/market-data-service`建立整个系统的证券、交易日历、行情、财务PIT和数据版本事实来源，并以Docker单独部署。

## 前置条件

- 阶段00全部通过。
- 完成ADR-001～ADR-004：数据源、证券主键、复权/PIT和存储归属。

## 开发边界

负责标准化和发布数据，不计算因子、不生成交易建议、不调用模型。

## 实施要求

- 第三方数据类型在Adapter边界转换。
- 所有历史查询遵守`availableAt`和DataVersion。
- Raw数据、标准数据和质量报告均可追溯。
- FAIL版本不能改变latest指针。
- 使用独立Database/User，通过Outbox发布`DataVersionPublished`事件。

## 顺序文档

1. [Security Master、交易日历与Provider](./01-security-calendar-adapters.md)
2. [标准化、PIT与数据质量](./02-normalization-pit-quality.md)
3. [版本快照、API与验收](./03-versioned-snapshot-api.md)

## 阶段验收

- 任意指定历史日可以重建当时已知的数据。
- 财务数据使用真实披露`availableAt`。
- 质量FAIL阻止版本发布。
- 相同DataVersion返回相同结果。
- Qlib和Node调用方使用同一证券与时间语义。
