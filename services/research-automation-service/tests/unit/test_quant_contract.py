from datetime import UTC, datetime

import pytest

from src.research_automation.promotion import PromotionGateResult, PromotionRequestService
from src.research_automation.quant_contract import (
    PromotionSubmission,
    QuantReproductionResponse,
    ResearchPromotionClient,
)
from tests.unit.test_promotion import _result


class FakeQuantPort:
    def reproduce(self, submission: PromotionSubmission) -> QuantReproductionResponse:
        return QuantReproductionResponse(submission.request_id, True, PromotionGateResult(True, True, True, True, True, True), "r" * 64)


def test_research_sends_only_hash_and_versioned_artifact_reference() -> None:
    request = PromotionRequestService().submit("promotion-contract", "key-contract", _result(), (), datetime(2026, 9, 3, tzinfo=UTC))
    response = ResearchPromotionClient(FakeQuantPort()).submit_for_reproduction(request)
    assert response.reproduced is True
    assert response.gates.passed is True


def test_research_identity_cannot_activate_quant() -> None:
    with pytest.raises(PermissionError, match="cannot activate"):
        ResearchPromotionClient(FakeQuantPort()).activate("promotion-contract")
