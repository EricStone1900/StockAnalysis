"""为已存在的 DataVersion 生成并登记 close-gap-index。"""

import argparse
import os

from market_data.qlib_quality import build_close_gap_index, close_gap_index_bytes
from market_data.repository import PostgresSourceLineageRepository
from market_data.storage import ArtifactStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version_id")
    args = parser.parse_args()
    database_url = os.environ["MARKET_DATA_DATABASE_URL"]
    store = ArtifactStore(
        os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        os.getenv("MINIO_SECRET_KEY", "local-minio-password"),
        os.getenv("ARTIFACT_BUCKET", "artifacts"),
    )
    repository = PostgresSourceLineageRepository(database_url)
    version = repository.get_data_version(args.version_id)
    if version is None:
        raise SystemExit(f"DataVersion not found: {args.version_id}")
    if version.close_gap_index_uri and version.close_gap_index_hash:
        print(version.close_gap_index_uri)
        return
    prefix = f"minio://{store.bucket}/"
    if not version.artifact_uri.startswith(prefix):
        raise SystemExit("parent Artifact URI does not belong to configured bucket")
    archive = store.get_verified(version.artifact_uri.removeprefix(prefix), version.artifact_hash)
    index = build_close_gap_index(archive, version.artifact_hash)
    key = f"quality/investment_data/{version.source_release_tag or version.version_id}/{version.artifact_hash}/close-gap-index.json"
    index_hash = store.put_immutable(key, close_gap_index_bytes(index))
    index_uri = f"minio://{store.bucket}/{key}"
    repository.attach_close_gap_index(version.version_id, index_uri, index_hash)
    print(index_uri)


if __name__ == "__main__":
    main()
