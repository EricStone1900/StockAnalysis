# 架构整改记录（2026-09-05）

## 基线与结论

- 基线提交：`4e6527336d81741d93c1dcc8e379c1b2d6bf5826`；本次变更尚未提交，测试针对当前工作区。
- 环境：Mac本机Node/pnpm；真实PostgreSQL通过本机Docker端口访问，测试创建随机独立Schema，结束后清理。
- 决策：[ADR-020](./adr/ADR-020-execution-consistency-and-delivery-gates.md)。
- 结论：本次为设计整改与执行安全专项，不是完整平台REAL_E2E或生产RELEASE验收。

## 已落实

| 问题 | 改动与验证范围 |
|---|---|
| 调用方可自行填写审批ID | 增加执行写入口服务身份Guard；缺失真实ExecutionAuthorization时默认拒绝创建批次；HTTP测试验证401及503 |
| 批次/Intent/Outbox非原子 | 执行应用服务使用同一连接BEGIN/COMMIT/ROLLBACK；数据库锁串行化初期写入与幂等查询 |
| 重启依赖内存 | 状态变更从数据库恢复Intent与成交历史；专项验证重新实例化后可继续处理 |
| 重复/超量成交 | 增量Fill以Decimal累计；重复成交不重复发布；相同幂等键不同载荷拒绝，超量拒绝 |
| 异常释放预算 | 接受请求异常和接受后步骤异常返回UNKNOWN、不释放预算；只有明确未接受才释放 |
| Worker只加载健康流程且静默Fake | 统一导出全部现有Workflow；新增worker命令；Fake仅允许显式非生产demo、执行关闭 |
| 契约分歧 | Envelope以packages/contracts的Schema及生成产物为准；增加兼容性可选聚合字段；执行接收状态统一为DISPATCHING |
| 本地启动耦合 | 增加local-stack分组入口、所需本地数据库配置、Web/BFF和Vite代理；Secret不覆盖；端口仅绑定loopback |
| 路线图和验收含混 | 增加M1/M2/M3纵向里程碑；同步受影响阶段设计/测试/验收；历史人工PASS与当前发布门禁分开 |
| 资金与可卖数量占用 | 增加机器契约、领域状态机、PostgreSQL持久化及组合锁；并发仅允许一个活动占用，UNKNOWN不自动释放 |
| 授权引用可以跨服务漂移 | 授权签发器逐项校验已批准Proposal、DISPATCHING预算、DISPATCHING资源占用、风险评估/策略版本、组合版本和执行内容Hash；任一不一致或过期即拒绝 |
| 数据库重启后治理状态机失忆 | Proposal与预算预留在迁移状态前按主键从PostgreSQL恢复到聚合，避免只依赖进程内Map |

## 未完成与发布阻塞

1. **权威执行授权适配器未接通**：签发规则和执行侧验签规则均已实现，但尚未以受服务身份认证保护的内部HTTP/gRPC接口连接治理、组合和执行服务；当前默认拒绝封闭缺口，测试allow stub仅在测试文件中。
2. **资源预留尚未接入账本结算**：资金、可卖数量、组合锁、持久化和同事务Outbox已实现；Fill、撤销、对账与公司行动尚未在同一事务更新或结算预留。详细顺序见[整改计划](../development-roadmap-v2/05-portfolio-governance-execution/07-execution-consistency-remediation.md)。
3. **真实Activity/Event Starter与恢复查询未接通**：Workflow测试调用实际函数但代理Activity；没有声称真实Temporal/NATS跨服务E2E通过。
4. **本地全栈未构建运行验证**：Compose配置及Web构建通过不等同于容器全部启动；尚无Mac峰值资源报告。full-demo不包含完整真实业务闭环。
5. 执行之外的写服务仍需逐一审查事务、鉴权和Inbox；当前整改不为全部服务背书。现有人工HTTP脚本须接入真实服务身份和业务授权后才能用于REAL_E2E。

因此，当前真实交易发布门禁为FAIL；历史人工确认仍保留其原有基线与范围，不被本记录撤销或扩大。

## 专项复现

在隔离环境设置`TRADE_EXECUTION_DATABASE_URL`后，从仓库根运行：

```sh
bash scripts/verify-execution-hardening.sh
pnpm --filter @stock/web lint
pnpm --filter @stock/web build
bash scripts/local-stack.sh config full-demo
git diff --check
```

验收范围：执行服务42项（含4项真实PostgreSQL事务/恢复测试）、工作流34项、契约6项；执行与工作流lint/typecheck、契约生成漂移检查、Web lint/build、Compose配置与Shell语法检查。实际结果以本次执行输出及就近测试为证据，不使用Fake测试数推导业务完成率。

## 版本、风险、回滚与签署

- 数据库：沿用执行迁移001；本次没有对已有业务Schema运行破坏性迁移。测试只清理自动创建的独立Schema。
- 契约：Envelope v1兼容可选字段；生成TS/Python产物随工作区更新。尚未生成发布镜像Digest或发布Tag。
- 行为变化：未配置可信授权时禁止创建批次；未认证执行写请求拒绝；Fake Worker默认不能启动；端口改为本机可达；历史Fill若使用累计量须先审计，不能直接按新增增量语义重放入账。
- 回滚：保持执行关闭，保留账本、Outbox和UNKNOWN。回滚代码前核对在途订单，不通过重发或删除数据卷修复。
- 自动检查执行者：Codex。真实E2E、上线风险与人工发布签署：未完成。
