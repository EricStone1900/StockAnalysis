from decimal import Decimal
from hashlib import sha256

import pytest

from quant_research.adapters.qlib import ArtifactIntegrityError, InMemoryVerifiedArtifactReader
from quant_research.baseline_model import LinearBaselineModel
from quant_research.domain import ArtifactRef
from quant_research.research_artifact_reader import ResearchArtifactReader
from quant_research.research_artifacts import ResearchArtifactPublisher


def test_reader_verifies_model_hash_before_parsing() -> None:
    model = LinearBaselineModel(
        model_id="baseline", model_version="v1", data_version_id="data-v1",
        factor_id="price.momentum.2d", intercept=Decimal(0), coefficient=Decimal(1),
        training_row_count=2, canonical_content_hash="a" * 64,
    )
    objects: dict[str, bytes] = {}

    class Writer:
        def put_immutable(self, key: str, content: bytes) -> str:
            objects[f"minio://artifacts/{key}"] = content
            return sha256(content).hexdigest()

    published = ResearchArtifactPublisher(Writer(), "minio://artifacts").publish_model(model)
    loaded = ResearchArtifactReader(InMemoryVerifiedArtifactReader(objects)).load_model(published.artifact)
    assert loaded == model

    tampered = objects[published.artifact.uri].replace(b"baseline", b"tampered", 1)
    objects[published.artifact.uri] = tampered
    with pytest.raises(ArtifactIntegrityError, match="hash mismatch"):
        ResearchArtifactReader(InMemoryVerifiedArtifactReader(objects)).load_model(published.artifact)


def test_reader_rejects_invalid_backtest_json() -> None:
    artifact = ArtifactRef(uri="minio://artifacts/bad.json", sha256=sha256(b"not-json").hexdigest())
    reader = ResearchArtifactReader(InMemoryVerifiedArtifactReader({artifact.uri: b"not-json"}))
    with pytest.raises(ArtifactIntegrityError, match="not valid portfolio"):
        reader.load_backtest(artifact)
