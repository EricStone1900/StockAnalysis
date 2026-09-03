# portfolio-risk-service

阶段 05-01 的期初持仓导入最小切片。运行 `pnpm dev` 可启动本地HTTP服务；迁移脚本位于
`migrations/001_portfolio_ledger.sql`，PostgreSQL适配器通过注入`SqlClient`使用参数化SQL。

当前默认组合根使用内存账本，待数据库连接配置和事务边界验收后再切换生产实现。不得把密钥或生产连接串写入仓库。
