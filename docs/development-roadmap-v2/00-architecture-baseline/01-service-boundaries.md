# 00-01 服务边界与事实所有权

## 实施步骤

1. 以[整体设计](../../architecture/stock-analysis-agent-system-design.md)的限界上下文表为基线。
2. 为每个服务登记Owner、Aggregate、Database/User、公开API、发布/订阅事件和禁止写入对象。
3. 单独登记`platform-api-service`、`workflow-orchestration-service`和`agent-service`为平台/应用层，不允许拥有行情、持仓、风险和订单事实。
4. 为六个Agent登记独立Tool白名单和输出契约，但不拆成六套代码仓库。
5. 形成服务依赖图；发现双向同步依赖时改为事件、查询投影或Process Manager。

核心登记格式：

```ts
interface ServiceCatalogEntry {
  serviceId: string;
  boundedContext: string;
  ownedAggregates: string[];
  database: string;
  inboundPorts: string[];
  outboundPorts: string[];
  forbiddenWrites: string[];
}
```

## 检查

- PortfolioSnapshot只由portfolio-risk-service写入。
- TradeProposal只由decision-governance-service写入。
- Order/Fill只由trade-execution-service写入。
- Agent和BFF数据库中没有上述事实的可写副本。

## 完成条件

服务目录评审通过，所有争议以ADR记录；未解决的事实所有权争议阻塞阶段01。

