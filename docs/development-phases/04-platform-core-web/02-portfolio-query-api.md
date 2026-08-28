# 04-02 组合、配置和查询API

## 目标

在独立`portfolio-risk-service`实现人工持仓快照和组合指标骨架；在`platform-api-service`实现配置入口和Dashboard聚合查询。

## 实施步骤

### 1. 人工快照命令

```ts
const manualPortfolioSnapshotSchema = z.object({
  effectiveAt: z.string().datetime({ offset: true }),
  cash: decimalStringSchema,
  positions: z.array(z.object({
    symbol: z.string(),
    exchange: exchangeSchema,
    quantity: decimalStringSchema,
    averageCost: decimalStringSchema,
  })),
  source: z.literal('MANUAL'),
});
```

portfolio-risk数据库金额使用NUMERIC，Node领域层使用Decimal库。写入要求operatorId和idempotencyKey；platform-api转发命令但不保存持仓副本。

### 2. PortfolioSnapshot

从流水/输入和指定MarketDataVersion计算，不把估值结果写回原始持仓数量。

```ts
interface PortfolioSnapshot {
  portfolioSnapshotId: string;
  asOf: string;
  cash: string;
  marketValue: string;
  totalEquity: string;
  positions: PositionSnapshot[];
  marketDataVersion: string;
  ledgerVersion: number;
}
```

### 3. 配置发布

配置使用`DRAFT -> PUBLISHED -> RETIRED`，包括模型Profile、数据新鲜度和显示设置。RiskPolicy由portfolio-risk-service建表并提供只读接口，本阶段不实现放行逻辑；BFF不能直接写该表。

### 4. Dashboard聚合

并行读取最新量化、持仓和服务健康，返回分区状态：

```ts
type SectionResult<T> =
  | { status: 'OK'; data: T; freshness: DataFreshness }
  | { status: 'UNAVAILABLE' | 'STALE'; error?: ErrorEnvelope; data?: T };
```

## 测试案例

1. 相同幂等键不会创建重复快照。
2. 负数量或非法Decimal被拒绝。
3. 行情版本变化产生新估值快照，不修改数量。
4. research服务失败时Dashboard其他分区仍返回。
5. 旧数据明确标记STALE。

## 完成条件

- 人工持仓和查询API可用。
- 配置发布有版本和审计。
- Dashboard聚合没有跨Schema写入。
- 使用platform-api数据库账户写portfolio-risk数据库的权限测试必须失败。
