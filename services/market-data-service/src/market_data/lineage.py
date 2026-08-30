from enum import StrEnum

from pydantic import BaseModel, Field


class ProvenanceRole(StrEnum):
    PRIMARY = "PRIMARY"
    SUPPLEMENT = "SUPPLEMENT"
    VERIFIED = "VERIFIED"


class FieldProvenance(BaseModel):
    """描述标准字段的来源，避免补充数据覆盖时丢失证据。"""

    field_name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    raw_artifact_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_version: str = Field(min_length=1)
    source_policy_version: str = Field(min_length=1)
    role: ProvenanceRole
