import io
import tarfile
from hashlib import sha256
from pathlib import Path

import pytest

from quant_research.adapters.qlib import ArtifactIntegrityError, InMemoryVerifiedArtifactReader
from quant_research.adapters.qlib_dataset import QlibDatasetMaterializer
from quant_research.domain import ArtifactRef, DataQualityStatus, MarketDataVersionRef


def archive_with(*members: tuple[str, bytes]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, content in members:
            item = tarfile.TarInfo(name)
            item.size = len(content)
            archive.addfile(item, io.BytesIO(content))
    return output.getvalue()


def data_version(content: bytes) -> MarketDataVersionRef:
    archive_ref = ArtifactRef(uri="minio://artifacts/qlib.tar.gz", sha256=sha256(content).hexdigest())
    return MarketDataVersionRef(
        version_id="cn-a-fixture-v1",
        artifact=archive_ref,
        close_gap_index=ArtifactRef(uri="minio://artifacts/gaps.json", sha256="a" * 64),
        quality_status=DataQualityStatus.WARN,
        source_release_tag="fixture-2026-08-30",
        source_policy_version="v1-close-gap-fast",
    )


def test_materializer_creates_stable_read_only_provider_cache(tmp_path: Path) -> None:
    content = archive_with(
        ("qlib_bin/calendars/day.txt", b"2020-01-02\n"),
        ("qlib_bin/instruments/all.txt", b"sh600000\t2020-01-02\t2099-12-31\n"),
    )
    version = data_version(content)
    materializer = QlibDatasetMaterializer(InMemoryVerifiedArtifactReader({version.artifact.uri: content}), tmp_path)

    first = materializer.materialize(version)
    second = materializer.materialize(version)

    assert first == second
    assert (first / "calendars/day.txt").read_text(encoding="utf-8") == "2020-01-02\n"
    assert not (first / "calendars/day.txt").stat().st_mode & 0o222


def test_materializer_rejects_path_escape(tmp_path: Path) -> None:
    content = archive_with(("../outside.txt", b"unsafe"))
    version = data_version(content)
    materializer = QlibDatasetMaterializer(InMemoryVerifiedArtifactReader({version.artifact.uri: content}), tmp_path)

    with pytest.raises(ArtifactIntegrityError, match="unsafe path"):
        materializer.materialize(version)
