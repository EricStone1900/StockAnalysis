# ADR-001～ADR-018 决策登记

## 使用规则

本登记是阶段 00 的 ADR 来源。每项在确认前均为 `BLOCKED`，不能被视为已批准；确认时补充决策人、日期、最终选择与后果。每次变更必须说明兼容性、受影响阶段和回滚/迁移策略。

| ADR | 决策主题 | 候选与推荐方向 | 影响与阶段 01 门禁 | 状态 |
|---|---|---|---|---|
| 001 | 主/备用行情供应商 | 合规供应商双源；推荐先确认许可、复权与历史覆盖再选型 | 影响 market-data；否 | BLOCKED |
| 002 | 证券主键、交易所与复权 | 稳定 `SecurityId` + 交易所属性；复权口径显式版本化 | 影响共享契约；是 | BLOCKED |
| 003 | 财务 PIT 语义 | `availableAt` 为唯一历史可见性门槛 | 影响数据契约；是 | BLOCKED |
| 004 | PostgreSQL/Parquet/MinIO 归属 | 事务事实用 PostgreSQL，分析列数据用 Parquet，大对象用 MinIO | 影响基础设施；是 | BLOCKED |
| 005 | Qlib 转换与数据版本发布 | 不可变 `DataVersion` Artifact 发布 | 影响阶段 02/03；否 | BLOCKED |
| 006 | 因子准入与审批角色 | 量化复验后人工批准，禁止研究服务直写 ACTIVE | 影响阶段 03/04；否 | BLOCKED |
| 007 | 盘中行情 Gateway | vn.py Gateway 或轮询；按许可、稳定性与延迟决策 | 影响阶段 06；否 | BLOCKED |
| 008 | 市场状态定义 | 固定枚举、迟滞和版本化规则；LLM 不计算状态 | 影响阶段 06；否 | BLOCKED |
| 009 | 模型 Provider 绑定 | 逻辑 Profile + 多 Provider 适配，配置隔离 | 影响阶段 08；否 | BLOCKED |
| 010 | 交易批次与日上限 | 每日最多 1～2 批，`NO_TRADE` 为正常结果 | 影响阶段 05/10；否 | BLOCKED |
| 011 | 人工 Fill 与持仓事实 | execution 写 Fill，portfolio-risk 写账本和持仓投影 | 影响阶段 05；否 | BLOCKED |
| 012 | 新闻许可与原文留存 | 仅合规来源；记录许可元数据与留存规则 | 影响阶段 06；否 | BLOCKED |
| 013 | Paper/Shadow/生产账户隔离 | 独立凭证、账户、Feature Flag 与审计边界 | 影响阶段 12；否 | BLOCKED |
| 014 | 风险复核策略 | 硬规则优先；证据不足或模型冲突默认拒绝/人工处理 | 影响阶段 09/10；否 | BLOCKED |
| 015 | JetStream 保留与 DLQ | Facts/Signals/Operations 分 Stream，明确保留、DLQ、恢复演练 | 影响事件基础设施；是 | BLOCKED |
| 016 | 服务边界与调用矩阵 | 以阶段 00 服务目录和通信基线为候选结论 | 影响全部服务；是 | BLOCKED |
| 017 | 六 Agent 部署隔离 | 同镜像、独立权限、Task Queue、Consumer 和 Model Profile | 影响阶段 08；否 | BLOCKED |
| 018 | Strategy Plugin SDK 与第三方隔离 | 版本化 SDK、隔离 Runner、SBOM/许可证门禁、人工激活 | 影响阶段 03；否 | BLOCKED |

## 确认记录模板

每项确认时，在对应 ADR 下追加以下内容；若需完整论证，可拆分为独立 `ADR-xxx-<topic>.md` 并从本表链接。

```text
状态：ACCEPTED | REJECTED | BLOCKED
背景：
候选方案：
最终选择：
后果与受影响服务：
兼容性/迁移/回滚：
决策人：
生效日期：
```

## 当前阻塞结论

ADR-002、003、004、015、016 是阶段 01 的硬门禁；它们未确认时不得创建共享契约、基础设施或服务骨架。其余 ADR 可以在不改变已冻结边界的前提下延后，但进入受影响阶段前必须转为 `ACCEPTED` 或明确 `REJECTED`。
