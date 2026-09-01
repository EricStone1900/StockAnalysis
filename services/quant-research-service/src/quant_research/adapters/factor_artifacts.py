"""因子矩阵的规范序列化与不可变Artifact写入。"""

from __future__ import annotations

import io
import json
import re
from datetime import date
from decimal import Decimal
from hashlib import sha256
from typing import Protocol

import pyarrow as pa
import pyarrow.parquet as pq
from boto3.session import Session
from pydantic import BaseModel, ConfigDict

from quant_research.adapters.factor_engine import (
    FactorObservation,
    PriceFactorMatrix,
    canonical_price_factor_matrix_hash,
)
from quant_research.adapters.qlib import ArtifactIntegrityError, VerifiedArtifactReader
from quant_research.domain import ArtifactRef, ResearchRunManifest
from quant_research.factors import CandidateFactorEvidence

_SAFE_KEY_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


class ImmutableArtifactWriter(Protocol):
    def put_immutable(self, key: str, content: bytes) -> str: ...


class PublishedFactorArtifacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    matrix_artifact: ArtifactRef
    manifest_artifact: ArtifactRef
    manifest: ResearchRunManifest


class S3ImmutableArtifactWriter:
    """MinIO/S3不可变写入端口；同键内容不同即拒绝覆盖。"""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str) -> None:
        self.bucket = bucket
        self._client = Session().client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def put_immutable(self, key: str, content: bytes) -> str:
        digest = sha256(content).hexdigest()
        try:
            existing = self._client.head_object(Bucket=self.bucket, Key=key)
        except Exception as error:
            response = getattr(error, "response", None)
            code = response.get("Error", {}).get("Code") if isinstance(response, dict) else None
            if code not in {"404", "NoSuchKey", "NotFound"}:
                raise
        else:
            if existing.get("Metadata", {}).get("sha256") != digest:
                raise ValueError("immutable artifact key already contains different content")
            return digest
        self._client.put_object(Bucket=self.bucket, Key=key, Body=content, Metadata={"sha256": digest})
        return digest


class FactorArtifactPublisher:
    def __init__(self, writer: ImmutableArtifactWriter, artifact_uri_prefix: str) -> None:
        self._writer = writer
        self._artifact_uri_prefix = artifact_uri_prefix.rstrip("/")

    def publish(
        self,
        matrix: PriceFactorMatrix,
        manifest: ResearchRunManifest,
        transform_version: str = "raw-price-v1",
    ) -> PublishedFactorArtifacts:
        _validate_segment(manifest.run_id)
        _validate_segment(matrix.data_version_id)
        _validate_segment(transform_version)
        parquet_content = _matrix_parquet_bytes(matrix)
        parquet_hash = sha256(parquet_content).hexdigest()
        base_key = f"quant-research/factors/{matrix.data_version_id}/{matrix.canonical_content_hash}"
        matrix_key = f"{base_key}/{parquet_hash}.parquet"
        stored_matrix_hash = self._writer.put_immutable(matrix_key, parquet_content)
        matrix_artifact = ArtifactRef(
            uri=f"{self._artifact_uri_prefix}/{matrix_key}",
            sha256=stored_matrix_hash,
        )
        published_manifest = manifest.model_copy(
            update={
                "factor_matrix_artifact": matrix_artifact,
                "factor_matrix_canonical_content_hash": matrix.canonical_content_hash,
                "factor_transform_version": transform_version,
            }
        )
        manifest_content = _canonical_json_bytes(published_manifest.model_dump(mode="json", exclude_none=True))
        manifest_hash = sha256(manifest_content).hexdigest()
        manifest_key = f"quant-research/runs/{manifest.run_id}/{matrix.canonical_content_hash}/{manifest_hash}.json"
        stored_manifest_hash = self._writer.put_immutable(manifest_key, manifest_content)
        manifest_artifact = ArtifactRef(
            uri=f"{self._artifact_uri_prefix}/{manifest_key}",
            sha256=stored_manifest_hash,
        )
        return PublishedFactorArtifacts(
            matrix_artifact=matrix_artifact,
            manifest_artifact=manifest_artifact,
            manifest=published_manifest,
        )


