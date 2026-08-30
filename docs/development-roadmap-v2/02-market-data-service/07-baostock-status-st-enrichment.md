# 02-07 BaoStock交易状态与ST补充

## 目标与非目标

本工作为固定`investment_data` Qlib日频版本补充交易状态与ST标识，用于解释`close`非有限值。原始Qlib行情、归档与Hash保持不变；结果以引用父版本的新“状态增强DataVersion”发布。

本工作不填充、前向填充、删除或改写价格；不以BaoStock估值或价格覆盖主数据；也不将当前抓取到的历史状态伪造成历史时点已知信息。

首期状态增强范围暂定为`CN_A_EQUITY_EX_BSE`：保留原始Qlib归档中的北交所、指数和基金等记录，但只将沪深普通A股纳入BaoStock状态对账、质量分母或阶段03首期股票池。质量报告必须分别记录被排除的BSE与非普通股空洞数量；未来接入覆盖北交所的可靠状态来源并扩展标的分类后，以新策略版本恢复该范围。

## 契约与所有权

`market-data-service`拥有`TradingStatusFact`及其对账结果。事实至少含证券、交易日、标准状态（`TRADING`、`SUSPENDED`、`DELISTED`、`UNKNOWN`）、`isSt`、原始供应商字段、`observedAt`、`availableAt`、原始Artifact、来源策略及字段级Provenance。

`availableAt`固定为本次原始响应落盘时间。缺少可证明的历史披露时间时，状态事实只能用于该时间之后的查询；历史`asOf`不得读取它。量化服务只能消费状态增强DataVersion及其Artifact引用。

## 实施顺序

1. 以录制响应执行能力探针，冻结BaoStock字段、代码映射、日期范围与异常语义；探针失败不得启动真实批量导入。
2. 针对Qlib收盘空洞及正常交易日对照样本抓取状态，按批次将原始响应不可变写入MinIO，并保存Hash和抓取元数据。
3. 标准化为交易状态事实，写入字段级Provenance；不可识别值统一为`UNKNOWN`，不得猜测。
4. 对每个收盘空洞生成对账结论：`SUSPENDED`为已解释停牌，`TRADING`为未解释缺失并隔离，无记录为状态未知；ST只补充约束信息，不改变价格。
5. 生成引用父Qlib版本、状态Artifact和对账报告的状态增强版本，并由质量门禁决定是否可供阶段03使用。

## 质量门禁

质量报告必须分别统计空洞总数、已确认停牌、正常交易缺失、状态未知、ST数量、覆盖率和冲突数，分类数量之和必须等于空洞总数。

只有目标股票池与日期范围内状态覆盖完整、`TRADING + close空洞`为零、状态未知为零、所有字段可追溯且PIT测试通过时，状态增强版本才能为`PASS`。否则保持`WARN`；字段矛盾、工件Hash异常或PIT泄漏为`FAIL`。BaoStock历史覆盖不足时，应明确记录降级范围，不得仅为进入阶段03而升级质量状态。

## 可配置处理模式

默认处理模式为`fast`快速模式，适用于开发、临时回测和受控预览：不调用BaoStock，而是为输入空洞生成`SUSPENSION_ASSUMED / manual_business_assumption`。它必须使用包含`fast`的新`policy_version`，并显式提供`fast_mode_acknowledged=true`、审批引用和操作者。系统把每批假设范围、父Artifact Hash、审批引用和操作者写成不可变Artifact，并通过字段级Provenance标记`business_assumption`。

`exact`精确模式必须通过`STATUS_ENRICHMENT_MODE=exact`或请求体`mode:"exact"`显式启用。它逐条查询BaoStock，并且只有原始响应中的`tradestatus=0`才能产生`SUSPENSION_CONFIRMED / baostock_tradestatus_0`。它是正式发布、阶段03真实数据验收与最终质量门禁的唯一可用模式。

快速模式不生成`TradingStatusFact`、不得写入`baostock_tradestatus_0`、不得覆盖精确模式的对账记录；质量状态固定为`WARN`，供应商覆盖率为`0`，不得发布为`PASS`或用于阶段03正式验收。要得到最终结论，必须以新的精确策略版本重新执行对账。

批次脚本默认`STATUS_ENRICHMENT_MODE=fast`及`STATUS_PROBE_POLICY_VERSION=v1-close-gap-fast`。使用快速模式还需设置`STATUS_FAST_MODE_ACKNOWLEDGED=true`、`STATUS_FAST_MODE_APPROVAL_REF=<审批引用>`和`STATUS_FAST_MODE_OPERATOR=<操作者>`；这些值不得包含密钥或令牌。切换精确模式时必须同时显式设置`STATUS_ENRICHMENT_MODE=exact`和独立的精确策略版本。

