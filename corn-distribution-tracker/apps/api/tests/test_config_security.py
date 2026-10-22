"""Security configuration fail-fast tests.

The deployment runbook (and the config module docstring) require production to
refuse startup with placeholder secrets, insecure cookies or local evidence
storage. Tests build Settings directly with `_env_file=None` so a developer's
local `.env` cannot affect the result, and use synthetic values only.
"""

from __future__ import annotations

import pytest

from app.core.config import DEV_SAMPLE_SECRET, Settings, assert_secure_settings


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_production_rejects_placeholder_defaults() -> None:
    settings = make_settings(
        app_env="production",
        secret_key=DEV_SAMPLE_SECRET,
        cookie_secure=False,
        storage_mode="local",
    )

    problems = settings.validate_security()
    assert any("SECRET_KEY" in problem for problem in problems)
    assert any("storage" in problem.lower() for problem in problems)
    with pytest.raises(RuntimeError, match="Insecure configuration for APP_ENV=production"):
        assert_secure_settings(settings)


def test_production_accepts_hardened_settings() -> None:
    settings = make_settings(
        app_env="production",
        secret_key="synthetic-" + "x" * 64,
        cors_allowed_origins="https://tracker.example.test",
        cookie_secure=True,
        storage_mode="s3",
        storage_bucket="synthetic-evidence-bucket",
        storage_access_key_id="synthetic-access-key",
        storage_secret_access_key="synthetic-secret-key",
    )

    assert settings.validate_security() == []
    assert_secure_settings(settings)


def test_staging_rejects_sample_secret() -> None:
    settings = make_settings(app_env="staging", secret_key=DEV_SAMPLE_SECRET)
    with pytest.raises(RuntimeError, match="APP_ENV=staging"):
        assert_secure_settings(settings)


def test_development_allows_documented_sample_defaults() -> None:
    settings = make_settings(app_env="development")
    assert_secure_settings(settings)
