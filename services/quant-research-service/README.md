# quant-research-service

阶段03的量化研究服务。当前完成03-01的 S0/S1：Python 3.12 锁定依赖、健康检查，以及只读
`DataVersion`、`CloseGapHandlingPolicy`与确定性停牌掩码的领域契约。

服务不直接访问 `investment_data`、BaoStock、AKShare、CNINFO 或 Tushare；后续 Qlib Adapter
只能使用通过 SHA-256 校验的、由 `market-data-service` 发布的不可变 Artifact。

本地检查：

```sh
UV_CACHE_DIR="$PWD/.uv-cache" uv run ruff check .
UV_CACHE_DIR="$PWD/.uv-cache" uv run mypy src
UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest tests/unit
```

首次在本机执行前需安装 Python 3.12 并生成锁文件：

```sh
UV_CACHE_DIR="$PWD/.uv-cache" uv python install 3.12
UV_CACHE_DIR="$PWD/.uv-cache" uv lock
```

PostgreSQL 元数据迁移：

```sh
psql "$QUANT_RESEARCH_DATABASE_URL" -f migrations/001_research_metadata.sql
UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest tests/integration -o addopts=''
```
