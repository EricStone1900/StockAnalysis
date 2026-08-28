# market-data-service测试计划

## 必测集合

- Domain：SecurityId、Calendar、Session、DataVersion状态机。
- Repository：唯一约束、乐观锁、PIT查询和迁移回滚。
- Contract：Security/Calendar/Bar/FinancialFact/DataVersion API及发布事件。
- Financial：复权、公司行动、时区、交易日、停牌和未来数据。
- Reliability：重复导入、进程崩溃、供应商限流、Artifact损坏和事件重放。
- Security：供应商Secret不出日志，其他服务数据库用户只读或无权访问。

## 验收Fixture

至少包含正常交易日、节假日、午休、停牌、上市、退市、分红送转、财报更正和供应商字段缺失。

关键断言：选择历史日期T生成的结果只包含`availableAt <= T`的数据。

