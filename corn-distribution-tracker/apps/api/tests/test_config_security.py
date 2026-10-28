"""Settings fail-fast tests for production and staging configuration."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
STRONG_KEY = "a" * 64


def run_settings(
    extra_env: dict[str, str], script: str = "import config.settings; print('ok')"
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(
            (
                "APP_ENV",
                "COOKIE_",
                "CSRF_",
                "CORS_",
                "STORAGE_",
                "SECRET_KEY",
                "SECRET_ACCESS_KEY",
                "RAILWAY_",
                "FRONTEND_ORIGIN",
                "BUCKET",
                "ENDPOINT",
                "REGION",
                "ACCESS_KEY_ID",
            )
        ):
            env.pop(name, None)
    env.update(
        {
            "APP_ENV": "production",
            "SECRET_KEY": STRONG_KEY,
            "COOKIE_SECURE": "true",
            "COOKIE_SAMESITE": "Lax",
            "STORAGE_MODE": "s3",
            "STORAGE_BUCKET": "synthetic-evidence",
            "STORAGE_ACCESS_KEY_ID": "synthetic-access",
            "STORAGE_SECRET_ACCESS_KEY": "synthetic-secret",
            "ALLOWED_HOSTS": "tracker.example.org",
            "CORS_ALLOWED_ORIGINS": "https://tracker.example.org",
            "CSRF_TRUSTED_ORIGINS": "https://tracker.example.org",
        }
    )
    env.update(extra_env)
    return subprocess.run(  # noqa: S603 - test-only, script is a module constant
        [sys.executable, "-c", script],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_production_rejects_sample_secret_and_insecure_cookies():
    result = run_settings({"SECRET_KEY": "sample-development-only-secret-change-me"})
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr

    result = run_settings({"COOKIE_SECURE": "false"})
    assert result.returncode != 0
    assert "COOKIE_SECURE" in result.stderr

    result = run_settings({"STORAGE_MODE": "local"})
    assert result.returncode != 0
    assert "S3-compatible" in result.stderr


def test_production_rejects_short_secret_and_wildcard_cors():
    result = run_settings({"SECRET_KEY": "short"})
    assert result.returncode != 0
    assert "32 characters" in result.stderr

    result = run_settings(
        {"CORS_ALLOWED_ORIGINS": "*", "CORS_ALLOW_CREDENTIALS": "true"}
    )
    assert result.returncode != 0
    assert "CORS wildcard" in result.stderr


def test_secure_production_config_loads():
    result = run_settings({})
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_production_rejects_insecure_frontend_origin():
    result = run_settings({"FRONTEND_ORIGIN": "http://tracker.example.org"})
    assert result.returncode != 0
    assert "FRONTEND_ORIGIN must use https://" in result.stderr


def test_railway_host_and_bucket_variables_are_supported():
    script = (
        "import config.settings as s; "
        "print(s.STORAGE_BUCKET, s.STORAGE_ACCESS_KEY_ID, s.STORAGE_ENDPOINT_URL, "
        "s.STORAGE_REGION, "
        "'corn-api.up.railway.app' in s.ALLOWED_HOSTS, "
        "'healthcheck.railway.app' in s.ALLOWED_HOSTS, "
        "'https://corn-app.vercel.app' in s.CORS_ALLOWED_ORIGINS, "
        "'https://corn-app.vercel.app' in s.CSRF_TRUSTED_ORIGINS)"
    )
    result = run_settings(
        {
            "STORAGE_BUCKET": "",
            "STORAGE_ACCESS_KEY_ID": "",
            "STORAGE_SECRET_ACCESS_KEY": "",
            "BUCKET": "railway-evidence",
            "ACCESS_KEY_ID": "railway-access",
            "SECRET_ACCESS_KEY": "railway-secret",
            "ENDPOINT": "https://t3.storageapi.dev",
            "REGION": "auto",
            "RAILWAY_PUBLIC_DOMAIN": "corn-api.up.railway.app",
            "FRONTEND_ORIGIN": "https://corn-app.vercel.app",
        },
        script=script,
    )
    assert result.returncode == 0, result.stderr
    assert (
        "railway-evidence railway-access https://t3.storageapi.dev auto True True True True"
        in result.stdout
    )


def test_raw_upload_limit_covers_configured_evidence_cap():
    from django.conf import settings

    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE > settings.MAX_EVIDENCE_UPLOAD_BYTES


def test_development_allows_local_defaults():
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(("APP_ENV", "COOKIE_", "SECRET_KEY", "STORAGE_")):
            env.pop(name, None)
    env["APP_ENV"] = "development"
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings; print(config.settings.APP_ENV)"],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "development" in result.stdout
