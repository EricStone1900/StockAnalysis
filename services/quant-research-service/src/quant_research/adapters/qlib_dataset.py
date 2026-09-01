"""阶段02 DataVersion Artifact 到只读 Qlib Provider 目录的受控转换。"""

from __future__ import annotations

import io
import shutil
import tarfile
from pathlib import Path, PurePosixPath
from tempfile import mkdtemp
from typing import cast
from urllib.parse import urlparse

from boto3.session import Session

from quant_research.adapters.qlib import ArtifactIntegrityError, VerifiedArtifactReader
from quant_research.domain import ArtifactRef, MarketDataVersionRef


class S3VerifiedArtifactReader:
    """MinIO/S3只读客户端；只接受配置Bucket中的minio://对象引用。"""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str) -> None:
        self._bucket = bucket
        self._client = Session().client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def get_verified(self, artifact: ArtifactRef) -> bytes:
        parsed = urlparse(artifact.uri)
        if parsed.scheme != "minio" or parsed.netloc != self._bucket or not parsed.path.lstrip("/"):
            raise ArtifactIntegrityError("artifact URI is outside the configured bucket")
        response = self._client.get_object(Bucket=self._bucket, Key=parsed.path.lstrip("/"))
        content = cast(bytes, response["Body"].read())
        from hashlib import sha256

        if sha256(content).hexdigest() != artifact.sha256:
            raise ArtifactIntegrityError(f"artifact hash mismatch: {artifact.uri}")
        return content


class QlibDatasetMaterializer:
    """安全解包阶段02的`qlib_bin/`归档，禁止覆盖及链接逃逸。"""

    def __init__(self, reader: VerifiedArtifactReader, cache_root: Path) -> None:
        self._reader = reader
        self._cache_root = cache_root

    def materialize(self, data_version: MarketDataVersionRef) -> Path:
        content = self._reader.get_verified(data_version.artifact)
        destination = self._cache_root / data_version.version_id / data_version.artifact.sha256
        provider_root = destination / "qlib_bin"
        marker = destination / ".artifact-sha256"
        if provider_root.is_dir() and marker.is_file() and marker.read_text(encoding="utf-8") == data_version.artifact.sha256:
            return provider_root
        if destination.exists():
            raise ArtifactIntegrityError("existing Qlib cache does not match its immutable artifact")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(mkdtemp(prefix="qlib-materialize-", dir=destination.parent))
        try:
            _extract_qlib_archive(content, temporary)
            provider = temporary / "qlib_bin"
            if not provider.is_dir():
                raise ArtifactIntegrityError("DataVersion artifact does not contain qlib_bin")
            (temporary / ".artifact-sha256").write_text(data_version.artifact.sha256, encoding="utf-8")
            _make_read_only(temporary)
            temporary.rename(destination)
            return provider_root
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise


def initialize_qlib_provider(provider_root: Path) -> None:
    """唯一允许初始化Qlib全局Provider的位置；调用方必须先完成Hash校验与解包。"""
    if not provider_root.is_dir():
        raise ArtifactIntegrityError("Qlib provider directory does not exist")
    import qlib

    qlib.init(provider_uri=str(provider_root), region="cn")


def _extract_qlib_archive(content: bytes, destination: Path) -> None:
    try:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
            for member in archive.getmembers():
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "qlib_bin":
                    raise ArtifactIntegrityError("Qlib archive contains an unsafe path")
                if member.issym() or member.islnk() or member.isdev():
                    raise ArtifactIntegrityError("Qlib archive contains a forbidden link or device")
                target = destination.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise ArtifactIntegrityError("Qlib archive contains an unsupported member")
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ArtifactIntegrityError("unable to read Qlib archive member")
                target.write_bytes(source.read())
    except tarfile.TarError as error:
        raise ArtifactIntegrityError("DataVersion artifact is not a readable tar.gz archive") from error


def _make_read_only(directory: Path) -> None:
    for path in sorted(directory.rglob("*"), reverse=True):
        path.chmod(0o555 if path.is_dir() else 0o444)
    directory.chmod(0o555)
