# market-data-service验收

## 前置条件

在仓库根目录运行`./scripts/infra-up.sh`，然后执行：

```bash
docker compose -f infra/compose/docker-compose.yml up -d --build market-data-service
curl http://localhost:3000/live
curl http://localhost:3000/ready
```

预期第一个接口返回`{"status":"UP"}`；第二个接口返回`status: UP`，且`postgres`、`minio`、`nats`均为`true`。

## 人工验收步骤

1. 打开`http://localhost:3000/docs`，确认 Security、Calendar、DataVersion 的 API 均存在，且两个写接口要求`Idempotency-Key`。
2. 在 Swagger 中向`POST /api/v1/securities`提交`SSE / 600000 / 浦发银行`与唯一幂等键；再以同一键重复提交。两次均应成功，随后`GET /api/v1/securities/600000`应只返回一条证券。
3. 调用`GET /api/v1/calendars/CN_A?day=2026-08-28`，确认返回上午`09:30-11:30`和下午`13:00-15:00`两个时段；将日期改为周末，预期无时段且非交易日。
4. 使用 MinIO 上传一个文件，记录其 SHA-256 和`minio://artifacts/<key>` URI。调用`POST /api/v1/data-versions`发布 PASS 版本；预期返回`READY`。以相同幂等键重试，预期不产生第二个事件。
5. 将请求中的 Artifact Hash 改错后再次发布；预期版本为`FAILED`，并且`GET /api/v1/data-versions/latest`仍返回先前 READY 版本。
6. 查看 NATS JetStream 的`STOCK_FACTS`，确认主题`stock.market-data.data-version.published.v1`消息仅含版本、范围、质量状态、Artifact URI 和发生时间，不包含 Artifact 内容或密钥。
7. 运行[测试计划](./90-test-plan.md)中的全部命令。Ruff、Mypy、单元测试与集成测试都必须通过。
8. 重复执行相同输入生成 Qlib Parquet Artifact，确认两个 SHA-256 相同；以修正前的`asOf`查询财务事实，确认看不到之后才可用的修正记录。

## 正式版v1数据源追加验收

当前Fixture验收完成后仍需执行以下检查，才能把阶段02判定为“可供阶段03真实数据验收使用”：

1. 按[首次真实Release人工导入](./06-first-real-release-import.md)选择并导入一个固定的`investment_data` Release Tag，保存归档、Manifest及其SHA-256；确认导入过程未请求浮动`latest`，且无Token时内部导入接口返回`503`。
2. 连续导入同一Release两次，确认DataVersion结果幂等；篡改Manifest或归档后重新导入，确认发布被质量门禁阻止。
3. 抽取至少三个正常交易日，以及停牌、ST、复权事件各一个样本，对照原始Artifact检查OHLCV、成交额、交易状态和复权语义。
4. 构造主源缺失和跨来源冲突，确认补充值带字段级来源；冲突超过阈值时进入隔离报告，不能静默覆盖。
5. 选择至少一家公司具有初始财报和更正公告的真实样本，分别在更正前后执行`asOf`查询；旧时点只能看到旧值，新时点可看到修订链和公告原文Hash。
6. 关闭每个补充源或移除可选Tushare Token，确认系统明确记录降级范围，价值/质量因子准入被阻止，而不是返回伪完整数据。
7. 检查许可清单、署名要求、调用配额、Secret存储、限流告警和数据删除/回滚Runbook。
8. 按[交易状态与ST补充](./07-baostock-status-st-enrichment.md#ubuntu独立人工验证步骤)在Ubuntu独立执行受控探针。保存父Qlib DataVersion、状态批次的原始URI/Hash、策略版本和抓取时间；确认原始Qlib Artifact未发生变化，且Mac运行数据未被作为验收证据复制。
9. 将质量报告中的收盘空洞总数与“已确认停牌、正常交易缺失、状态未知、冲突”逐项相加，结果必须相等。抽样核对至少一条停牌、一条ST和一条正常交易日；停牌样本仍无填充价格，ST样本仅增加状态与Provenance。
10. 分别以早于和晚于状态Artifact落盘时间的`asOf`查询同一状态事实。前者不得可见，后者才可见。若存在正常交易日收盘空洞、未知状态或PIT失败，验收结论必须为`FAIL`或`WARN`，不得放行阶段03。
11. 按[单批次恢复演练](./07-baostock-status-st-enrichment.md#单批次恢复演练)执行一个`batch_size=1`探针。查询`status_enrichment_batches`：目标批次必须为`SUCCEEDED`、`attempts=1`，其余批次保持`PENDING`；再次请求相同序号必须返回`422`，且数据库中不得产生额外状态事实、对账记录或原始Artifact。
12. 在受控测试批次上模拟一次供应商超时，确认状态变为`FAILED`并保存`last_error`；以新`Idempotency-Key`重试后必须转为`SUCCEEDED`且`attempts=2`。不得通过删除进度行来实现重试。
13. 如启用快速模式，使用独立的含`fast`策略版本、显式确认、审批引用和操作者执行一条探针。确认不产生BaoStock请求或`TradingStatusFact`；对账记录必须为`SUSPENSION_ASSUMED / manual_business_assumption`，其字段级Provenance和不可变Artifact来源均为`business_assumption`，质量必须为`WARN`。快速模式结果不得作为阶段03真实数据验收输入。

验收记录新增以下字段：来源策略版本、各来源Release/API版本、原始Artifact URI与Hash、日期范围、证券数、行数、缺失率、补充率、冲突率、修订样本、许可引用及降级结论。

## 通过标准

所有自动化命令与基础八项人工检查通过后，可冻结DataVersion v1契约。正式版v1数据源追加验收也通过后，阶段03才可使用真实数据进行生产候选验收；量化服务始终只能通过API或Artifact引用消费数据。

## 2026-09-05 本地真实数据验收记录

- 固定 Release：`2026-07-29`；DataVersion：`cn-a-investment-data-2026-07-29-6a4947798614`。
- 归档 Hash：`6a4947798614d077add2d6ac14ae306eef2f287949de8ceeef06d66cb9d5de90`；Manifest Hash：`df26610d8ef97520e9c45eaf9bf1684b350e0bd7be7b66e4da4c0a1a4fcbb175`。
- 结构质量报告：`WARN`，原因 `unclassified_close_gap`，收盘非有限值 `577070`；因此该父 DataVersion 当前不能作为阶段03生产候选放行。
- BaoStock `exact` 单条探针：`PASS`；1 个收盘空洞被确认为 `SUSPENSION_CONFIRMED / baostock_tradestatus_0`，`UNEXPLAINED_MISSING=0`，`STATUS_UNKNOWN=0`，原始 Qlib Hash 未改变。
- `batch_size=1` 恢复演练：成功批次 `SUCCEEDED`、`attempts=1`；重复认领返回 `422 status batch is not claimable`。
- 本轮修复批次身份必须包含 `parent_version_id + policy_version`，避免不同 Release 的相同 ordinal 发生冲突；新增跨父 Release 回归测试。
- 结论：真实来源接入和精确状态探针通过；阶段02正式 PASS 仍被结构质量 WARN 和未完成的全量状态覆盖阻塞，不能放行阶段03。
