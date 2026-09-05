# 执行一致性整改实施计划

依据：[ADR-020](../../architecture/adr/ADR-020-execution-consistency-and-delivery-gates.md)。本文件是整改计划，不是完整业务验收证明。

## 目标与非目标

目标：批准不可伪造、写入原子化、占用不重复、恢复不重下，形成隔离环境真实人工E2E。非目标：生产自动下单、合并服务、跨库写入、放宽硬风控或删除历史验收。

## 顺序与文件清单

| 顺序 | 所有者与文件 | 输入输出和完成门禁 |
|---|---|---|
| S0 | 本计划、ADR-020、`packages/contracts/` | 已冻结授权、资源占用、DISPATCHING和幂等冲突契约 |
| S1/S2 | `trade-execution-service/src/application/execution-authorization.ts`、`execution-write-guard.ts` | 已实现默认拒绝及Grant字段匹配；服务身份不能替代业务批准，真实Reader待接通 |
| S2 | `trade-execution-service/src/application/execution-service.ts`、Repository | 已实现单连接事务写批次/Intent/Outbox，回滚后可重试，重启后恢复 |
| S2/S3 | portfolio-risk `resource-reservation`、迁移与Repository | 已实现资源冻结、组合锁、持久化和并发测试；账本写入与预留的统一事务及Fill结算仍待接通 |
| S4 | governance/risk授权API与生成Client | 验证当前批准和风险，而非只验证命令内ID；授权失败、撤销、旧版本全部拒绝 |
| S4/S5 | workflow真实Activity适配器及Event Starter | 明确未接受才释放；UNKNOWN按原幂等键查询，不能重建替代批次 |
| S6 | 三服务API、真实PostgreSQL/NATS、真实Temporal与Web | 指定提交完整E2E、故障注入、报告与签署 |

## ResourceReservation契约

唯一写入方为portfolio-risk，不能放在execution的独立数据库中代替账本占用。

- 输入：reservationId、portfolioId、ledgerVersion、decisionId、proposalVersion、riskEvaluationId、riskPolicyVersion、executionContentHash、idempotencyKey。
- 资源由已验证的执行计划推导，不接受调用方自报“availableCash”；每个BUY使用有上限的执行价格和费用缓冲，每个SELL使用权威可卖数量。
- 状态：RESERVED、DISPATCHING、IN_FLIGHT、UNKNOWN、SETTLED、RELEASED。前三类及UNKNOWN均保持资源占用。
- 每个组合最多一个活动预留，用数据库唯一约束和组合锁实现；锁必须同时覆盖持仓修正、公司行动与预留创建，不能只锁预留表。
- 重复幂等键且请求一致返回已有结果，不同载荷返回CONFLICT；旧ledgerVersion或旧风险版本拒绝。
- 未确认的卖出所得不计入买入可用现金；先卖后买也必须等待确认与入账。首版不支持依赖未成交所得的乐观买入。
- SETTLED必须同时证明全部订单终态且成交已幂等入账。RELEASED必须有执行权威未接受或确认撤销且无剩余成交的证明。TTL、HTTP异常和Workflow超时不构成释放依据。
- 保留资源的UNKNOWN必须暴露在Web、告警和审计中；恢复只查询原批次。

## 授权契约与安全

授权必须绑定全部Leg、批准ID/版本、持仓/策略/风险版本、预算DISPATCHING、资源预留及有效期。治理与风险分别验证自己的权威记录；执行不能跨库查表。服务身份使用受限凭证，字段级身份不能来自未经认证的Header。标准错误至少区分UNAUTHORIZED、AUTHORITY_UNAVAILABLE、VERSION_CONFLICT、RESOURCE_CONFLICT。

当前默认拒绝端口仅封闭安全缺口，**不代表已经完成权威授权适配器**。不得为了演示将测试allow stub接入HTTP运行入口。

## 测试矩阵

| 场景 | 可衡量结果 |
|---|---|
| 正确Hash搭配伪造审批ID | 无READY记录、无Outbox，拒绝可见 |
| 第二条Intent或Outbox写入失败 | 本次批次、全部Intent与事件均为0条 |
| 并发重复批次 | 1批、每Leg 1条、1个创建事件 |
| 进程重启后状态变化及重复成交 | 可恢复；成交事实与事件各1条 |
| 两笔各占80%的买入并发 | 最多1笔预留成功；无资金超用 |
| 部分卖出、买入先到、UNKNOWN | 不提前使用卖出所得、不释放剩余占用 |
| 批次接受响应丢失或接受后异常 | UNKNOWN，释放调用为0次 |
| 真实Worker误配Fake | 启动失败，不登记为REAL_E2E |

## 验收记录与回滚

专项已执行结果见[整改记录](../../architecture/architecture-remediation-2026-09-05.md)。资源预留已持久化，但尚未与账本写入、权威授权Reader、真实Activity贯通前，阶段05/10/12当前发布门禁为FAIL，不覆盖历史人工确认。

记录提交、镜像/迁移/契约版本、运行环境、报告、风险、回滚目标和签署人。保留已有账本及Outbox；回滚时关闭执行并核对在途批次，不清理UNKNOWN、不重复发送历史委托。
