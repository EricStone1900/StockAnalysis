"""PromotionRequest 审计元数据 PostgreSQL 仓储。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .promotion import PromotionRequest
from .reproducibility import manifest_payload


class PostgresPromotionRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def migrate(self, migration: Path) -> None:
        import psycopg

        with psycopg.connect(self._database_url, autocommit=True) as connection:
            connection.execute(migration.read_text(encoding="utf-8"))

    def save_submission(self, request: PromotionRequest, idempotency_key: str) -> None:
        import psycopg

        payload = _request_payload(request)
        encoded = _canonical(payload)
        with psycopg.connect(self._database_url) as connection:
            idem = connection.execute(
                "SELECT request_id,content_hash FROM research_promotion_idempotency WHERE idempotency_key=%s FOR UPDATE",
                (idempotency_key,),
            ).fetchone()
            if idem is not None and (str(idem[0]) != request.request_id or str(idem[1]) != request.result.content_hash):
                raise ValueError("idempotency key is already bound to different content")
            existing = connection.execute(
                "SELECT payload::text FROM research_promotion_requests WHERE request_id=%s FOR UPDATE",
                (request.request_id,),
            ).fetchone()
            if existing is not None:
                if _canonical(json.loads(str(existing[0]))) != encoded:
                    raise ValueError("promotion request already contains different content")
                return
            connection.execute(
                "INSERT INTO research_promotion_requests(request_id,content_hash,status,payload,created_at,updated_at) VALUES (%s,%s,%s,%s::jsonb,%s,%s)",
                (request.request_id, request.result.content_hash, request.status.value, encoded, request.created_at, request.created_at),
            )
            connection.execute(
                "INSERT INTO research_promotion_idempotency(idempotency_key,request_id,content_hash) VALUES (%s,%s,%s)",
                (idempotency_key, request.request_id, request.result.content_hash),
            )

    def update(self, request: PromotionRequest, updated_at: datetime) -> None:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                "UPDATE research_promotion_requests SET status=%s,payload=%s::jsonb,updated_at=%s WHERE request_id=%s",
                (request.status.value, _canonical(_request_payload(request)), updated_at, request.request_id),
            )


def _request_payload(request: PromotionRequest) -> dict[str, Any]:
    return {
        "requestId": request.request_id,
        "status": request.status.value,
        "createdAt": request.created_at.isoformat(),
        "risks": list(request.risks),
        "result": manifest_payload(request.result),
        "reproduction": None if request.reproduction is None else {
            "pitPassed": request.reproduction.pit_passed,
            "outOfSample": request.reproduction.out_of_sample,
            "costPassed": request.reproduction.cost_passed,
            "correlationPassed": request.reproduction.correlation_passed,
            "sensitivityPassed": request.reproduction.sensitivity_passed,
            "securityPassed": request.reproduction.security_passed,
        },
        "rejectionReason": request.rejection_reason,
    }


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
