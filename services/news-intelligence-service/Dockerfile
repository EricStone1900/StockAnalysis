FROM python:3.13-slim
WORKDIR /app
COPY services/news-intelligence-service/pyproject.toml .
RUN pip install --no-cache-dir .
COPY services/news-intelligence-service/src ./src
COPY services/news-intelligence-service/migrations ./migrations
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3000"]
