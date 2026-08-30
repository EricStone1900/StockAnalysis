"""固定Release的investment_data导入边界，不允许使用latest。"""

import hashlib
import io
import json
import tarfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol, cast
from urllib.request import urlopen

from pydantic import BaseModel, Field

from .pit import RawArtifact
from .quality import QualityStatus
from .versioning import DataVersion

RELEASE_ROOT = "https://github.com/chenditc/investment_data/releases/download"
ARCHIVE_NAME = "qlib_bin.tar.gz"
MANIFEST_NAME = "qlib_bin.manifest.json"
REQUIRED_MANIFEST_KEYS = frozenset(
    {
        "release_tag",
        "target_trade_date",
        "future_start_date",
        "future_end_date",
        "dolt_commit",
        "investment_data_commit",
        "qlib_commit",
        "image_digest",
        "archive_size_bytes",
        "archive_sha256",
    }
)
REQUIRED_ARCHIVE_MEMBERS = (
    "qlib_bin/calendars/day.txt",
    "qlib_bin/calendars/day_future.txt",
    "qlib_bin/instruments/all.txt",
    "qlib_bin/instruments/csi300.txt",
    "qlib_bin/instruments/csi500.txt",
    "qlib_bin/instruments/csi800.txt",
    "qlib_bin/instruments/csi1000.txt",
    "qlib_bin/instruments/csiall.txt",
)


class ReleaseAssetFetcher(Protocol):
    def fetch(self, url: str) -> bytes: ...


class ImmutableArtifactWriter(Protocol):
    def put_immutable(self, key: str, content: bytes) -> str: ...


class UrlLibReleaseAssetFetcher:
    def fetch(self, url: str) -> bytes:
        with urlopen(url, timeout=60) as response:
            return cast(bytes, response.read())


class ReleaseManifest(BaseModel):
    release_tag: str
    target_trade_date: date
    future_start_date: date
    future_end_date: date
    dolt_commit: str = Field(pattern=r"^[0-9a-v]{32}$")
    investment_data_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    qlib_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    archive_size_bytes: int = Field(gt=0)
    archive_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ValidatedRelease:
    manifest: ReleaseManifest
    archive: bytes
    manifest_bytes: bytes
    archive_hash: str
    manifest_hash: str


@dataclass(frozen=True)
class LandedRelease:
    validated: ValidatedRelease
    archive_artifact: RawArtifact
    manifest_artifact: RawArtifact

    def build_data_version(
        self, policy_version: str, available_at: datetime, quality_report_uri: str | None = None,
        close_gap_index_uri: str | None = None, close_gap_index_hash: str | None = None,
    ) -> DataVersion:
        tag = self.validated.manifest.release_tag
        return DataVersion(
            version_id=f"cn-a-investment-data-{tag}-{self.validated.archive_hash[:12]}",
            scope="CN_A",
            source_version=self.validated.manifest.investment_data_commit,
            source_release_tag=tag,
            source_policy_version=policy_version,
            source_manifest_hash=self.validated.manifest_hash,
            artifact_uri=self.archive_artifact.raw_artifact_uri,
            artifact_hash=self.archive_artifact.raw_artifact_hash,
            quality_report_uri=quality_report_uri,
            close_gap_index_uri=close_gap_index_uri,
            close_gap_index_hash=close_gap_index_hash,
            quality_status=QualityStatus.PASS,
            available_at=available_at.astimezone(UTC),
            content_hash=self.validated.archive_hash,
        )


class InvestmentDataReleaseAdapter:
    def __init__(self, fetcher: ReleaseAssetFetcher | None = None, release_root: str = RELEASE_ROOT) -> None:
        self.fetcher = fetcher or UrlLibReleaseAssetFetcher()
        self.release_root = release_root.rstrip("/")

    def download_and_validate(self, release_tag: str) -> ValidatedRelease:
        _require_release_tag(release_tag)
        manifest_bytes = self.fetcher.fetch(self._asset_url(release_tag, MANIFEST_NAME))
        archive = self.fetcher.fetch(self._asset_url(release_tag, ARCHIVE_NAME))
        return validate_release(release_tag, archive, manifest_bytes)

    def land(
        self,
        validated: ValidatedRelease,
        writer: ImmutableArtifactWriter,
        policy_version: str,
        artifact_uri_prefix: str = "minio://artifacts",
    ) -> LandedRelease:
        base_key = f"raw/investment_data/{validated.manifest.release_tag}/{validated.archive_hash}"
        archive_key = f"{base_key}/{ARCHIVE_NAME}"
        manifest_key = f"{base_key}/{MANIFEST_NAME}"
        if writer.put_immutable(archive_key, validated.archive) != validated.archive_hash:
            raise ValueError("artifact writer returned unexpected archive hash")
        if writer.put_immutable(manifest_key, validated.manifest_bytes) != validated.manifest_hash:
            raise ValueError("artifact writer returned unexpected manifest hash")
        ingested_at = datetime.now(UTC)
        release_tag = validated.manifest.release_tag
        source_version = validated.manifest.investment_data_commit
        return LandedRelease(
            validated=validated,
            archive_artifact=RawArtifact(
                source="investment_data",
                source_record_id=f"{release_tag}/{ARCHIVE_NAME}",
                source_version=source_version,
                source_release_tag=release_tag,
                raw_artifact_uri=f"{artifact_uri_prefix.rstrip('/')}/{archive_key}",
                raw_artifact_hash=validated.archive_hash,
                license_ref="https://github.com/chenditc/investment_data/blob/main/LICENSE",
                source_policy_version=policy_version,
                ingested_at=ingested_at,
            ),
            manifest_artifact=RawArtifact(
                source="investment_data",
                source_record_id=f"{release_tag}/{MANIFEST_NAME}",
                source_version=source_version,
                source_release_tag=release_tag,
                raw_artifact_uri=f"{artifact_uri_prefix.rstrip('/')}/{manifest_key}",
                raw_artifact_hash=validated.manifest_hash,
                license_ref="https://github.com/chenditc/investment_data/blob/main/LICENSE",
                source_policy_version=policy_version,
                ingested_at=ingested_at,
            ),
        )

    def _asset_url(self, release_tag: str, asset_name: str) -> str:
        return f"{self.release_root}/{release_tag}/{asset_name}"


