"""Private evidence/object storage abstraction.

Production uses an S3-compatible private bucket with short-lived presigned
URLs. Development/testing uses a private on-disk directory served by the API
through HMAC-signed, expiring URLs. Storage keys are opaque random strings.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any, NamedTuple

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

from .errors import AppError


class ObjectStat(NamedTuple):
    size_bytes: int
    content_type: str | None


class StorageService(ABC):
    mode = "abstract"

    @abstractmethod
    def put_object(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def get_object(self, key: str, max_bytes: int | None = None) -> bytes:
        """Read an object, returning at most ``max_bytes + 1`` when bounded.

        Callers that pass ``max_bytes`` must reject a result longer than the
        limit. The extra byte distinguishes an exact-size object from an
        oversized one without reading an attacker-controlled object into
        memory.
        """
        ...

    @abstractmethod
    def stat_object(self, key: str) -> ObjectStat: ...

    @abstractmethod
    def presigned_put(
        self, key: str, content_type: str, max_bytes: int, expires_in: int | None = None
    ) -> str | None: ...

    @abstractmethod
    def upload_headers(self, content_type: str) -> dict[str, str]: ...

    @abstractmethod
    def presigned_get(self, key: str, evidence_id: str) -> str: ...

    @abstractmethod
    def health(self) -> dict[str, Any]: ...


class S3StorageService(StorageService):
    mode = "s3"

    def __init__(self) -> None:
        addressing_style = getattr(settings, "STORAGE_ADDRESSING_STYLE", "auto")
        s3_config: dict[str, Any] = {"signature_version": "s3v4"}
        if addressing_style in {"path", "virtual"}:
            s3_config["s3"] = {"addressing_style": addressing_style}
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.STORAGE_ENDPOINT_URL or None,
            region_name=settings.STORAGE_REGION or None,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY_ID,
            aws_secret_access_key=settings.STORAGE_SECRET_ACCESS_KEY,
            config=BotoConfig(**s3_config),
        )
        self.bucket = settings.STORAGE_BUCKET

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
        }
        encryption = getattr(settings, "STORAGE_SERVER_SIDE_ENCRYPTION", "")
        if encryption:
            kwargs["ServerSideEncryption"] = encryption
            kms_key_id = getattr(settings, "STORAGE_KMS_KEY_ID", "")
            if kms_key_id:
                kwargs["SSEKMSKeyId"] = kms_key_id
        self.client.put_object(**kwargs)

    def get_object(self, key: str, max_bytes: int | None = None) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            try:
                return body.read() if max_bytes is None else body.read(max_bytes + 1)
            finally:
                body.close()
        except ClientError as exc:
            raise AppError("Evidence object could not be read", code="INTERNAL_ERROR") from exc

    def stat_object(self, key: str) -> ObjectStat:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                raise AppError(
                    "Uploaded object not found; retry the upload.", status_code=404, code="NOT_FOUND"
                ) from exc
            raise AppError("Evidence object could not be inspected", code="INTERNAL_ERROR") from exc
        return ObjectStat(
            size_bytes=int(response.get("ContentLength", 0)),
            content_type=response.get("ContentType"),
        )

    def presigned_put(
        self, key: str, content_type: str, max_bytes: int, expires_in: int | None = None
    ) -> str | None:
        params: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "ContentType": content_type,
        }
        encryption = getattr(settings, "STORAGE_SERVER_SIDE_ENCRYPTION", "")
        if encryption:
            params["ServerSideEncryption"] = encryption
            kms_key_id = getattr(settings, "STORAGE_KMS_KEY_ID", "")
            if kms_key_id:
                params["SSEKMSKeyId"] = kms_key_id
        return self.client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=expires_in or settings.STORAGE_SIGNED_URL_TTL_SECONDS,
        )

    def upload_headers(self, content_type: str) -> dict[str, str]:
        headers = {"Content-Type": content_type}
        encryption = getattr(settings, "STORAGE_SERVER_SIDE_ENCRYPTION", "")
        if encryption:
            headers["x-amz-server-side-encryption"] = encryption
            kms_key_id = getattr(settings, "STORAGE_KMS_KEY_ID", "")
            if kms_key_id:
                headers["x-amz-server-side-encryption-aws-kms-key-id"] = kms_key_id
        return headers

    def presigned_get(self, key: str, evidence_id: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=settings.STORAGE_SIGNED_URL_TTL_SECONDS,
        )

    def health(self) -> dict[str, Any]:
        configured = bool(self.bucket and settings.STORAGE_ACCESS_KEY_ID)
        reachable = False
        if configured:
            try:
                self.client.head_bucket(Bucket=self.bucket)
                reachable = True
            except (ClientError, BotoCoreError):
                # A DNS/timeout/endpoint failure must make readiness fail, not
                # turn the health probe into an unhandled 500.
                reachable = False
        return {"mode": "s3", "configured": configured, "reachable": reachable}


class LocalStorageService(StorageService):
    mode = "local"

    def __init__(self) -> None:
        self.root = Path(settings.LOCAL_STORAGE_DIR).resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.ttl = settings.STORAGE_SIGNED_URL_TTL_SECONDS
        self.public_base_url = settings.PUBLIC_BASE_URL.rstrip("/")

    def _path(self, key: str) -> Path:
        if ".." in key or key.startswith("/"):
            raise AppError("Invalid storage key", code="INTERNAL_ERROR")
        path = (self.root / key).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            raise AppError("Invalid storage key", code="INTERNAL_ERROR") from None
        return path

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)

    def get_object(self, key: str, max_bytes: int | None = None) -> bytes:
        path = self._path(key)
        try:
            with path.open("rb") as handle:
                return handle.read() if max_bytes is None else handle.read(max_bytes + 1)
        except FileNotFoundError:
            raise AppError("Evidence object not found", status_code=404, code="NOT_FOUND") from None

    def stat_object(self, key: str) -> ObjectStat:
        path = self._path(key)
        try:
            stat = path.stat()
        except FileNotFoundError:
            raise AppError(
                "Uploaded object not found; retry the upload.", status_code=404, code="NOT_FOUND"
            ) from None
        return ObjectStat(size_bytes=stat.st_size, content_type=None)

    def presigned_put(
        self, key: str, content_type: str, max_bytes: int, expires_in: int | None = None
    ) -> str | None:
        return None

    def upload_headers(self, content_type: str) -> dict[str, str]:
        return {"Content-Type": content_type}

    def presigned_get(self, key: str, evidence_id: str) -> str:
        expires = int(time.time()) + self.ttl
        sig = _blob_signature(evidence_id, expires)
        return (
            f"{self.public_base_url}/api/v1/evidence/blob/{evidence_id}"
            f"?exp={expires}&sig={sig}"
        )

    def health(self) -> dict[str, Any]:
        probe = self.root / ".storage-health"
        try:
            fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, b"ok")
            finally:
                os.close(fd)
            probe.unlink(missing_ok=True)
            writable = True
        except OSError:
            writable = False
        return {"mode": "local", "writable": writable}


def _blob_signature(evidence_id: str, expires: int) -> str:
    message = f"evidence:{evidence_id}:{expires}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def verify_blob_signature(evidence_id: str, expires: int, signature: str) -> bool:
    if expires < int(time.time()):
        return False
    return hmac.compare_digest(_blob_signature(evidence_id, expires), signature)


@lru_cache
def get_storage_service() -> StorageService:
    if settings.STORAGE_MODE == "s3":
        return S3StorageService()
    return LocalStorageService()


def reset_storage_for_tests() -> None:
    get_storage_service.cache_clear()


def storage_health_probe() -> dict[str, Any]:
    return get_storage_service().health()
