# 02-08 BaoStock 状态批次运行与监控

## 目的

历史全量计划共 5,720 个批次，每批 100 条空洞。当前已暂停剩余快速模式批次，不得继续处理。已完成的快速模式记录保留为历史审计证据；剩余空洞改由阶段03依据固定策略和`close-gap-index`按需解释。

如未来决定恢复批处理，必须重新评审质量风险并显式设置`STATUS_BULK_EXECUTION_ENABLED=true`。执行仍须采用有限窗口，禁止一次性启动全部批次。

## 启动受控窗口

以下命令在 `market-data-service` 容器内执行。`STATUS_WORKER_START_ORDINAL` 为起始批次，`STATUS_WORKER_MAX_BATCHES` 为本次最多执行批次数：

```sh
docker compose -f infra/compose/docker-compose.yml exec -T \
  -e PYTHONPATH=src \
  -e STATUS_PROBE_VERSION_ID=<父DataVersion> \
  -e MARKET_DATA_DATABASE_URL=<容器内数据库地址> \
  -e STATUS_PROBE_POLICY_VERSION=v1-close-gap-fast \
  -e STATUS_PROBE_BATCH_SIZE=100 \
  -e STATUS_WORKER_START_ORDINAL=118 \
  -e STATUS_WORKER_MAX_BATCHES=100 \
  -e STATUS_ENRICHMENT_MODE=fast \
  -e STATUS_FAST_MODE_ACKNOWLEDGED=true \
  -e STATUS_FAST_MODE_APPROVAL_REF=<审批引用> \
  -e STATUS_FAST_MODE_OPERATOR=<操作者> \
  -e STATUS_BULK_EXECUTION_ENABLED=true \
  market-data-service python -u scripts/run_status_batch_worker.py
```

窗口开始前确认没有其他 `run_status_batch_worker.py` 进程；失败窗口不得并发重启。

默认运行快速模式。它不会访问BaoStock，但结果固定为`WARN`。当前阶段03采用按需解释策略，批处理结果仅供审计参考；若需要正式精确结果，显式使用`STATUS_ENRICHMENT_MODE=exact`与独立的精确策略版本。

```sh
STATUS_PROBE_POLICY_VERSION=v1-close-gap-fast \
STATUS_ENRICHMENT_MODE=fast \
STATUS_FAST_MODE_ACKNOWLEDGED=true \
STATUS_FAST_MODE_APPROVAL_REF=<审批引用> \
STATUS_FAST_MODE_OPERATOR=<操作者> \
python -u scripts/run_status_batch_worker.py
```

快速模式与精确模式的批次、Artifact、Provenance和对账记录按不同`policy_version`隔离；快速模式批次身份额外包含父DataVersion与策略版本，避免与既有精确批次碰撞。不得复用`v1-baostock-status-prod100`，也不得将`SUSPENSION_ASSUMED`统计为BaoStock确认停牌。

## 进度检查

```sh
docker compose -f infra/compose/docker-compose.yml exec -T postgres \
  psql -U market_data -d market_data -c "
  SELECT state, count(*)
  FROM status_enrichment_batches
  WHERE policy_version='v1-baostock-status-prod100'
  GROUP BY state ORDER BY state;"
```

每个窗口必须保存：起止批次、开始/结束时间、成功/失败数量、`last_error`、BaoStock登录/限速错误、Artifact与数据库计数。`FAILED` 批次使用新幂等键重试；不得删除批次、事实或Artifact。

## 全量发布门禁

只有全部批次为 `SUCCEEDED`、状态覆盖率和PIT检查通过、Artifact/Provenance完整且人工复核完成后，才能生成状态增强DataVersion并进入Ubuntu验收。
