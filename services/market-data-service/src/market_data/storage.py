from hashlib import sha256
from typing import cast

from boto3.session import Session


class ArtifactStore:
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str) -> None:
        self.bucket = bucket
        self.client = Session().client("s3", endpoint_url=endpoint_url, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

    def put_immutable(self, key: str, content: bytes) -> str:
        digest = sha256(content).hexdigest()
        try:
            existing = self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception as error:
            response = getattr(error, "response", None)
            code = response.get("Error", {}).get("Code") if isinstance(response, dict) else None
            if code not in {"404", "NoSuchKey", "NotFound"}:
                raise
        else:
            existing_hash = existing.get("Metadata", {}).get("sha256")
            if existing_hash != digest:
                raise ValueError("immutable artifact key already contains different content")
            return digest
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content, Metadata={"sha256": digest})
        return digest

    def get_verified(self, key: str, expected_hash: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        content = cast(bytes, response["Body"].read())
        if sha256(content).hexdigest() != expected_hash:
            raise ValueError("artifact hash mismatch")
        return content
