# market-data-service测试计划

## 自动化执行

在仓库根目录先启动基础设施：

```bash
./scripts/infra-up.sh
cd services/market-data-service
UV_CACHE_DIR="$PWD/.uv-cache" uv run ruff check .
UV_CACHE_DIR="$PWD/.uv-cache" uv run mypy src
UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest tests/unit
MARKET_DATA_DATABASE_URL='postgresql://market_data:market_data_local_only@localhost:5433/market_data' \
  UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest \
  tests/integration/test_postgres_repository.py::test_status_batch_repository_claims_retries_and_prevents_duplicate_success \
  -o addopts=''
```

单元测试覆盖领域、PIT、质量门禁、Outbox 重试、OpenAPI 路径、不可变 Parquet Hash 和运行时依赖探测；集成测试覆盖 PostgreSQL 乐观锁、MinIO Hash 校验和 NATS JetStream 投递。

`tests/integration`中的部分旧用例会清理整张来源元数据表，因此**不得**将全套集成测试连接到已导入真实Release的运行库。全套集成测试只能使用独立、可销毁的测试数据库；上面的选择器是运行库中允许执行的隔离批次测试，仅操作`test-batch-*`测试记录。

## 必测集合

- Domain：SecurityId、Calendar、Session、DataVersion状态机。
- Repository：唯一约束、乐观锁、PIT查询和迁移回滚。
- Contract：Security/Calendar/Bar/FinancialFact/DataVersion API及发布事件。
- Financial：复权、公司行动、时区、交易日、停牌和未来数据。
- Reliability：重复导入、进程崩溃、供应商限流、Artifact损坏和事件重放。
- Security：供应商Secret不出日志，其他服务数据库用户只读或无权访问。
- Provider：固定Release、Manifest/Hash校验、接口字段漂移、限流重试和无凭证降级。
- Reconciliation：主源优先、补充源只补缺、冲突隔离、字段级Provenance和来源切换新版本。
- Revision：首次披露、更正公告、多个修订版本及`availableAt`保守截止规则。

## 验收Fixture

至少包含正常交易日、节假日、午休、停牌、上市、退市、分红送转、财报更正和供应商字段缺失。

关键断言：选择历史日期T生成的结果只包含`availableAt <= T`的数据。

当前 Fixture 位于`services/market-data-service/tests/fixtures/`，包含交易日/节假日/午休说明、停牌、上市、退市、公司行动、财报更正、日线及供应商字段缺失案例。

## 真实来源追加测试

实现[首版数据源策略](./05-v1-data-source-policy.md)中的Adapter后，新增独立的录制Fixture与受控联网冒烟测试。CI默认读取脱敏录制数据，不依赖第三方在线稳定性；人工验收再执行真实下载。

- 同一`investment_data` Release重复导入只产生一个逻辑结果，归档或Manifest损坏必须失败。
- 不允许解析浮动`latest`作为可复现输入；Release Tag、归档Hash和Manifest Hash写入证据。
- 主源字段完整时，BaoStock、AKShare或Tushare不得静默替换；缺失补全必须标记字段来源。
- 同一财务事实的初始值和更正值均保留；更正公布前的`asOf`只能返回旧值。
- CNINFO原公告Hash无法验证、披露时间缺失或跨来源冲突超阈值时，相关质量状态不得为`PASS`。
- 未配置Tushare Token时可选Adapter必须明确跳过并保留能力降级原因；配置后验证配额、退避和Secret脱敏。
- 对固定Release Qlib归档执行日历、股票池、OHLCV字段覆盖、二进制索引和价格范围检查；缺字段、无效价格、OHLC关系错误或索引越界必须为`FAIL`。
- 收盘字段非有限值但没有停牌/交易状态证据时必须为`WARN`并写入质量报告，不能静默按正常数据发布。
- BaoStock状态录制Fixture必须覆盖正常交易、停牌、ST、未知值、代码映射失败和供应商字段漂移；探针失败时真实任务不得执行。
- 每个收盘空洞必须且只能产生一项状态对账结果。`SUSPENDED`可解释空洞但不得填价；`TRADING`加空洞必须为`FAIL`；无状态证据必须为`WARN`。
- 快速模式必须显式确认、使用含`fast`的独立策略版本并提供审批引用和操作者；不得调用BaoStock，必须落盘假设Artifact和`business_assumption`字段级Provenance，结果只能为`SUSPENSION_ASSUMED / manual_business_assumption`与`WARN`。不得产生`TradingStatusFact`或`baostock_tradestatus_0`。
- 快速模式与精确模式对同一空洞必须以不同策略版本保存，彼此不可覆盖；精确模式重新对账后仍以BaoStock原始Artifact为准。
- 状态事实的`availableAt`必须为响应落盘时间。以早于该时间的`asOf`查询时不得返回该事实，防止用事后抓取数据污染历史回测。
- 批次计划必须按“交易所、证券代码、交易日”稳定排序；相同输入和批次大小应得到相同`batch_id`、首尾键与序号。
- PostgreSQL集成测试必须验证批次原子认领：`PENDING`仅能被一个执行器认领；`RUNNING`与`SUCCEEDED`均不可再次认领；`FAILED`可重试且`attempts`递增；成功后`last_error`为空。
- 批次探针只能处理一个已认领批次且不得发布DataVersion；同一成功批次再次提交应返回不可认领错误，不得再次请求供应商或新增原始Artifact。
- 真实任务应验证限速、可恢复批次、相同批次幂等工件Hash和失败批次不发布事件；CI仅运行录制Fixture。
- 内部导入接口未配置`MARKET_DATA_IMPORT_TOKEN`时返回`503`；错误Token返回`403`，两种情况均不得产生下载、MinIO写入或NATS事件。
- 使用相同`Idempotency-Key`重复导入固定Release，预期DataVersion、原始Artifact和质量报告不重复创建，发布事件仅一条。