class PublishedFactorEvidenceReader:
    """从已校验的Artifact重建候选准入证据，禁止调用方伪造矩阵元数据。"""

    def __init__(self, reader: VerifiedArtifactReader) -> None:
        self._reader = reader

    def load_candidate_evidence(self, manifest_artifact: ArtifactRef) -> CandidateFactorEvidence:
        manifest_content = self._reader.get_verified(manifest_artifact)
        try:
            manifest = ResearchRunManifest.model_validate_json(manifest_content)
        except ValueError as error:
            raise ArtifactIntegrityError("factor run manifest is not valid JSON") from error
        if manifest.factor_matrix_artifact is None or manifest.factor_matrix_canonical_content_hash is None:
            raise ArtifactIntegrityError("factor run manifest does not reference a published matrix")
        matrix_content = self._reader.get_verified(manifest.factor_matrix_artifact)
        matrix = _read_price_factor_matrix(matrix_content, manifest.data_version_id)
        if matrix.canonical_content_hash != manifest.factor_matrix_canonical_content_hash:
            raise ArtifactIntegrityError("factor matrix canonical hash does not match the run manifest")
        return CandidateFactorEvidence(
            run_manifest=manifest,
            run_manifest_artifact=manifest_artifact,
            matrix_factor_ids=tuple(sorted({row.factor_id for row in matrix.observations})),
        )


def _matrix_parquet_bytes(matrix: PriceFactorMatrix) -> bytes:
    rows = sorted(matrix.observations, key=lambda row: (row.security_id, row.trading_day, row.factor_id))
    table = pa.table(
        {
            "security_id": pa.array([row.security_id for row in rows], type=pa.string()),
            "trading_day": pa.array([row.trading_day for row in rows], type=pa.date32()),
            "factor_id": pa.array([row.factor_id for row in rows], type=pa.string()),
            "value": pa.array([row.value for row in rows], type=pa.decimal128(24, 8)),
            "data_version_id": pa.array([matrix.data_version_id for _ in rows], type=pa.string()),
        }
    )
    output = io.BytesIO()
    pq.write_table(table, output, compression="zstd", use_dictionary=False, write_statistics=False)
    return output.getvalue()


def _read_price_factor_matrix(content: bytes, expected_data_version_id: str) -> PriceFactorMatrix:
    try:
        table = pq.read_table(io.BytesIO(content))
    except Exception as error:
        raise ArtifactIntegrityError("factor matrix is not a readable Parquet artifact") from error
    required_columns = ("security_id", "trading_day", "factor_id", "value", "data_version_id")
    if tuple(table.column_names) != required_columns or table.num_rows == 0:
        raise ArtifactIntegrityError("factor matrix has an unsupported schema or is empty")
    rows = table.to_pylist()
    try:
        observations = tuple(
            FactorObservation(
                security_id=str(row["security_id"]),
                trading_day=_as_date(row["trading_day"]),
                factor_id=str(row["factor_id"]),
                value=Decimal(str(row["value"])),
            )
            for row in rows
        )
        data_version_ids = {str(row["data_version_id"]) for row in rows}
    except (KeyError, TypeError, ValueError) as error:
        raise ArtifactIntegrityError("factor matrix contains an invalid value") from error
    if data_version_ids != {expected_data_version_id}:
        raise ArtifactIntegrityError("factor matrix does not belong to the run manifest DataVersion")
    ordered = tuple(sorted(observations, key=lambda row: (row.security_id, row.trading_day, row.factor_id)))
    if observations != ordered:
        raise ArtifactIntegrityError("factor matrix rows are not stably ordered")
    return PriceFactorMatrix(
        data_version_id=expected_data_version_id,
        observations=observations,
        canonical_content_hash=canonical_price_factor_matrix_hash(expected_data_version_id, observations),
    )


def _as_date(value: object) -> date:
    if isinstance(value, date):
        return value
    raise ValueError("trading_day must be a date")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _validate_segment(value: str) -> None:
    if not _SAFE_KEY_SEGMENT.fullmatch(value):
        raise ValueError("artifact key segment contains unsupported characters")
