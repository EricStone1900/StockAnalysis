# news-intelligence-service测试计划

- Source Adapter、许可、原文Artifact和Provenance。
- URL/Hash/近似/聚类去重。
- Security实体关联、歧义、别名和退市公司。
- publishedAt/availableAt、时区和迟到新闻。
- Candidate和FinancialNewsEvent契约。
- 重复采集、重复Agent结果、Outbox恢复和来源限流。
- 不可信正文、恶意指令、Hash篡改和日志脱敏。

Fixture至少含公告、媒体报道、转载、标题更新、公司简称冲突和恶意正文。

## 本机验证记录（Mac）

- `uv run ruff check .`：通过。
- `uv run mypy src`：通过。
- 未配置持久化环境变量时运行 `pytest tests/unit -o addopts=''`：16 passed。
- 配置本机 PostgreSQL 后运行 `pytest tests/integration -o addopts=''`：1 passed，覆盖迁移、新闻、Candidate、FinancialNewsEvent及重复 `agentRunId`。
- MinIO适配器使用受控 Fake Client 验证Hash、不可变对象和重复写入；真实MinIO连通性需在部署环境单独验证。

单元测试必须清除新闻服务持久化环境变量，避免测试误连接本机数据库；集成测试只允许使用测试库。禁止在测试输出中记录访问密钥。
