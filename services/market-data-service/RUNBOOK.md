# market-data-service 运行手册

## SLO 与新鲜度

| 数据 | 最大延迟 |
|---|---:|
| 日线 | 18 小时 |
| 分钟线 | 5 分钟 |
| 财务事实 | 24 小时 |

供应商必须配置速率限制、超时、重试次数和许可元数据。主来源失败时切换备用来源；切换来源、回补或 Artifact 重放必须创建新的 DataVersion，绝不覆盖旧版本。

## 恢复指定版本

1. 从 Artifact URI 取得原始内容并验证保存的 SHA-256 Hash。
2. 以原始来源、范围和 `availableAt` 重新标准化并运行质量检查。
3. 质量为 PASS/WARN 时创建新 DataVersion；FAIL 不得发布 READY。
4. 对比重建版本的 `contentHash`；不同则保留差异证据并禁止替换历史版本。

数据库、MinIO 或 NATS 不可用时停止 READY 发布；恢复后从最后成功检查点补发 Outbox。历史回补运行在独立队列，不能阻塞当日发布。

## 本地迁移与恢复验证

按顺序使用`migrations/001_security_calendar.sql`和`migrations/002_source_lineage.sql`初始化独立`market_data`数据库。恢复时先验证Artifact Hash，再重放Outbox；Inbox以`eventId + consumerName`去重。Qlib只能读取DataVersion生成的只读Artifact，不能查询业务表。

## investment_data固定Release导入

只允许指定日期格式的Release Tag，禁止`latest`。Adapter必须从同一Release取得`qlib_bin.tar.gz`与`qlib_bin.manifest.json`，校验Manifest十个字段、归档大小/Hash、Qlib必需成员和交易日历，再写入MinIO的`raw/investment_data/<tag>/<archive-hash>/`不可变路径。相同Tag与Hash的重复导入必须返回相同对象；同一路径的不同内容必须失败。

真实Release导入前确认数据许可与署名范围，保存Release Tag、两份SHA-256、DataVersion、来源策略版本和质量报告。结构校验通过不代表行情质量验收通过；未完成标准化、交易日、停牌、复权和对账检查前，不得把结果作为阶段03真实数据生产候选。

## 首次真实Release人工导入

以下操作由验收人手工执行。导入接口默认禁用；不要把Token写进仓库、`.env`、命令历史或验收报告。

1. 选择一个已发布的固定日期Tag，记录Release链接及上游许可信息。设置`RELEASE_TAG`和保守的`AVAILABLE_AT`；后者应晚于该Release可获得的实际时间，日期无时刻时取下一交易时点。
2. 在终端以静默方式输入一次性导入Token，然后重建本地服务。Token只通过当前进程环境传给Compose，完成验收后退出该终端或清除变量。

```bash
export RELEASE_TAG='替换为YYYY-MM-DD Release Tag'
export AVAILABLE_AT='替换为实际可用时间，例如2026-08-29T01:00:00Z'
read -rs MARKET_DATA_IMPORT_TOKEN
export MARKET_DATA_IMPORT_TOKEN
docker compose -f infra/compose/docker-compose.yml up -d --force-recreate market-data-service
```

3. 使用唯一幂等键调用内部接口；`policy_document_uri`固定指向仓库中的首版数据源策略。

```bash
curl --fail-with-body --request POST http://localhost:3000/internal/v1/jobs/import-investment-data \
  --header 'Content-Type: application/json' \
  --header 'Idempotency-Key: investment-data-first-import-001' \
  --header "X-Import-Token: $MARKET_DATA_IMPORT_TOKEN" \
  --data "{\"release_tag\":\"$RELEASE_TAG\",\"policy_version\":\"v1\",\"policy_document_uri\":\"docs/development-roadmap-v2/02-market-data-service/05-v1-data-source-policy.md\",\"available_at\":\"$AVAILABLE_AT\"}"
```

4. 保存响应中的DataVersion、`artifact_uri`、`artifact_hash`、`source_manifest_hash`和`quality_report_uri`。用相同幂等键重复一次请求，预期返回同一DataVersion且NATS只增加一条发布事件。
5. 查看质量报告。`FAIL`不得产生READY版本；`WARN`必须记录空洞数量和原因，未补齐停牌/ST证据前不得把该版本用于阶段03生产候选。抽查正常日、停牌或空洞样本、复权事件和ST样本，完成阶段02验收文档的其余检查。
6. 验收后执行`unset MARKET_DATA_IMPORT_TOKEN`。若导入失败，保留MinIO原始Artifact与质量报告作为证据；不要手工覆盖对象或删除历史DataVersion。
