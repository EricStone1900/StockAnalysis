# 02-06 首次真实Release人工导入

本文由验收人手工执行，用于将一个固定`investment_data` Release导入本地MinIO并发布DataVersion。不得使用`latest`，不得把Token、数据归档或MinIO数据卷提交到Git。

## 1. 启动与预检查

在仓库根目录执行：

```bash
cd /Users/huangbosong/Documents/ChatGPT/StockAnalysis
./scripts/infra-up.sh
docker compose -f infra/compose/docker-compose.yml up -d --build market-data-service
curl --fail http://localhost:3000/ready
df -h .
```

预期`postgres`、`minio`和`nats`均为`true`。确认磁盘有足够空间保存归档及MinIO副本。

## 2. 固定输入与启用一次性Token

在[`investment_data` Releases](https://github.com/chenditc/investment_data/releases)中选择一个已发布、格式为`YYYY-MM-DD`的Tag，记录链接、许可和署名要求。将实际值填入；`AVAILABLE_AT`必须晚于数据实际可获得时间。若没有时刻证据，取目标日后的下一A股交易时点（09:30北京时间，即`01:30Z`）。

```bash
export RELEASE_TAG='替换为固定YYYY-MM-DD Tag'
export AVAILABLE_AT='替换为保守可用时间，例如2026-08-31T01:30:00Z'
read -rs MARKET_DATA_IMPORT_TOKEN
export MARKET_DATA_IMPORT_TOKEN
docker compose -f infra/compose/docker-compose.yml up -d --force-recreate market-data-service
```

`read -rs`会静默读取Token；不要把Token值写进命令、`.env`、文档或验收记录。

## 3. 导入固定Release

```bash
export IMPORT_KEY='investment-data-first-import-001'
export IMPORT_RESPONSE='/tmp/investment-data-import-1.json'

curl --fail-with-body --request POST \
  http://localhost:3000/internal/v1/jobs/import-investment-data \
  --header 'Content-Type: application/json' \
  --header "Idempotency-Key: $IMPORT_KEY" \
  --header "X-Import-Token: $MARKET_DATA_IMPORT_TOKEN" \
  --data "{\"release_tag\":\"$RELEASE_TAG\",\"policy_version\":\"v1\",\"policy_document_uri\":\"docs/development-roadmap-v2/02-market-data-service/05-v1-data-source-policy.md\",\"available_at\":\"$AVAILABLE_AT\"}" \
  --output "$IMPORT_RESPONSE"

sed -n '1p' "$IMPORT_RESPONSE"
```

请求可能持续数分钟。保存响应中的`version_id`、`status`、`quality_status`、`artifact_uri`、`artifact_hash`、`source_release_tag`、`source_manifest_hash`和`quality_report_uri`。

## 4. 验证来源与质量报告

```bash
curl --fail http://localhost:3000/api/v1/data-versions/latest
docker compose -f infra/compose/docker-compose.yml exec -T postgres \
  psql -U postgres -d market_data -P pager=off -c \
  "SELECT source, source_release_tag, source_record_id, raw_artifact_hash, raw_artifact_uri, source_policy_version FROM raw_artifacts WHERE source = 'investment_data' ORDER BY source_record_id;"
```

预期有归档和Manifest两条`raw_artifacts`记录，且Tag等于`$RELEASE_TAG`。从响应复制`quality_report_uri`，去掉`minio://artifacts/`前缀后设为`QUALITY_KEY`，再读取报告：

```bash
export QUALITY_KEY='替换为quality/开头的完整路径'
docker compose -f infra/compose/docker-compose.yml exec -T -e QUALITY_KEY market-data-service \
  python -c "import os; from boto3.session import Session; body = Session().client('s3', endpoint_url=os.environ['MINIO_ENDPOINT'], aws_access_key_id=os.environ['MINIO_ACCESS_KEY'], aws_secret_access_key=open(os.environ['MINIO_SECRET_KEY_FILE']).read().strip()).get_object(Bucket=os.environ['ARTIFACT_BUCKET'], Key=os.environ['QUALITY_KEY'])['Body'].read(); print(body.decode())"
```

检查`daily_quality.status`、`reasons`、`close_feature_coverage`和`nonfinite_close_count`。`FAIL`不得继续；`WARN`不得用于阶段03生产候选，须先补充停牌/ST证据。

## 5. 幂等、清理与结论

使用第3节完全相同的请求、`IMPORT_KEY`和输入再执行一次，保存为`/tmp/investment-data-import-2.json`：

```bash
cmp -s /tmp/investment-data-import-1.json /tmp/investment-data-import-2.json && echo '幂等响应一致'
```

预期输出`幂等响应一致`，且不得新增第二个发布事件。完成后禁用接口：

```bash
unset MARKET_DATA_IMPORT_TOKEN
docker compose -f infra/compose/docker-compose.yml up -d --force-recreate market-data-service
```

验收记录必须附带Release链接、DataVersion、两份Hash、质量报告、幂等结果、日期范围、缺失/空洞统计、许可引用和验收结论。详细通过标准见[阶段02验收](./99-acceptance.md)。