当前不再继续执行快速模式全量批次。`run_status_batch_worker.py`额外要求`STATUS_BULK_EXECUTION_ENABLED=true`才会启动；该开关只能在重新评审后临时设置。剩余空洞由阶段03按固定策略与`close-gap-index`按需解释，详见[阶段03总设计](../03-quant-research-service/00-stage-design.md#收盘空洞的按需解释策略)。

## 安全与运行要求

真实抓取为受令牌保护的内部任务；登录信息仅从环境变量或Secret读取，不写入日志、Artifact或文档。任务应限速、超时重试、支持按批次断点续跑；失败批次不得发布新的状态增强版本。CI只使用脱敏录制Fixture，人工验收才允许联网。

## Ubuntu独立人工验证步骤

Ubuntu必须独立产生原始Artifact、数据库记录与质量报告；不得复制Mac的PostgreSQL、MinIO卷或探针结果作为验收证据。以下命令假设仓库部署在`/srv/StockAnalysis`、远端分支为`main`；若实际路径或分支不同，先替换为对应值。

1. 连接服务器并获取代码，确认工作区无未提交改动：

   ```bash
   ssh <ubuntu-user>@<ubuntu-host>
   cd /srv/StockAnalysis
   git pull --ff-only origin main
   git status --short
   ```

2. 执行本地静态验证并启动基础设施。首次构建会下载镜像与Python依赖：

   ```bash
   cd /srv/StockAnalysis/services/market-data-service
   UV_CACHE_DIR="$PWD/.uv-cache" uv run ruff check .
   UV_CACHE_DIR="$PWD/.uv-cache" uv run mypy src
   UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest tests/unit
   cd /srv/StockAnalysis
   ./scripts/infra-up.sh
   docker compose -f infra/compose/docker-compose.yml up -d --build market-data-service
   curl --fail http://localhost:3000/ready
   ```

3. 仅在当前终端输入一次性导入令牌；输入时终端不回显属于正常行为。不要把令牌写入`.env`、Shell历史或文档：

   ```bash
   read -rs MARKET_DATA_IMPORT_TOKEN
   export MARKET_DATA_IMPORT_TOKEN
   docker compose -f infra/compose/docker-compose.yml up -d --force-recreate market-data-service
   ```

4. 按[首次真实Release人工导入](./06-first-real-release-import.md)导入固定的`investment_data` Release，并将成功响应保存为`/tmp/parent-data-version.json`。确认其中的`artifact_uri`、`artifact_hash`、`source_release_tag`和`quality_status`均存在。不得使用浮动`latest`。

5. 先执行单条探针，而不是全量任务。该命令默认排除北交所、指数和基金等非首期普通A股；`probe: true`保证不会发布部分覆盖的DataVersion：

   ```bash
   jq -n --slurpfile parent /tmp/parent-data-version.json \
     '{parent_version:$parent[0],policy_version:"v1-baostock-status",policy_document_uri:"docs/development-roadmap-v2/02-market-data-service/07-baostock-status-st-enrichment.md",available_at:"<UTC-ISO-8601时间>",max_gaps:1,probe:true,exclude_bse:true,exclude_non_equity:true,mode:"exact"}' \
     >/tmp/baostock-status-probe-request.json

   curl --fail-with-body --request POST \
     http://localhost:3000/internal/v1/jobs/enrich-baostock-status \
     --header 'Content-Type: application/json' \
     --header 'Idempotency-Key: baostock-status-probe-001' \
     --header "X-Import-Token: $MARKET_DATA_IMPORT_TOKEN" \
     --data @/tmp/baostock-status-probe-request.json \
     --output /tmp/baostock-status-probe-response.json
   jq . /tmp/baostock-status-probe-response.json
   ```

   `<UTC-ISO-8601时间>`必须不早于执行探针的实际UTC时间，例如`date -u +%Y-%m-%dT%H:%M:%SZ`的输出。探针响应应包含`facts`、`reconciliations`和`report`；`excluded_bse_gap_count`与`excluded_non_equity_gap_count`可大于零。若结论为`UNEXPLAINED_MISSING`，`quality_status`必须为`FAIL`，这是预期的阻断，不是可忽略错误。

6. 核验持久化证据。将`<证券ID>`和`<交易日>`替换为探针响应中的值：

   ```bash
   docker compose -f infra/compose/docker-compose.yml exec -T postgres \
     psql -U market_data -d market_data \
     -c "SELECT security_id, trading_day, trading_status, is_st, raw_artifact_hash FROM trading_status_facts WHERE security_id = '<证券ID>' AND trading_day = '<交易日>';" \
     -c "SELECT security_id, trading_day, status, reason FROM close_gap_reconciliations WHERE security_id = '<证券ID>' AND trading_day = '<交易日>';"
   ```

   还应在MinIO中确认响应给出的`raw_artifact_uri`存在，且其SHA-256与`raw_artifact_hash`一致。原Qlib归档Hash必须保持不变。

7. 立即禁用内部导入任务：

   ```bash
   unset MARKET_DATA_IMPORT_TOKEN
   docker compose -f infra/compose/docker-compose.yml up -d --force-recreate market-data-service
   curl --fail-with-body --request POST http://localhost:3000/internal/v1/jobs/enrich-baostock-status \
     --header 'Content-Type: application/json' \
     --header 'Idempotency-Key: verify-disabled' \
     --header 'X-Import-Token: disabled' \
     --data '{}' \
     --output /tmp/disabled-response.json || true
   jq . /tmp/disabled-response.json
   ```

   预期返回`503`与`import task is not enabled`；若返回请求体字段校验错误，说明服务尚未完成重建或令牌仍被保留，不能继续验收。

当前只允许完成上述探针验收。全量补充必须等待批次进度、限速、超时重试与断点恢复能力完成，并由人工明确批准。

## 全量前可靠性门禁

全量任务按稳定的“交易所、证券代码、交易日”顺序计划批次，并在`status_enrichment_batches`记录批次身份、范围、尝试次数、状态和最后错误。只有失败批次可被单独重试；已成功批次不得重复请求供应商或覆盖原始Artifact。全量执行前还必须接入供应商限速、指数退避、超时和恢复Runbook，并增加批次级集成测试。

运行参数由环境变量控制：`BAOSTOCK_MAX_ATTEMPTS`、`BAOSTOCK_INITIAL_BACKOFF_SECONDS`、`BAOSTOCK_MIN_INTERVAL_SECONDS`和`BAOSTOCK_QUERY_TIMEOUT_SECONDS`。正式全量任务必须在验收记录中保存实际参数值；不得将这些参数与令牌混在同一Secret中。

## 单批次恢复演练

批次模式只能用于`probe: true`，因此不会发布覆盖不完整的状态增强DataVersion。它用于在全量授权前验证：批次计划可重复生成、单个批次能被原子认领，以及成功批次不能被重复执行。执行前先按上一节的步骤完成父版本导入和令牌配置；以下示例只处理排序后的第`0`批、最多`1`条合格的沪深普通A股空洞。

```bash
export BAOSTOCK_MAX_ATTEMPTS=3
export BAOSTOCK_INITIAL_BACKOFF_SECONDS=1
export BAOSTOCK_MIN_INTERVAL_SECONDS=0.2
export BAOSTOCK_QUERY_TIMEOUT_SECONDS=30
docker compose -f infra/compose/docker-compose.yml up -d --force-recreate market-data-service

jq -n --slurpfile parent /tmp/parent-data-version.json \
  '{parent_version:$parent[0],policy_version:"v1-baostock-status",policy_document_uri:"docs/development-roadmap-v2/02-market-data-service/07-baostock-status-st-enrichment.md",available_at:(now|strftime("%Y-%m-%dT%H:%M:%SZ")),probe:true,batch_size:1,batch_ordinal:0,exclude_bse:true,exclude_non_equity:true,mode:"exact"}' \
  >/tmp/baostock-status-batch-0-request.json

curl --fail-with-body --request POST \
  http://localhost:3000/internal/v1/jobs/enrich-baostock-status \
  --header 'Content-Type: application/json' \
  --header 'Idempotency-Key: baostock-status-batch-0-001' \
  --header "X-Import-Token: $MARKET_DATA_IMPORT_TOKEN" \
  --data @/tmp/baostock-status-batch-0-request.json \
  --output /tmp/baostock-status-batch-0-response.json
jq . /tmp/baostock-status-batch-0-response.json
```

响应成功后，检查批次状态；应仅有`ordinal=0`为`SUCCEEDED`，其余计划批次仍为`PENDING`。再次提交相同批次应返回`422`与`status batch is not claimable`，并且不得新增BaoStock原始Artifact。若首次调用失败，状态应为`FAILED`，可用新的幂等键重试同一`ordinal`；记录`attempts`和`last_error`，而不是删除进度行。

```bash
docker compose -f infra/compose/docker-compose.yml exec -T postgres \
  psql -U market_data -d market_data \
  -c "SELECT ordinal, state, attempts, last_error FROM status_enrichment_batches ORDER BY created_at, ordinal;"
```

此演练与真实全量执行不同：它只验证一个可恢复的纵向切片。完整批次计划、供应商配额和发布授权仍须由人工完成阶段验收后另行批准。
