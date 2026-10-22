"""Deterministic test settings: isolated PostgreSQL schema and private temp storage.

Every value here is synthetic. Real environment variables are overridden so a
developer's local `.env` cannot redirect the suite at a real database.
"""

from __future__ import annotations

import os
import tempfile

os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+psycopg://corn:corn@localhost:5432/corn_tracker_test",
        ),
        "SECRET_KEY": "test-only-secret-not-for-production-0123456789abcdef",
        "CORS_ALLOWED_ORIGINS": "http://localhost:5173",
        "CSRF_TRUSTED_ORIGINS": "http://localhost:5173",
        "COOKIE_SECURE": "false",
        "COOKIE_SAMESITE": "Lax",
        "STORAGE_MODE": "local",
        "LOCAL_STORAGE_DIR": os.environ.get(
            "TEST_LOCAL_STORAGE_DIR", tempfile.mkdtemp(prefix="corn-test-evidence-")
        ),
        "PUBLIC_BASE_URL": "http://testserver",
        "MAX_EVIDENCE_UPLOAD_BYTES": "1048576",
        "LOG_LEVEL": "WARNING",
    }
)

from config.settings import *  # noqa: E402,F403
