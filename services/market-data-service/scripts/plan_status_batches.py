"""登记 BaoStock 状态补充的正式批次计划，不执行供应商请求。"""

import os

from market_data.baostock_status import security_id_from_qlib
from market_data.qlib_quality import parse_close_gap_index
from market_data.repository import (
    PostgresSourceLineageRepository,
    PostgresStatusBatchRepository,
    SourcePolicy,
)
from market_data.status_batches import plan_status_batches
from market_data.storage import ArtifactStore
from market_data.trading_status import StatusEnrichmentMode
from market_data.universe import is_stage03_cn_a_equity


def main() -> None:
    database_url = os.environ["MARKET_DATA_DATABASE_URL"]
    version_id = os.environ["STATUS_PROBE_VERSION_ID"]
    policy_version = os.getenv("STATUS_PROBE_POLICY_VERSION", "v1-close-gap-fast")
    mode = StatusEnrichmentMode(os.getenv("STATUS_ENRICHMENT_MODE", "fast"))
    batch_size = int(os.getenv("STATUS_PROBE_BATCH_SIZE", "100"))
    lineage = PostgresSourceLineageRepository(database_url)
    parent = lineage.get_data_version(version_id)
    if parent is None:
        raise RuntimeError(f"DataVersion not found: {version_id}")
    if not parent.close_gap_index_uri or not parent.close_gap_index_hash:
        raise RuntimeError("parent DataVersion has no close-gap index")
    with open(os.getenv("MINIO_SECRET_KEY_FILE", "/run/secrets/minio_root_password")) as secret_file:
        secret_key = secret_file.read().strip()
    store = ArtifactStore(
        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=secret_key,
        bucket=os.getenv("ARTIFACT_BUCKET", "artifacts"),
    )
    prefix = f"minio://{store.bucket}/"
    key = parent.close_gap_index_uri.removeprefix(prefix)
    index = parse_close_gap_index(store.get_verified(key, parent.close_gap_index_hash), parent.artifact_hash)
    gaps = [
        (security_id_from_qlib(item.symbol), item.trading_day)
        for item in index.gaps
        if is_stage03_cn_a_equity(security_id_from_qlib(item.symbol))
    ]
    batches = plan_status_batches(
        [type("Gap", (), {"security_id": security_id, "trading_day": day})() for security_id, day in gaps],
        batch_size,
        identity_namespace=f"{parent.version_id}:{policy_version}" if mode is StatusEnrichmentMode.FAST else "",
    )
    lineage.ensure_policy(
        SourcePolicy(
            policy_version=policy_version,
            primary_source="baostock" if mode is StatusEnrichmentMode.EXACT else "business_assumption",
            policy_document_uri="docs/development-roadmap-v2/02-market-data-service/07-baostock-status-st-enrichment.md",
        )
    )
    PostgresStatusBatchRepository(database_url).ensure_batches(parent.version_id, policy_version, batches)
    print(f"planned_batches={len(batches)}")
    print(f"eligible_gaps={len(gaps)}")
    print(f"batch_size={batch_size}")
    print(f"policy_version={policy_version}")


if __name__ == "__main__":
    main()
