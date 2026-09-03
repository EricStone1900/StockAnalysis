import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.research_automation.promotion import PromotionRequestService
from src.research_automation.promotion_persistence import PostgresPromotionRepository
from tests.unit.test_promotion import _result

pytestmark = pytest.mark.skipif(
    "RESEARCH_AUTOMATION_DATABASE_URL" not in os.environ,
    reason="requires local PostgreSQL",
)


def test_promotion_request_audit_is_idempotent() -> None:
    url = os.environ["RESEARCH_AUTOMATION_DATABASE_URL"]
    repository = PostgresPromotionRepository(url)
    repository.migrate(Path(__file__).parents[2] / "migrations/002_promotion_governance.sql")
    request = PromotionRequestService().submit("promotion-pg-1", "promotion-pg-key-1", _result(), (), datetime(2026, 9, 3, tzinfo=UTC))
    repository.save_submission(request, "promotion-pg-key-1")
    repository.save_submission(request, "promotion-pg-key-1")
