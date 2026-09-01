FROM ghcr.io/astral-sh/uv:0.12.7 AS uv
FROM python:3.12-slim
WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY services/quant-research-service/pyproject.toml services/quant-research-service/uv.lock ./
COPY services/quant-research-service/src ./src
COPY services/quant-research-service/migrations ./migrations
RUN uv sync --frozen --no-dev
CMD ["/app/.venv/bin/uvicorn", "main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "3000"]
