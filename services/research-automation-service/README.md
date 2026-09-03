# research-automation-service

阶段 04-01 实验与 Sandbox 最小切片。服务只接受白名单 `scriptId` 和不可变 DataVersion Artifact 引用，
不接收任意源码，不拥有 quant 生产 Registry 权限。

本地检查：

```bash
UV_CACHE_DIR="$PWD/../../.uv-cache" uv run ruff check .
UV_CACHE_DIR="$PWD/../../.uv-cache" uv run mypy src
UV_CACHE_DIR="$PWD/../../.uv-cache" uv run pytest tests/unit tests/integration -o addopts=''
```

启用 PostgreSQL 时设置 `RESEARCH_AUTOMATION_DATABASE_URL`，并先执行
`migrations/001_research_automation.sql`。集成测试未配置数据库时会自动跳过。
