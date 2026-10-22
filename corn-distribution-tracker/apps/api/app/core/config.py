"""Application configuration.

All configuration is environment-driven (12-factor). Production startup validates
that required secrets exist and insecure sample/default modes are rejected (see
`Settings.validate_security`), per docs/architecture/SECURITY_AND_PRIVACY.md and
docs/ops/ENVIRONMENT_VARIABLES.md.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("app.config")

# Development bootstrap fallback only; production must set SECRET_KEY via env.
# Not a credential: it is an obvious, documented placeholder (never used in prod).
DEV_SAMPLE_SECRET = "sample-development-only-secret-change-me"  # noqa: S105


def _split_origins(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "Corn Distribution Tracker"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://corn:corn@localhost:5432/corn_tracker"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    secret_key: str = DEV_SAMPLE_SECRET
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14

    # Exact origins; "*" is only allowed without credentials in development.
    cors_allowed_origins: str = "http://localhost:5173"
    cors_allow_credentials: bool = True

    cookie_secure: bool = False
    cookie_samesite: Literal["Lax", "Strict", "None"] = "Lax"
    cookie_domain: str = ""

    rate_limit_backend_url: str = ""

    # Evidence storage: "s3" for production S3-compatible buckets, "local" for
    # development/testing (private on-disk directory with expiring signed URLs).
    storage_mode: Literal["s3", "local"] = "local"
    storage_endpoint_url: str = ""
    storage_region: str = ""
    storage_bucket: str = ""
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_signed_url_ttl_seconds: int = 120
    local_storage_dir: str = "./storage-data"
    max_evidence_upload_bytes: int = 10 * 1024 * 1024
    allowed_evidence_content_types: str = "image/jpeg,image/png,image/webp"

    # Organization defaults (DB settings row overrides once bootstrapped).
    org_timezone: str = "Africa/Juba"
    default_geofence_radius_m: int = 200
    max_acceptable_gps_accuracy_m: int = 100
    max_location_age_seconds: int = 300
    max_capture_time_drift_seconds: int = 600

    log_level: str = "INFO"

    # Absolute base URL used when constructing local-mode signed URLs and emails.
    public_base_url: str = "http://localhost:8000"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]

    @property
    def evidence_content_type_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_evidence_content_types.split(",") if item.strip()]

    @property
    def is_testing(self) -> bool:
        return self.app_env == "test"

    def validate_security(self) -> list[str]:
        """Return a list of configuration insecurities (never secret values)."""
        problems: list[str] = []
        if self.is_production:
            if self.secret_key == DEV_SAMPLE_SECRET:
                problems.append("SECRET_KEY must be replaced with a high-entropy production secret.")
            if "*" in self.cors_allowed_origins and self.cors_allow_credentials:
                problems.append("CORS wildcard origin cannot be combined with credentials.")
            if not self.cookie_secure:
                problems.append("COOKIE_SECURE=true is required in production.")
            if self.cookie_samesite == "None" and not self.cookie_secure:
                problems.append("SameSite=None requires Secure cookies.")
            if self.storage_mode != "s3":
                problems.append("Private S3-compatible evidence storage is required in production.")
            elif not (self.storage_bucket and self.storage_access_key_id and self.storage_secret_access_key):
                problems.append("Storage credentials are required for storage_mode=s3.")
        elif self.app_env == "staging" and self.secret_key == DEV_SAMPLE_SECRET:
            problems.append("SECRET_KEY must not stay at the development sample value in staging.")
        return problems


def assert_secure_settings(settings: Settings) -> None:
    """Fail startup for insecure production/staging configuration.

    Development/test keep the convenient sample defaults; production and staging
    must never run with a placeholder secret, insecure cookies or local storage.
    The raised message lists problems only, never secret values.
    """
    problems = settings.validate_security()
    if not problems:
        return
    for problem in problems:
        logger.error("Security configuration problem: %s", problem)
    if settings.is_production or settings.app_env == "staging":
        raise RuntimeError(
            f"Insecure configuration for APP_ENV={settings.app_env}: " + "; ".join(problems)
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    assert_secure_settings(settings)
    return settings
