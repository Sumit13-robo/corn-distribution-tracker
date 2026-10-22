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
from typing import Any

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from django.conf import settings

from .errors import AppError


class StorageService(ABC):
    mode = "abstract"

    @abstractmethod
    def put_object(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def get_object(self, key: str) -> bytes: ...

    @abstractmethod
    def presigned_put(self, key: str, content_type: str, max_bytes: int) -> str | None: ...

    @abstractmethod
    def presigned_get(self, key: str, evidence_id: str) -> str: ...


class S3StorageService(StorageService):
    mode = "s3"

    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.STORAGE_ENDPOINT_URL or None,
            region_name=settings.STORAGE_REGION or None,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY_ID,
            aws_secret_access_key=settings.STORAGE_SECRET_ACCESS_KEY,
            config=BotoConfig(signature_version="s3v4"),
        )
        self.bucket = settings.STORAGE_BUCKET

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get_object(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as exc:
            raise AppError("Evidence object could not be read", code="INTERNAL_ERROR") from exc

    def presigned_put(self, key: str, content_type: str, max_bytes: int) -> str | None:
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=settings.STORAGE_SIGNED_URL_TTL_SECONDS,
        )

    def presigned_get(self, key: str, evidence_id: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=settings.STORAGE_SIGNED_URL_TTL_SECONDS,
        )


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
        return None

    def presigned_get(self, key: str, evidence_id: str) -> str:
        expires = int(time.time()) + self.ttl
        sig = _blob_signature(evidence_id, expires)
        return (
            f"{self.public_base_url}/api/v1/evidence/blob/{evidence_id}"
            f"?exp={expires}&sig={sig}"
        )


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
    if settings.STORAGE_MODE == "s3":
        return {
            "mode": "s3",
            "configured": bool(settings.STORAGE_BUCKET and settings.STORAGE_ACCESS_KEY_ID),
        }
    root = Path(settings.LOCAL_STORAGE_DIR)
    return {"mode": "local", "writable": os.access(root if root.exists() else Path("."), os.W_OK)}
