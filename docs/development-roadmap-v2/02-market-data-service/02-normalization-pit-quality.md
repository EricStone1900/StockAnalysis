# 02-02 标准化、PIT与数据质量

## 实施步骤

1. 定义Raw、Normalized和Published三层数据，原始Artifact保留来源、许可、采集时间和Hash。
2. 标准化日线、分钟线、财务事实、公司行动和复权因子；价格和金额使用Decimal。
3. 财务数据同时保存periodEnd、announcedAt、availableAt和revision。
4. 实现Point-in-Time查询，先过滤`availableAt <= asOf`，再选择当时最新修订。
5. 建立完整性、唯一性、范围、跨字段、交易日、复权连续性和来源一致性规则。
6. 质量结果分PASS/WARN/FAIL；FAIL数据不可进入Published层。

PIT查询骨架：

```sql
SELECT DISTINCT ON (security_id, fact_type, period_end) *
FROM financial_fact
WHERE available_at <= :decision_as_of
ORDER BY security_id, fact_type, period_end, available_at DESC, revision DESC;
```

## 测试

- 财报更正前的历史查询不能看到更正值。
- 当日收盘数据不能在收盘前可见。
- 未来股票池、退市样本和复权信息不得泄漏。
- 缺失率、异常跳变和重复Bar触发正确质量级别。

