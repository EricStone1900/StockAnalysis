#!/usr/bin/env python3
"""只读验证阶段02 DataVersion Artifact 能被阶段03 Qlib加载。"""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

from quant_research.adapters.factor_artifacts import (
    FactorArtifactPublisher,
    S3ImmutableArtifactWriter,
)
from quant_research.adapters.qlib import QlibCloseGapIndexAdapter
from quant_research.adapters.qlib_dataset import (
    QlibDatasetMaterializer,
    S3VerifiedArtifactReader,
    initialize_qlib_provider,
)
from quant_research.adapters.qlib_features import QlibPriceFeatureReader
from quant_research.application_price_factors import QlibMaskedPriceFactorService
from quant_research.domain import (
    ArtifactRef,
    CloseGapHandlingPolicy,
    DataQualityStatus,
    MarketDataVersionRef,
    resolve_close_gaps,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-data-url", default=os.getenv("MARKET_DATA_API_URL", "http://localhost:3000"))
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--factor-instrument", default="sh600000")
    parser.add_argument("--factor-window-days", type=int, default=30)
    parser.add_argument("--publish-factor-artifacts", action="store_true")
    arguments = parser.parse_args()
    payload = _latest_data_version(arguments.market_data_url)
    data_version = _to_reference(payload)
    secret_key = _environment_secret("MINIO_SECRET_KEY", "MINIO_SECRET_KEY_FILE")
    reader = S3VerifiedArtifactReader(
        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=secret_key,
        bucket=os.getenv("ARTIFACT_BUCKET", "artifacts"),
    )
    artifact_writer = None
    if arguments.publish_factor_artifacts:
        artifact_writer = S3ImmutableArtifactWriter(
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=secret_key,
            bucket=os.getenv("ARTIFACT_BUCKET", "artifacts"),
        )
    provider_root = QlibDatasetMaterializer(reader, arguments.cache_root).materialize(data_version)
    initialize_qlib_provider(provider_root)
    from qlib.data import D

    calendar = D.calendar(freq="day")
    if len(calendar) == 0:
        raise RuntimeError("Qlib provider contains no daily calendar")
    if arguments.factor_window_days < 3:
        raise ValueError("factor window must contain at least three trading days")
    gaps = QlibCloseGapIndexAdapter(reader).load_gaps(data_version)
    smoke_gap = next((gap for gap in gaps if not gap.security_id.lower().startswith("bj")), None)
    if smoke_gap is None:
        raise RuntimeError("close-gap index contains no non-BSE gap for smoke verification")
    raw_close = D.features(
        [smoke_gap.security_id],
        ["$close"],
        start_time=smoke_gap.trading_day.isoformat(),
        end_time=smoke_gap.trading_day.isoformat(),
    )
    if raw_close.empty or not math.isnan(float(raw_close.iloc[0, 0])):
        raise RuntimeError("Qlib close-gap smoke sample was not NaN in the immutable source")
    policy = _smoke_policy(artifact_writer, os.getenv("ARTIFACT_BUCKET", "artifacts"))
    resolution = resolve_close_gaps(
        data_version,
        policy,
        gaps,
        datetime(2026, 8, 30, tzinfo=UTC),
    )
    if not any(
        entry.security_id == smoke_gap.security_id and entry.trading_day == smoke_gap.trading_day
        for entry in resolution.entries
    ):
        raise RuntimeError("close-gap policy did not produce the expected suspension mask")
    factor_end = _calendar_date(calendar[-1])
    factor_start = _calendar_date(calendar[max(0, len(calendar) - arguments.factor_window_days)])
    matrix, _, manifest = QlibMaskedPriceFactorService(
        QlibPriceFeatureReader(),
        QlibCloseGapIndexAdapter(reader),
    ).calculate(
        run_id="stage03-real-price-factor-smoke",
        data_version=data_version,
        policy=policy,
        instruments=(arguments.factor_instrument,),
        start_date=factor_start,
        end_date=factor_end,
        generated_at=datetime(2026, 8, 30, tzinfo=UTC),
        resolution=resolution,
    )
    if not matrix.observations:
        raise RuntimeError("real Qlib price-factor smoke produced no observations")
    mask_keys = {(entry.security_id, entry.trading_day) for entry in resolution.entries}
    if any((row.security_id, row.trading_day) in mask_keys for row in matrix.observations):
        raise RuntimeError("price-factor output includes a close-gap suspension mask day")
    published = None
    if arguments.publish_factor_artifacts:
        if artifact_writer is None:
            raise RuntimeError("artifact writer is required when publishing factor artifacts")
        published = FactorArtifactPublisher(artifact_writer, f"minio://{artifact_writer.bucket}").publish(matrix, manifest)
    print(
        json.dumps(
            {
                "dataVersionId": data_version.version_id,
                "artifactHash": data_version.artifact.sha256,
                "closeGapIndexHash": data_version.close_gap_index.sha256,
                "qualityStatus": data_version.quality_status.value,
                "providerRoot": str(provider_root),
                "calendarDays": len(calendar),
                "closeGapCount": len(gaps),
                "verifiedGap": f"{smoke_gap.security_id}:{smoke_gap.trading_day.isoformat()}",
                "verifiedGapRawClose": "NaN",
                "verifiedGapMaskStatus": "SUSPENSION_ASSUMED",
                "maskHash": resolution.canonical_content_hash,
                "factorInstrument": arguments.factor_instrument,
                "factorStart": factor_start.isoformat(),
                "factorEnd": factor_end.isoformat(),
                "factorObservationCount": len(matrix.observations),
                "factorIds": sorted({row.factor_id for row in matrix.observations}),
                "factorQualityStatus": matrix.quality_status.value,
                "factorSnapshotEligibility": manifest.snapshot_eligibility,
                "publishedFactorMatrixArtifact": None if published is None else published.matrix_artifact.model_dump(),
                "publishedRunManifestArtifact": None if published is None else published.manifest_artifact.model_dump(),
            },
            ensure_ascii=False,
        )
    )


def _latest_data_version(base_url: str) -> dict[str, object]:
    with urlopen(f"{base_url.rstrip('/')}/api/v1/data-versions/latest", timeout=15) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise TypeError("market-data latest DataVersion response is invalid")
    return payload


def _calendar_date(value: object) -> date:
    return date.fromisoformat(str(value)[:10])


def _smoke_policy(writer: S3ImmutableArtifactWriter | None, bucket: str) -> CloseGapHandlingPolicy:
    body = {
        "acknowledgedBy": "stage03-local-smoke",
        "applicableUniverseVersion": "cn-a-main-board-v1",
        "approvalReference": "stage03-local-smoke",
        "approvedAt": "2026-08-30T00:00:00Z",
        "bseExclusionEnabled": True,
        "mode": "assume_suspension_on_read",
        "policyVersion": "v1-assume-suspension-on-read-smoke",
    }
    content = json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    content_hash = sha256(content).hexdigest()
    key = f"quant-research/policies/{body['policyVersion']}/{content_hash}.json"
    artifact = ArtifactRef(uri=f"policy://{key}", sha256=content_hash)
    if writer is not None:
        stored_hash = writer.put_immutable(key, content)
        artifact = ArtifactRef(uri=f"minio://{bucket}/{key}", sha256=stored_hash)
    return CloseGapHandlingPolicy(
        policy_version=str(body["policyVersion"]),
        artifact=artifact,
        applicable_universe_version=str(body["applicableUniverseVersion"]),
        approval_reference=str(body["approvalReference"]),
        acknowledged_by=str(body["acknowledgedBy"]),
        approved_at=datetime.fromisoformat(str(body["approvedAt"])),
    )


def _to_reference(payload: dict[str, object]) -> MarketDataVersionRef:
    required = (
        "version_id",
        "artifact_uri",
        "artifact_hash",
        "close_gap_index_uri",
        "close_gap_index_hash",
        "quality_status",
        "source_release_tag",
        "source_policy_version",
    )
    if any(not isinstance(payload.get(key), str) or not payload[key] for key in required):
        raise RuntimeError("market-data response lacks a complete immutable DataVersion reference")
    return MarketDataVersionRef(
        version_id=str(payload["version_id"]),
        artifact=ArtifactRef(uri=str(payload["artifact_uri"]), sha256=str(payload["artifact_hash"])),
        close_gap_index=ArtifactRef(uri=str(payload["close_gap_index_uri"]), sha256=str(payload["close_gap_index_hash"])),
        quality_status=DataQualityStatus(str(payload["quality_status"])),
        source_release_tag=str(payload["source_release_tag"]),
        source_policy_version=str(payload["source_policy_version"]),
    )


def _environment_secret(name: str, file_name: str) -> str:
    if value := os.getenv(name):
        return value
    if path := os.getenv(file_name):
        return Path(path).read_text(encoding="utf-8").strip()
    raise RuntimeError(f"{name} or {file_name} must be configured")


if __name__ == "__main__":
    main()
