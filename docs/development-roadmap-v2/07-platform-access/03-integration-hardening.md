# 07-03 权限、部分失败和实时状态

## 实施步骤

1. 定义Viewer、Researcher、RiskReviewer、Approver、ExecutionOperator和Admin角色。
2. 建立SSE状态通道，只推任务/事件摘要；正文和大对象继续由API读取。
3. 为下游设置独立超时、并发上限、缓存和Circuit Breaker。
4. 审计所有写代理的actor、原因、请求Hash和结果引用。
5. 建立前后端版本兼容、Feature Flag和安全Headers。

## 故障场景

- quant不可用时Portfolio页面仍可用。
- SSE断线自动重连但不重复显示同一eventId。
- RBAC变化立即影响后续请求。
- 缓存结果超过validUntil必须标STALE。

## 完成条件

Web与BFF可独立部署；领域服务部分故障时用户能准确看到缺失范围。

