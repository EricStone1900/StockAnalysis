import json

import pytest

from src.research_automation.model_audit import ModelCallAuditStore
from src.research_automation.provider import FixedModelProvider, ModelRequest, ProviderAdapter


def _request() -> ModelRequest:
    return ModelRequest("call-1", "fixed", "model-v1", "prompt-v1", "a" * 64, "生成候选")


def _valid_output() -> str:
    return json.dumps({
        "candidate_type": "factor",
        "title": "测试因子",
        "summary": "固定测试候选",
        "support_evidence": ["evidence-1"],
        "counterexamples": ["counterexample-1"],
        "failure_reasons": ["尚未完成样本外验证"],
        "uncertainty": "仅用于研究",
    })


def test_provider_output_is_validated_and_audited() -> None:
    audits = ModelCallAuditStore()
    proposal = ProviderAdapter(FixedModelProvider(_valid_output()), audits).generate_candidate(_request())
    assert proposal.candidate_type == "factor"
    assert audits.get("call-1") is not None


def test_invalid_output_fails_closed_after_audit() -> None:
    audits = ModelCallAuditStore()
    with pytest.raises(ValueError, match="failed candidate schema"):
        ProviderAdapter(FixedModelProvider('{"candidate_type":"factor"}'), audits).generate_candidate(_request())
    assert audits.get("call-1") is not None


def test_output_size_limit_rejects_before_schema_processing() -> None:
    with pytest.raises(ValueError, match="size limit"):
        ProviderAdapter(FixedModelProvider(_valid_output()), ModelCallAuditStore(), max_output_bytes=4).generate_candidate(_request())
