import hashlib
import io
import json
import tarfile
from datetime import UTC, datetime

import pytest

from market_data.investment_data import (
    ARCHIVE_NAME,
    MANIFEST_NAME,
    REQUIRED_ARCHIVE_MEMBERS,
    InvestmentDataReleaseAdapter,
    validate_release,
)


class FakeFetcher:
    def __init__(self, assets: dict[str, bytes]) -> None:
        self.assets = assets
        self.requests: list[str] = []

    def fetch(self, url: str) -> bytes:
        self.requests.append(url)
        return self.assets[url]


class InMemoryWriter:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_immutable(self, key: str, content: bytes) -> str:
        existing = self.objects.setdefault(key, content)
        if existing != content:
            raise ValueError("immutable object conflict")
        return hashlib.sha256(content).hexdigest()


def canonical_archive() -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        files = {
            "qlib_bin/calendars/day.txt": b"2026-08-27\n2026-08-28\n",
            "qlib_bin/calendars/day_future.txt": b"2026-08-27\n2026-08-28\n2026-08-31\n2026-09-01\n",
        }
        files.update({name: b"sh600000\t2020-01-01\t2026-08-28\n" for name in REQUIRED_ARCHIVE_MEMBERS[2:]})
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return stream.getvalue()


def canonical_manifest(archive: bytes) -> bytes:
    return json.dumps(
        {
            "release_tag": "2026-08-28",
            "target_trade_date": "2026-08-28",
            "future_start_date": "2026-08-31",
            "future_end_date": "2026-09-01",
            "dolt_commit": "a" * 32,
            "investment_data_commit": "b" * 40,
            "qlib_commit": "c" * 40,
            "image_digest": f"sha256:{'d' * 64}",
            "archive_size_bytes": len(archive),
            "archive_sha256": f"sha256:{hashlib.sha256(archive).hexdigest()}",
        },
        separators=(",", ":"),
    ).encode()


def test_fixed_release_is_validated_landed_idempotently_and_becomes_data_version() -> None:
    archive = canonical_archive()
    manifest = canonical_manifest(archive)
    root = "https://example.test/releases"
    fetcher = FakeFetcher(
        {
            f"{root}/2026-08-28/{MANIFEST_NAME}": manifest,
            f"{root}/2026-08-28/{ARCHIVE_NAME}": archive,
        }
    )
    adapter = InvestmentDataReleaseAdapter(fetcher, root)
    writer = InMemoryWriter()

    validated = adapter.download_and_validate("2026-08-28")
    first = adapter.land(validated, writer, "v1")
    second = adapter.land(validated, writer, "v1")
    version = first.build_data_version("v1", datetime(2026, 8, 29, tzinfo=UTC))

    assert len(writer.objects) == 2
    assert first.archive_artifact.raw_artifact_hash == second.archive_artifact.raw_artifact_hash
    assert version.source_release_tag == "2026-08-28"
    assert version.source_manifest_hash == first.manifest_artifact.raw_artifact_hash
    assert version.artifact_hash == first.archive_artifact.raw_artifact_hash
    assert fetcher.requests == [f"{root}/2026-08-28/{MANIFEST_NAME}", f"{root}/2026-08-28/{ARCHIVE_NAME}"]


def test_invalid_archive_identity_or_latest_tag_is_rejected() -> None:
    archive = canonical_archive()
    manifest = canonical_manifest(archive)
    with pytest.raises(ValueError, match="fixed YYYY-MM-DD"):
        validate_release("latest", archive, manifest)
    with pytest.raises(ValueError, match="identity"):
        validate_release("2026-08-28", archive + b"tampered", manifest)
