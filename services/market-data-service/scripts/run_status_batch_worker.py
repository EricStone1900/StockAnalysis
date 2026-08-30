"""受控执行 BaoStock 状态批次；默认只执行一个批次。"""

import asyncio
import os
from datetime import UTC, datetime

import main
from market_data.importing import BaoStockStatusEnrichmentCommand
from market_data.repository import PostgresSourceLineageRepository


async def run() -> None:
    if os.getenv("STATUS_BULK_EXECUTION_ENABLED", "false").lower() != "true":
        raise RuntimeError(
            "status bulk execution is paused; use the stage03 on-read close-gap policy or explicitly set "
            "STATUS_BULK_EXECUTION_ENABLED=true"
        )
    version_id = os.environ["STATUS_PROBE_VERSION_ID"]
    database_url = os.environ["MARKET_DATA_DATABASE_URL"]
    policy_version = os.getenv("STATUS_PROBE_POLICY_VERSION", "v1-close-gap-fast")
    batch_size = int(os.getenv("STATUS_PROBE_BATCH_SIZE", "100"))
    start_ordinal = int(os.getenv("STATUS_WORKER_START_ORDINAL", "0"))
    max_batches = int(os.getenv("STATUS_WORKER_MAX_BATCHES", "1"))
    mode = os.getenv("STATUS_ENRICHMENT_MODE", "fast")
    fast_acknowledged = os.getenv("STATUS_FAST_MODE_ACKNOWLEDGED", "false").lower() == "true"
    fast_approval_ref = os.getenv("STATUS_FAST_MODE_APPROVAL_REF")
    fast_operator = os.getenv("STATUS_FAST_MODE_OPERATOR")
    parent = PostgresSourceLineageRepository(database_url).get_data_version(version_id)
    if parent is None:
        raise RuntimeError(f"DataVersion not found: {version_id}")
    available_at = max(datetime.now(UTC), parent.available_at)
    succeeded = 0
    failed = 0
    for ordinal in range(start_ordinal, start_ordinal + max_batches):
        key = f"status-enrichment-worker-{policy_version}-{ordinal:06d}"
        command = BaoStockStatusEnrichmentCommand(
            parent_version=parent,
            policy_version=policy_version,
            policy_document_uri="docs/development-roadmap-v2/02-market-data-service/07-baostock-status-st-enrichment.md",
            available_at=available_at,
            probe=True,
            batch_size=batch_size,
            batch_ordinal=ordinal,
            exclude_bse=True,
            exclude_non_equity=True,
            mode=mode,
            fast_mode_acknowledged=fast_acknowledged,
            fast_mode_approval_ref=fast_approval_ref,
            fast_mode_operator=fast_operator,
        )
        try:
            result = await main.baostock_status_import_service.import_status(command, key)
        except (RuntimeError, ValueError, OSError) as error:  # 单批失败已由服务写入 FAILED，后台继续推进
            failed += 1
            print(f"batch={ordinal} state=FAILED error={type(error).__name__}:{error}", flush=True)
            continue
        succeeded += 1
        print(
            f"batch={ordinal} state=SUCCEEDED facts={len(result.facts)} "
            f"reconciliations={len(result.reconciliations)} quality={result.quality_status}",
            flush=True,
        )
    print(f"worker_summary succeeded={succeeded} failed={failed}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())
