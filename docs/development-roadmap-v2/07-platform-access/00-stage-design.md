# 阶段07：平台访问层

## 目标

交付`platform-api-service`和React Web，只通过生成Client聚合已验收领域服务，为后续Agent和人工工作流提供可观测、可操作的界面基础。

## 顺序

1. [Platform API骨架与查询](./01-platform-api.md)。
2. [React Web骨架与领域页面](./02-react-web.md)。
3. [权限、部分失败与实时状态](./03-integration-hardening.md)。
4. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 边界

- BFF不保存行情、持仓、建议、风险或订单事实。
- Web不直接调用内部微服务、NATS、数据库或模型Provider。
- 第一版只提供研究、持仓、快照、服务状态和人工治理基础页面，不接真实Agent运行按钮。


## ADR-020整改增量

遵循[ADR-020](../../architecture/adr/ADR-020-execution-consistency-and-delivery-gates.md)。M1允许前置只读页面；Web到BFF到真实数据服务验证代理、新鲜度和降级；开发身份头不构成生产认证。 保留服务S0～S6，不变更事实所有权，不开放生产自动交易。前置依赖未具备时明确阻塞对应真实能力；允许独立验证的切片继续执行。
