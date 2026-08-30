# market-data-service

阶段02的市场数据服务基础实现。使用`uv run uvicorn src.main:app --port 3000`启动。

当前提供Security、交易日历、DataVersion、Artifact Hash、PIT基础查询，以及来源追溯、财务修订和字段对账的领域契约。数据库迁移按数字顺序执行：

```bash
psql "$MARKET_DATA_DATABASE_URL" -f migrations/001_security_calendar.sql
psql "$MARKET_DATA_DATABASE_URL" -f migrations/002_source_lineage.sql
```

`002_source_lineage.sql`创建来源策略、原始Artifact、财务修订、字段Provenance和对账结果表。容器启动会按数字顺序应用迁移。`investment_data`已具备固定Release下载、Manifest/归档校验、MinIO不可变落地、来源策略/Artifact持久化、结构质量报告、Qlib日频OHLCV质量扫描、受Token保护的内部导入入口与DataVersion发布应用服务；首次真实Release导入及质量验收、异步调度和字段级事实写入仍待执行。收盘空洞在没有停牌/交易状态证据时只会产生`WARN`。BaoStock、AKShare、CNINFO和Tushare Adapter尚未实现；接入顺序和门禁见[阶段02首版数据源与PIT补全策略](../../docs/development-roadmap-v2/02-market-data-service/05-v1-data-source-policy.md)。
