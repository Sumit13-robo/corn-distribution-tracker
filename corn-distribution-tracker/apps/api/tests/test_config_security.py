"""Settings fail-fast tests for production and staging configuration."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
STRONG_KEY = "a" * 64


def run_settings(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(("APP_ENV", "COOKIE_", "CSRF_", "CORS_", "STORAGE_", "SECRET_KEY")):
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
    return subprocess.run(
        [sys.executable, "-c", "import config.settings; print('ok')"],
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
