# platform-api-service

## 1. 定位

面向 React 前端和受信任内部客户端的统一入口。它是控制平面的 BFF/API Gateway，不负责运行大模型、回测、因子计算或长时间采集任务。

推荐技术栈：NestJS、Fastify、OpenAPI、PostgreSQL、Redis、SSE。

## 2. 职责边界

负责：

- 登录、身份认证、RBAC 和操作审计。
- 前端所需的聚合查询。
- 系统、策略、Agent、模型和风险参数配置。
- 持仓录入与查询入口；写操作转发给portfolio-risk-service。
- 交易建议、人工审批和历史记录入口；状态由decision-governance-service拥有。
- 启动、暂停、重跑 Temporal 工作流。
- SSE 推送任务进度、重要事件和审批提醒。

不负责：

- 直接访问模型厂商 API。
- 在 HTTP 请求中运行 Qlib、RD-Agent 或回测。
- 直接抓取财经新闻。
- 直接调用券商接口。
- 绕过硬风控生成可执行订单。

## 3. 内部模块

    AppModule
      AuthModule
      UserModule
      ConfigModule
      PortfolioQueryModule
      ResearchQueryModule
      NewsQueryModule
      DecisionQueryModule
      ApprovalModule
      WorkflowControlModule
      AuditQueryModule
      RealtimeNotificationModule

各 Query Module 通过生成的内部 Client 调用对应服务，不在 Controller 中编写跨服务业务逻辑。

## 4. 对外 API

主要端点：

- GET /api/v1/dashboard
- GET /api/v1/portfolio
- PUT /api/v1/portfolio/manual-snapshot
- GET /api/v1/research/snapshots/latest
- GET /api/v1/stocks/{symbol}/analysis
- GET /api/v1/stocks/{symbol}/news-events
- GET /api/v1/decisions
- GET /api/v1/decisions/{decisionId}
- POST /api/v1/decisions/{decisionId}/approve
- POST /api/v1/decisions/{decisionId}/reject
- GET /api/v1/workflows/{runId}
- POST /api/v1/workflows/{workflowType}/start
- GET /api/v1/audit/events

所有变更接口必须写入 actorId、requestId、correlationId 和客户端时间。

## 5. 聚合规则

Dashboard 查询可以聚合：

- 最新量化快照。
- 最新新闻重要事件。
- 当前持仓和风险摘要。
- 待审批交易建议。
- 最近工作流状态。

聚合失败时使用部分响应结构，但必须标注每个分区的 status 和 freshness；不能用旧数据冒充最新数据。

## 6. 存储

本服务只保存：

- 用户、角色和权限。
- UI 偏好和展示配置。
- 策略和系统配置的发布记录。
- 审批操作的入口审计。

量化结果、新闻事件、风险快照和订单仍由各自领域服务拥有。

## 7. 安全与可靠性

- API Key 和模型密钥不能返回前端。
- 审批接口要求二次校验和幂等键。
- 配置发布采用草稿、审核、已发布状态。
- 对内部服务设置超时、熔断和隔离舱。
- 对读取接口使用短时缓存，对审批和持仓接口禁止不透明缓存。
- SSE 只推送状态和标识符，详情重新通过授权 API 查询。

## 8. 后续扩展

- 接入企业 SSO、OIDC 和细粒度数据权限。
- 为多账户提供独立BFF视图，但持仓、风控和决策事实继续由对应领域服务拥有。
- 增加移动端 BFF。
- 增加 WebSocket，但不用于关键状态唯一传输。
- 增加多账户、多组合和多市场租户隔离。

## 9. 验收标准

- OpenAPI 可以生成可用的前端 Client。
- 任一聚合依赖故障时 Dashboard 不整体崩溃。
- 审批请求重复提交不会产生多个状态变化。
- 所有配置和审批变更可按用户、时间和请求追溯。
