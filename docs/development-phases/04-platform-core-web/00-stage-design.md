# 阶段04：Portfolio Risk、Platform API与Web总设计

## 目标

实现独立的`portfolio-risk-service`、`platform-api-service`和React前端基础，让用户可以录入持仓、查看量化结果、查看新鲜度和审计信息。

## 开发边界

本阶段不运行Agent、不执行完整投资决策、不接券商。portfolio-risk先建立领域骨架和只读组合指标，完整预交易规则在阶段08接通；platform-api只做BFF，不拥有持仓事实。

## 实施要求

- 两个NestJS服务使用独立Database/User，禁止跨库写入。
- 前后端只通过生成Client和公开API交互。
- 金额和数量使用Decimal语义。
- 所有写操作具备身份、幂等和审计。

## 顺序文档

1. [Platform API服务和API基础](./01-platform-core-modules.md)
2. [组合、配置和查询API](./02-portfolio-query-api.md)
3. [React Dashboard和研究页面](./03-react-web-dashboard.md)

## 阶段验收

- 用户可录入人工PortfolioSnapshot。
- 前端可查询最新量化快照、持仓和数据新鲜度。
- 所有写操作有身份、幂等和审计。
- 任一聚合依赖失败时返回带状态的部分结果。
- 两个服务镜像可以单独启动、停止和迁移数据库。