def validate_release(release_tag: str, archive: bytes, manifest_bytes: bytes) -> ValidatedRelease:
    _require_release_tag(release_tag)
    manifest = _parse_manifest(manifest_bytes)
    if manifest.release_tag != release_tag:
        raise ValueError("release tag does not match manifest")
    archive_hash = hashlib.sha256(archive).hexdigest()
    if manifest.archive_size_bytes != len(archive) or manifest.archive_sha256 != f"sha256:{archive_hash}":
        raise ValueError("archive identity does not match manifest")
    _validate_archive_semantics(archive, manifest)
    return ValidatedRelease(
        manifest=manifest,
        archive=archive,
        manifest_bytes=manifest_bytes,
        archive_hash=archive_hash,
        manifest_hash=hashlib.sha256(manifest_bytes).hexdigest(),
    )


def _parse_manifest(manifest_bytes: bytes) -> ReleaseManifest:
    try:
        payload = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid release manifest") from error
    if not isinstance(payload, dict) or set(payload) != REQUIRED_MANIFEST_KEYS:
        raise ValueError("release manifest keys do not match the canonical schema")
    try:
        return ReleaseManifest.model_validate(payload)
    except ValueError as error:
        raise ValueError("invalid release manifest") from error


def _validate_archive_semantics(archive_bytes: bytes, manifest: ReleaseManifest) -> None:
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            members = {member.name: member for member in archive.getmembers()}
            if len(members) != len(archive.getmembers()) or any(not _safe_member(member) for member in archive.getmembers()):
                raise ValueError("archive contains unsafe members")
            for name in REQUIRED_ARCHIVE_MEMBERS:
                if name not in members or not members[name].isfile():
                    raise ValueError(f"archive is missing required member: {name}")
            days = _read_dates(archive, members["qlib_bin/calendars/day.txt"])
            future_days = _read_dates(archive, members["qlib_bin/calendars/day_future.txt"])
            instrument_end_dates = [
                _read_instrument_end_dates(archive, members[name]) for name in REQUIRED_ARCHIVE_MEMBERS[2:]
            ]
    except (OSError, tarfile.TarError, EOFError) as error:
        raise ValueError("invalid qlib archive") from error
    if days[-1] != manifest.target_trade_date:
        raise ValueError("target trade date does not match archive")
    if any(max(end_dates) != manifest.target_trade_date for end_dates in instrument_end_dates):
        raise ValueError("instrument date range does not match target trade date")
    if future_days[: len(days)] != days or len(future_days) <= len(days):
        raise ValueError("future calendar does not extend the trading calendar")
    if future_days[len(days)] != manifest.future_start_date or future_days[-1] != manifest.future_end_date:
        raise ValueError("future calendar does not match manifest")


def _safe_member(member: tarfile.TarInfo) -> bool:
    name = member.name.rstrip("/")
    is_qlib_member = name == "qlib_bin" or name.startswith("qlib_bin/")
    path_parts = name.split("/")
    return (
        bool(name)
        and not name.startswith("/")
        and "\\" not in name
        and is_qlib_member
        and all(part not in {"", ".", ".."} for part in path_parts)
        and (member.isfile() or member.isdir())
    )


def _read_dates(archive: tarfile.TarFile, member: tarfile.TarInfo) -> list[date]:
    content = archive.extractfile(member)
    if content is None:
        raise ValueError("required archive member is unreadable")
    try:
        dates = [date.fromisoformat(line) for line in content.read().decode("utf-8").splitlines()]
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("calendar member is malformed") from error
    if not dates or dates != sorted(set(dates)):
        raise ValueError("calendar member is not strictly ordered")
    return dates


def _read_instrument_end_dates(archive: tarfile.TarFile, member: tarfile.TarInfo) -> list[date]:
    content = archive.extractfile(member)
    if content is None:
        raise ValueError("required archive member is unreadable")
    try:
        rows = [line.split("\t") for line in content.read().decode("utf-8").splitlines()]
        end_dates = [date.fromisoformat(row[2]) for row in rows if len(row) == 3 and row[0]]
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("instrument member is malformed") from error
    if not rows or len(end_dates) != len(rows):
        raise ValueError("instrument member is malformed")
    return end_dates


def _require_release_tag(value: str) -> None:
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as error:
        raise ValueError("release tag must be a fixed YYYY-MM-DD value, never latest") from error
