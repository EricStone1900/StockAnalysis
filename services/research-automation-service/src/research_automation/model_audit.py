"""模型调用审计记录，供应商适配器只能写审计数据，不能改变领域契约。"""

from __future__ import annotations

from .artifacts import ModelCallAudit


class ModelCallAuditStore:
    def __init__(self) -> None:
        self._records: dict[str, ModelCallAudit] = {}

    def record(self, call_id: str, audit: ModelCallAudit) -> None:
        existing = self._records.get(call_id)
        if existing is not None and existing != audit:
            raise ValueError("model call id already contains different audit")
        self._records[call_id] = audit

    def get(self, call_id: str) -> ModelCallAudit | None:
        return self._records.get(call_id)
