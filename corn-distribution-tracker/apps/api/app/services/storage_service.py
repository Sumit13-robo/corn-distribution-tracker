"""Private evidence/object storage abstraction.

Production uses an S3-compatible private bucket with short-lived presigned URLs.
Development/testing uses a private on-disk directory; "signed" URLs are served through
an API endpoint carrying an HMAC token bound to the evidence id and an expiry.
Storage keys are opaque random strings - never names/addresses (STACK_AND_REPO).
"""

from __future__ import annotations

import hmac
import os
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import hashlib_sha256


class StorageService(ABC):
    mode: str = "abstract"

    @abstractmethod
    def put_object(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def get_object(self, key: str) -> bytes: ...

    @abstractmethod
    def presigned_put(self, key: str, content_type: str, max_bytes: int) -> str | None:
        """Return a presigned upload URL, or None when uploads must go through the API."""

    @abstractmethod
    def presigned_get(self, key: str, evidence_id: str) -> str:
        """Return a short-lived authorized read URL for a private object."""


class S3StorageService(StorageService):
    mode = "s3"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url or None,
            region_name=settings.storage_region or None,
            aws_access_key_id=settings.storage_access_key_id,
            aws_secret_access_key=settings.storage_secret_access_key,
            config=BotoConfig(signature_version="s3v4"),
        )
        self.bucket = settings.storage_bucket

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get_object(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as exc:
            raise AppError("Evidence object could not be read", code="INTERNAL_ERROR") from exc

    def presigned_put(self, key: str, content_type: str, max_bytes: int) -> str | None:
        ttl = self.settings.storage_signed_url_ttl_seconds
        return self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=ttl,
        )

    def presigned_get(self, key: str, evidence_id: str) -> str:
        ttl = self.settings.storage_signed_url_ttl_seconds
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=ttl,
        )


class LocalStorageService(StorageService):
    mode = "local"

    def __init__(self, settings: Settings) -> None:
        self.root = Path(settings.local_storage_dir).resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.ttl = settings.storage_signed_url_ttl_seconds
        self.public_base_url = settings.public_base_url

    def _path(self, key: str) -> Path:
        # Defense against path traversal: keys are server-generated opaque strings.
        if ".." in key or key.startswith("/"):
            raise AppError("Invalid storage key", code="INTERNAL_ERROR")
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root)):
            raise AppError("Invalid storage key", code="INTERNAL_ERROR")
        return path

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)

    def get_object(self, key: str) -> bytes:
        path = self._path(key)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            raise AppError("Evidence object not found", status_code=404, code="NOT_FOUND") from None

    def presigned_put(self, key: str, content_type: str, max_bytes: int) -> str | None:
        return None  # uploads flow through the authorized API endpoint in local mode

    def presigned_get(self, key: str, evidence_id: str) -> str:
        expires = int(time.time()) + self.ttl
        sig = hashlib_sha256(f"evidence:{evidence_id}:{expires}")
        return f"{self.public_base_url}/api/v1/evidence/blob/{evidence_id}?exp={expires}&sig={sig}"


def verify_blob_signature(evidence_id: str, expires: int, signature: str) -> bool:
    if expires < int(time.time()):
        return False
    expected = hashlib_sha256(f"evidence:{evidence_id}:{expires}")
    return hmac.compare_digest(expected, signature)


@lru_cache
def get_storage_service() -> StorageService:
    settings = get_settings()
    service: StorageService
    if settings.storage_mode == "s3":
        service = S3StorageService(settings)
    else:
        service = LocalStorageService(settings)
    return service


def reset_storage_for_tests() -> None:
    get_storage_service.cache_clear()


def storage_health_probe(settings: Settings) -> dict[str, Any]:
    """Safe readiness info: never returns credentials or keys."""
    if settings.storage_mode == "s3":
        return {"mode": "s3", "configured": bool(settings.storage_bucket and settings.storage_access_key_id)}
    root = Path(settings.local_storage_dir)
    return {"mode": "local", "writable": os.access(root if root.exists() else Path("."), os.W_OK)}
