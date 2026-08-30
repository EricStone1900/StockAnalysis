"""执行已登记父版本的单批状态探针。"""

import asyncio
import os
from datetime import UTC, datetime

import main
from market_data.importing import BaoStockStatusEnrichmentCommand
from market_data.repository import PostgresSourceLineageRepository


async def run() -> None:
    version_id = os.environ["STATUS_PROBE_VERSION_ID"]
    print("probe: loading parent version", flush=True)
    parent = PostgresSourceLineageRepository(os.environ["MARKET_DATA_DATABASE_URL"]).get_data_version(version_id)
    if parent is None:
        raise RuntimeError(f"DataVersion not found: {version_id}")
    print("probe: parent version loaded", flush=True)
    batch_size = int(os.getenv("STATUS_PROBE_BATCH_SIZE", "1"))
    batch_ordinal = int(os.getenv("STATUS_PROBE_BATCH_ORDINAL", "0"))
    idempotency_key = os.getenv(
        "STATUS_PROBE_IDEMPOTENCY_KEY", f"status-enrichment-batch-{batch_ordinal:04d}"
    )
    # 增强版本的可用时间不得早于父版本；父版本可能按计划发布时间登记在未来。
    available_at = max(datetime.now(UTC), parent.available_at)
    command = BaoStockStatusEnrichmentCommand(
        parent_version=parent,
        policy_version=os.getenv("STATUS_PROBE_POLICY_VERSION", "v1-close-gap-fast"),
        policy_document_uri="docs/development-roadmap-v2/02-market-data-service/07-baostock-status-st-enrichment.md",
        available_at=available_at,
        probe=True,
        batch_size=batch_size,
        batch_ordinal=batch_ordinal,
        exclude_bse=True,
        exclude_non_equity=True,
        mode=os.getenv("STATUS_ENRICHMENT_MODE", "fast"),
        fast_mode_acknowledged=os.getenv("STATUS_FAST_MODE_ACKNOWLEDGED", "false").lower() == "true",
        fast_mode_approval_ref=os.getenv("STATUS_FAST_MODE_APPROVAL_REF"),
        fast_mode_operator=os.getenv("STATUS_FAST_MODE_OPERATOR"),
    )
    print("probe: starting status enrichment", flush=True)
    result = await main.baostock_status_import_service.import_status(command, idempotency_key)
    print("probe: status enrichment completed", flush=True)
    print(result.model_dump_json())


if __name__ == "__main__":
    asyncio.run(run())
