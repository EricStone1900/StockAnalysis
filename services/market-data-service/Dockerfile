FROM python:3.13-slim
WORKDIR /app
COPY services/market-data-service/pyproject.toml services/market-data-service/uv.lock ./
COPY services/market-data-service/src ./src
COPY services/market-data-service/scripts ./scripts
COPY services/market-data-service/migrations ./migrations
RUN pip install --no-cache-dir .
CMD ["/bin/sh", "-ec", "python scripts/bootstrap_infra.py && uvicorn --app-dir src main:app --host 0.0.0.0 --port 3000"]
