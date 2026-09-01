"""阶段03的稳定领域契约；不依赖 Qlib 或外部数据供应商。"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from enum import StrEnum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DataQualityStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class CloseGapHandlingMode(StrEnum):
    ASSUME_SUSPENSION_ON_READ = "assume_suspension_on_read"


class ArtifactRef(BaseModel):
    """跨服务传递的不可变对象引用；内容只由拥有服务读取。"""

    model_config = ConfigDict(frozen=True)

    uri: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if any(character not in "0123456789abcdef" for character in value):
            raise ValueError("sha256 must be a lowercase hexadecimal digest")
        return value


class MarketDataVersionRef(BaseModel):
    """market-data-service 发布的只读 DataVersion 输入。"""

    model_config = ConfigDict(frozen=True)

    version_id: str = Field(min_length=1)
    artifact: ArtifactRef
    close_gap_index: ArtifactRef
    quality_status: DataQualityStatus
    source_release_tag: str = Field(min_length=1)
    source_policy_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def reject_failed_data_version(self) -> MarketDataVersionRef:
        if self.quality_status is DataQualityStatus.FAIL:
            raise ValueError("FAIL DataVersion cannot be used for research")
        return self


class CloseGap(BaseModel):
    """原始 Qlib 收盘价为空的股票日；不携带或修改价格。"""

    model_config = ConfigDict(frozen=True)

    security_id: str = Field(min_length=1)
    trading_day: date


class CloseGapHandlingPolicy(BaseModel):
    """版本化且经审批的按需空洞解释策略。"""

    model_config = ConfigDict(frozen=True)

    policy_version: str = Field(min_length=1)
    artifact: ArtifactRef
    mode: CloseGapHandlingMode = CloseGapHandlingMode.ASSUME_SUSPENSION_ON_READ
    applicable_universe_version: str = Field(min_length=1)
    bse_exclusion_enabled: bool = True
    approval_reference: str = Field(min_length=1)
    acknowledged_by: str = Field(min_length=1)
    approved_at: datetime

    @field_validator("approved_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("approved_at must use UTC")
        return value


class SuspensionMaskEntry(BaseModel):
    """对单个空洞的确定性解释，明确不是供应商确认事实。"""

    model_config = ConfigDict(frozen=True)

    security_id: str
    trading_day: date
    status: str = "SUSPENSION_ASSUMED"
    reason: str = "close_gap_policy_assume_suspension_on_read"


class CloseGapResolution(BaseModel):
    """被 Run Manifest 与输出 Artifact 共同引用的不可变解释结果。"""

    model_config = ConfigDict(frozen=True)

    data_version: MarketDataVersionRef
    policy: CloseGapHandlingPolicy
    entries: tuple[SuspensionMaskEntry, ...]
    quality_status: DataQualityStatus = DataQualityStatus.WARN
    canonical_content_hash: str
    generated_at: datetime

    @model_validator(mode="after")
    def validate_warning_quality(self) -> CloseGapResolution:
        if self.quality_status is not DataQualityStatus.WARN:
            raise ValueError("assume_suspension_on_read must retain WARN quality")
        return self


class ResearchRunManifest(BaseModel):
    """最小研究运行清单；WARN 输入不能被伪装成正式 READY 输出。"""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    data_version_id: str
    data_artifact: ArtifactRef
    close_gap_index: ArtifactRef
    policy_artifact: ArtifactRef
    policy_version: str
    suspension_mask_hash: str
    factor_matrix_artifact: ArtifactRef | None = None
    factor_matrix_canonical_content_hash: str | None = None
    factor_transform_version: str | None = None
    quality_status: DataQualityStatus = DataQualityStatus.WARN
    snapshot_eligibility: str = "CANDIDATE_ONLY"
    generated_at: datetime

    @model_validator(mode="after")
    def reject_ready_publication(self) -> ResearchRunManifest:
        if self.quality_status is not DataQualityStatus.WARN:
            raise ValueError("on-read close-gap handling must retain WARN quality")
        if self.snapshot_eligibility != "CANDIDATE_ONLY":
            raise ValueError("on-read close-gap handling cannot publish a READY snapshot")
        artifact_fields = (
            self.factor_matrix_artifact,
            self.factor_matrix_canonical_content_hash,
            self.factor_transform_version,
        )
        if any(field is None for field in artifact_fields) and any(field is not None for field in artifact_fields):
            raise ValueError("factor output fields must be populated together")
        return self


def resolve_close_gaps(
    data_version: MarketDataVersionRef,
    policy: CloseGapHandlingPolicy,
    gaps: tuple[CloseGap, ...],
    generated_at: datetime,
) -> CloseGapResolution:
    """生成稳定掩码，不读取、填充或替换任何 Qlib 价格。"""
    if generated_at.tzinfo is None or generated_at.utcoffset() != UTC.utcoffset(generated_at):
        raise ValueError("generated_at must use UTC")
    entries = tuple(
        SuspensionMaskEntry(security_id=gap.security_id, trading_day=gap.trading_day)
        for gap in sorted(gaps, key=lambda item: (item.security_id, item.trading_day))
        if not policy.bse_exclusion_enabled or not _is_bse_security(gap.security_id)
    )
    canonical_content_hash = _canonical_hash(data_version, policy, entries)
    return CloseGapResolution(
        data_version=data_version,
        policy=policy,
        entries=entries,
        canonical_content_hash=canonical_content_hash,
        generated_at=generated_at,
    )


def build_run_manifest(run_id: str, resolution: CloseGapResolution) -> ResearchRunManifest:
    return ResearchRunManifest(
        run_id=run_id,
        data_version_id=resolution.data_version.version_id,
        data_artifact=resolution.data_version.artifact,
        close_gap_index=resolution.data_version.close_gap_index,
        policy_artifact=resolution.policy.artifact,
        policy_version=resolution.policy.policy_version,
        suspension_mask_hash=resolution.canonical_content_hash,
        generated_at=resolution.generated_at,
    )
def _canonical_hash(
    data_version: MarketDataVersionRef,
    policy: CloseGapHandlingPolicy,
    entries: tuple[SuspensionMaskEntry, ...],
) -> str:
    payload = {
        "dataVersionId": data_version.version_id,
        "dataArtifactHash": data_version.artifact.sha256,
        "closeGapIndexHash": data_version.close_gap_index.sha256,
        "policyArtifactHash": policy.artifact.sha256,
        "policyVersion": policy.policy_version,
        "mode": policy.mode.value,
        "universeVersion": policy.applicable_universe_version,
        "bseExclusionEnabled": policy.bse_exclusion_enabled,
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _is_bse_security(security_id: str) -> bool:
    normalized = security_id.lower()
    return normalized.startswith("bj") or normalized.endswith(".bj")
