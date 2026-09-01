"""Factor Registry 的领域模型；计算实现与Qlib表达式仍留在 Adapter 层。"""

from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, field_validator

from quant_research.domain import ArtifactRef, DataQualityStatus, ResearchRunManifest


class FactorCategory(StrEnum):
    PRICE_MOMENTUM = "PRICE_MOMENTUM"
    VOLATILITY = "VOLATILITY"
    LIQUIDITY = "LIQUIDITY"
    VALUE = "VALUE"
    QUALITY = "QUALITY"


class FactorStatus(StrEnum):
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class FactorDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor_id: str = Field(min_length=1)
    category: FactorCategory
    required_fields: tuple[str, ...]
    lookback_trading_days: int = Field(ge=1)
    requires_valuation_pit: bool = False
    requires_financial_revision_pit: bool = False


class FactorVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    expression_hash: str = Field(min_length=64, max_length=64)
    data_version_id: str = Field(min_length=1)
    transform_version: str = Field(min_length=1)
    status: FactorStatus = FactorStatus.DRAFT
    approval_reference: str | None = None

    @field_validator("expression_hash")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if any(character not in "0123456789abcdef" for character in value):
            raise ValueError("expression_hash must be a lowercase hexadecimal digest")
        return value


class FactorSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    factor_set_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    factors: tuple[FactorVersion, ...]
    canonical_content_hash: str


class FactorPromotionError(ValueError):
    """因子未满足数据或人工准入门禁。"""


class CandidateFactorEvidence(BaseModel):
    """价格因子从 DRAFT 进入研究候选时必须保留的可复核证据。"""

    model_config = ConfigDict(frozen=True)

    run_manifest: ResearchRunManifest
    run_manifest_artifact: ArtifactRef
    matrix_factor_ids: tuple[str, ...] = Field(min_length=1)


class CandidateFactorRecord(BaseModel):
    """不可变候选准入记录；不是生产 FactorSet 的成员资格。"""

    model_config = ConfigDict(frozen=True)

    factor: FactorVersion
    data_version_id: str
    factor_matrix_artifact: ArtifactRef
    run_manifest_artifact: ArtifactRef
    factor_matrix_canonical_content_hash: str = Field(min_length=64, max_length=64)
    transform_version: str = Field(min_length=1)
    input_quality_status: DataQualityStatus
    eligibility: str = "RESEARCH_ONLY"


_PRICE_FACTOR_CATEGORIES = frozenset(
    {
        FactorCategory.PRICE_MOMENTUM,
        FactorCategory.VOLATILITY,
        FactorCategory.LIQUIDITY,
    }
)
_LOCAL_SMOKE_APPROVAL_REFERENCES = frozenset({"stage03-local-smoke"})


def promote_to_candidate(
    definition: FactorDefinition,
    version: FactorVersion,
    *,
    price_data_ready: bool,
    valuation_pit_ready: bool,
    financial_revision_pit_ready: bool,
    approval_reference: str,
) -> FactorVersion:
    if version.factor_id != definition.factor_id:
        raise FactorPromotionError("factor definition and version do not match")
    if version.status is not FactorStatus.DRAFT:
        raise FactorPromotionError("only DRAFT factor versions can become CANDIDATE")
    if not price_data_ready:
        raise FactorPromotionError("price data quality gate is not satisfied")
    if definition.requires_valuation_pit and not valuation_pit_ready:
        raise FactorPromotionError("valuation PIT gate is not satisfied")
    if definition.requires_financial_revision_pit and not financial_revision_pit_ready:
        raise FactorPromotionError("financial revision PIT gate is not satisfied")
    if not approval_reference:
        raise FactorPromotionError("candidate promotion requires an approval reference")
    return version.model_copy(update={"status": FactorStatus.CANDIDATE, "approval_reference": approval_reference})


def admit_price_factor_candidate(
    definition: FactorDefinition,
    version: FactorVersion,
    evidence: CandidateFactorEvidence,
    *,
    approval_reference: str,
) -> CandidateFactorRecord:
    """以已发布矩阵和运行清单为证据，准入首版价格类研究候选。

    该函数有意不把 ``WARN`` 提升为 ``PASS``，也不创建 ``ACTIVE`` 因子；正式生产
    准入仍需后续独立的质量、回测和审批门禁。
    """
    manifest = evidence.run_manifest
    if definition.category not in _PRICE_FACTOR_CATEGORIES:
        raise FactorPromotionError("only price, volatility, and liquidity factors use this candidate gate")
    if definition.requires_valuation_pit or definition.requires_financial_revision_pit:
        raise FactorPromotionError("price factor candidate cannot require valuation or financial PIT data")
    if version.factor_id != definition.factor_id:
        raise FactorPromotionError("factor definition and version do not match")
    if version.status is not FactorStatus.DRAFT:
        raise FactorPromotionError("only DRAFT factor versions can become CANDIDATE")
    if version.factor_id not in evidence.matrix_factor_ids:
        raise FactorPromotionError("published factor matrix does not contain the factor")
    if manifest.data_version_id != version.data_version_id:
        raise FactorPromotionError("run manifest and factor version data versions do not match")
    if manifest.factor_transform_version != version.transform_version:
        raise FactorPromotionError("run manifest and factor version transform versions do not match")
    if manifest.factor_matrix_artifact is None or manifest.factor_matrix_canonical_content_hash is None:
        raise FactorPromotionError("candidate promotion requires a published factor matrix and canonical hash")
    if manifest.quality_status is DataQualityStatus.FAIL:
        raise FactorPromotionError("FAIL input quality cannot become a candidate")
    if manifest.snapshot_eligibility != "CANDIDATE_ONLY":
        raise FactorPromotionError("price factor evidence must retain CANDIDATE_ONLY eligibility")
    if not approval_reference or approval_reference in _LOCAL_SMOKE_APPROVAL_REFERENCES:
        raise FactorPromotionError("candidate promotion requires a non-smoke approval reference")

    candidate = version.model_copy(update={"status": FactorStatus.CANDIDATE, "approval_reference": approval_reference})
    return CandidateFactorRecord(
        factor=candidate,
        data_version_id=manifest.data_version_id,
        factor_matrix_artifact=manifest.factor_matrix_artifact,
        run_manifest_artifact=evidence.run_manifest_artifact,
        factor_matrix_canonical_content_hash=manifest.factor_matrix_canonical_content_hash,
        transform_version=manifest.factor_transform_version,
        input_quality_status=manifest.quality_status,
    )


def build_active_factor_set(
    factor_set_id: str,
    version: str,
    factors: tuple[FactorVersion, ...],
) -> FactorSet:
    if not factors:
        raise FactorPromotionError("an active factor set requires at least one factor")
    if any(factor.status is not FactorStatus.ACTIVE for factor in factors):
        raise FactorPromotionError("only ACTIVE factors may enter a production factor set")
    ordered = tuple(sorted(factors, key=lambda item: (item.factor_id, item.version)))
    payload = {
        "factorSetId": factor_set_id,
        "version": version,
        "factors": [factor.model_dump(mode="json") for factor in ordered],
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return FactorSet(
        factor_set_id=factor_set_id,
        version=version,
        factors=ordered,
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )
