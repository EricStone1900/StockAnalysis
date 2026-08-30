import asyncio
import os
from pathlib import Path
from time import sleep

import boto3
import nats
import psycopg
from nats.js.api import RetentionPolicy, StorageType, StreamConfig


def environment_secret(name: str, default: str) -> str:
    secret_file = os.getenv(f"{name}_FILE")
    if secret_file:
        with open(secret_file) as file:
            return file.read().strip()
    return os.getenv(name, default)


def ensure_bucket() -> None:
    client = boto3.client("s3", endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"), aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"), aws_secret_access_key=environment_secret("MINIO_SECRET_KEY", "local-minio-password"))
    bucket = os.getenv("ARTIFACT_BUCKET", "artifacts")
    if bucket not in [item["Name"] for item in client.list_buckets()["Buckets"]]:
        client.create_bucket(Bucket=bucket)


def apply_migrations() -> None:
    database_url = os.getenv("MARKET_DATA_DATABASE_URL")
    if not database_url:
        return
    migration_dir = Path(__file__).parents[1] / "migrations"
    with psycopg.connect(database_url, autocommit=True) as connection:
        for migration in sorted(migration_dir.glob("[0-9][0-9][0-9]_*.sql")):
            connection.execute(migration.read_text())


async def ensure_streams() -> None:
    client = await nats.connect(os.getenv("NATS_URL", "nats://localhost:4222"))
    jetstream = client.jetstream()
    for name, subjects in [("STOCK_FACTS", ["stock.market-data.>"]), ("STOCK_SIGNALS", ["stock.signals.>"]), ("STOCK_OPERATIONS", ["stock.operations.>"]), ("STOCK_DLQ", ["stock.dlq.>"])]:
        try:
            await jetstream.add_stream(StreamConfig(name=name, subjects=subjects, retention=RetentionPolicy.LIMITS, storage=StorageType.FILE))
        except Exception as error:
            if "stream name already in use" not in str(error):
                raise
    await client.drain()


def bootstrap(retries: int = 20) -> None:
    for attempt in range(retries):
        try:
            apply_migrations()
            ensure_bucket()
            asyncio.run(ensure_streams())
            return
        except Exception:
            if attempt == retries - 1:
                raise
            sleep(1)


if __name__ == "__main__":
    bootstrap()
