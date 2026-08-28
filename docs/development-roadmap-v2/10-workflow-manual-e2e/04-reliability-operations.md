# 10-04 可靠性、运维与发布

## 实施步骤

1. 为每个Workflow定义SLO、超时、最大重试、Blocked队列和人工Runbook。
2. 建立全局暂停、只观察、Agent禁用和执行禁用Feature Flag。
3. 监控Schedule、Workflow Lag、Activity失败、NATS Lag、快照stale、Agent成本和未决审批。
4. 进行Worker滚动升级、Workflow版本兼容、NATS/数据库/Provider故障和恢复演练。
5. 建立完整审计导出和事故复盘模板。

## 失败关闭规则

- 风控/证据/持仓不确定：不得新增或加仓。
- Order状态UNKNOWN：查询或人工处理，不重下。
- Agent全部Provider失败：REVIEW_BLOCKED。
- 对账差异未解决：禁用自动化入口。

## 完成条件

人工闭环可稳定运行，且关闭Agent或任一非关键情报服务后仍能明确降级。

