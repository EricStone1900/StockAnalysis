FROM python:3.13-slim
WORKDIR /app
COPY services/market-monitor-service/pyproject.toml .
RUN pip install --no-cache-dir .
COPY services/market-monitor-service/src ./src
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3000"]
