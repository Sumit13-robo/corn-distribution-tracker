"""Django settings for the Corn Distribution Tracker API.

The canonical runtime configuration remains environment-driven (12-factor).
The API was deliberately migrated from FastAPI to Django + DRF at the product
owner's request; the HTTP contract and domain rules are preserved. See
docs/ops/IMPLEMENTATION_DECISIONS.md for the recorded deviation.

Production startup fails fast for insecure secrets, cookies, CORS or local
evidence storage. Development/testing keep convenient local defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parents[1]

# Load the repository-level .env first; real environment variables always win.
load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(BASE_DIR / ".env", override=False)

DEV_SAMPLE_SECRET = "sample-development-only-secret-change-me"  # noqa: S105 - rejected in production


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer.") from exc


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


APP_ENV = env("APP_ENV", "development").lower()
if APP_ENV not in {"development", "test", "staging", "production"}:
    raise ImproperlyConfigured("APP_ENV must be development, test, staging or production.")

SECRET_KEY = env("SECRET_KEY", DEV_SAMPLE_SECRET)
DEBUG = APP_ENV in {"development", "test"}
ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver" if not DEBUG else "*",
)
if APP_ENV == "production" and "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must not contain '*' in production.")
# Railway injects these hostnames. Adding them avoids a deploy-time mismatch
# while still requiring an explicit allowlist on every other platform.
railway_hosts: tuple[str, ...] = (
    env("RAILWAY_PUBLIC_DOMAIN"),
    env("RAILWAY_PRIVATE_DOMAIN"),
)
if any(railway_hosts):
    railway_hosts += ("healthcheck.railway.app",)
for railway_host in railway_hosts:
    if railway_host:
        railway_host = railway_host.removeprefix("https://").removeprefix("http://").rstrip("/")
    if railway_host and railway_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(railway_host)

API_V1_PREFIX = env("API_V1_PREFIX", "/api/v1")
APP_NAME = env("APP_NAME", "Corn Distribution Tracker")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
_DATABASE_URL = env("DATABASE_URL", "postgresql+psycopg://corn:corn@localhost:5432/corn_tracker")
_parsed = urlparse(_DATABASE_URL)
if _parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}:
    raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL (postgresql+psycopg://...).")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(_parsed.path.lstrip("/")) or "corn_tracker",
        "USER": unquote(_parsed.username or ""),
        "PASSWORD": unquote(_parsed.password or ""),
        "HOST": _parsed.hostname or "localhost",
        "PORT": str(_parsed.port or 5432),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
    }
}

# ---------------------------------------------------------------------------
# Applications / middleware
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "corsheaders",
    "rest_framework",
    "corn",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "corn.middleware.RequestContextMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "corn.middleware.OriginCheckMiddleware",
    "corn.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {},
    }
]

APPEND_SLASH = False

# ---------------------------------------------------------------------------
# Auth / sessions
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "corn.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = env("SESSION_COOKIE_NAME", "sessionid")
SESSION_COOKIE_AGE = env_int("SESSION_TTL_DAYS", 14) * 86400
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env_bool("COOKIE_SECURE", False)
SESSION_COOKIE_SAMESITE = (env("COOKIE_SAMESITE", "Lax") or "Lax").title()
SESSION_COOKIE_DOMAIN = env("COOKIE_DOMAIN") or None
SESSION_SAVE_EVERY_REQUEST = False

CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

# ---------------------------------------------------------------------------
# CORS / browser security
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
CORS_ALLOW_CREDENTIALS = env_bool("CORS_ALLOW_CREDENTIALS", True)
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "idempotency-key",
    "x-csrftoken",
    "x-request-id",
]
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

# A single deployment origin keeps CORS, CSRF and cookie settings in sync. The
# Vercel rewrite proxies /api to Railway, so the browser stays same-origin.
FRONTEND_ORIGIN = env("FRONTEND_ORIGIN").rstrip("/")
if FRONTEND_ORIGIN:
    if FRONTEND_ORIGIN not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(FRONTEND_ORIGIN)
    if FRONTEND_ORIGIN not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(FRONTEND_ORIGIN)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Set when TLS is terminated by a trusted reverse proxy. Never enable this when
# clients can spoof the forwarding header directly.
if env_bool("TRUST_X_FORWARDED_PROTO", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Only trust X-Forwarded-For when the app is behind a proxy that overwrites the
# header. Enabling this while the app is directly reachable lets clients spoof
# their source IP and bypass per-IP rate limits.
TRUST_X_FORWARDED_FOR = env_bool("TRUST_X_FORWARDED_FOR", False)
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0)
if SECURE_HSTS_SECONDS:
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "corn.auth.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "corn.errors.drf_exception_handler",
    "UNAUTHENTICATED_USER": None,
}

# ---------------------------------------------------------------------------
# Evidence storage
# ---------------------------------------------------------------------------
STORAGE_MODE = env("STORAGE_MODE", "local").lower()
# Railway Buckets auto-inject BUCKET/ENDPOINT/REGION/ACCESS_KEY_ID/
# SECRET_ACCESS_KEY. Prefer explicit STORAGE_* names, then fall back to those
# provider names so the bucket can be connected without duplicating secrets.
STORAGE_ENDPOINT_URL = env("STORAGE_ENDPOINT_URL") or env("ENDPOINT")
STORAGE_REGION = env("STORAGE_REGION") or env("REGION")
STORAGE_BUCKET = env("STORAGE_BUCKET") or env("BUCKET")
STORAGE_ACCESS_KEY_ID = env("STORAGE_ACCESS_KEY_ID") or env("ACCESS_KEY_ID")
STORAGE_SECRET_ACCESS_KEY = env("STORAGE_SECRET_ACCESS_KEY") or env("SECRET_ACCESS_KEY")
# "auto" keeps boto3's default; set "virtual" for Railway Buckets and
# "path" for providers that require path-style URLs.
STORAGE_ADDRESSING_STYLE = env("STORAGE_ADDRESSING_STYLE", "auto").lower()
STORAGE_SIGNED_URL_TTL_SECONDS = env_int("STORAGE_SIGNED_URL_TTL_SECONDS", 120)
STORAGE_SERVER_SIDE_ENCRYPTION = env("STORAGE_SERVER_SIDE_ENCRYPTION", "AES256")
STORAGE_KMS_KEY_ID = env("STORAGE_KMS_KEY_ID")
LOCAL_STORAGE_DIR = env("LOCAL_STORAGE_DIR", "./storage-data")
MAX_EVIDENCE_UPLOAD_BYTES = env_int("MAX_EVIDENCE_UPLOAD_BYTES", 10 * 1024 * 1024)
MAX_EVIDENCE_PIXELS = env_int("MAX_EVIDENCE_PIXELS", 40_000_000)
EVIDENCE_UPLOAD_TTL_SECONDS = env_int("EVIDENCE_UPLOAD_TTL_SECONDS", 900)
# Django's request.body guard defaults to 2.5 MiB, which is smaller than the
# evidence cap and made ordinary phone photos fail with a 500 before the
# service could validate or store them. Keep the raw-body ceiling just above
# the configured evidence cap; the service still rejects oversize payloads.
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_EVIDENCE_UPLOAD_BYTES + 1024 * 1024
ALLOWED_EVIDENCE_CONTENT_TYPES = env_list(
    "ALLOWED_EVIDENCE_CONTENT_TYPES", "image/jpeg,image/png,image/webp"
)
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:8000")

# Organization defaults (the database row overrides these after bootstrap).
ORG_TIMEZONE = env("ORG_TIMEZONE", "Asia/Kolkata")
DEFAULT_GEOFENCE_RADIUS_M = env_int("DEFAULT_GEOFENCE_RADIUS_M", 200)
MAX_ACCEPTABLE_GPS_ACCURACY_M = env_int("MAX_ACCEPTABLE_GPS_ACCURACY_M", 100)
MAX_LOCATION_AGE_SECONDS = env_int("MAX_LOCATION_AGE_SECONDS", 300)
MAX_CAPTURE_TIME_DRIFT_SECONDS = env_int("MAX_CAPTURE_TIME_DRIFT_SECONDS", 600)

# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "default"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "corn": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


def validate_security() -> None:
    """Fail fast for insecure production/staging configuration."""
    problems: list[str] = []
    if APP_ENV in {"production", "staging"} and SECRET_KEY == DEV_SAMPLE_SECRET:
        problems.append("SECRET_KEY must be replaced with a high-entropy secret.")
    if APP_ENV in {"production", "staging"} and len(SECRET_KEY) < 32:
        problems.append("SECRET_KEY must contain at least 32 characters.")
    if APP_ENV in {"production", "staging"} and DEBUG:
        problems.append("DEBUG must be false outside development and tests.")
    if FRONTEND_ORIGIN and not FRONTEND_ORIGIN.startswith("https://") and APP_ENV in {
        "production",
        "staging",
    }:
        problems.append("FRONTEND_ORIGIN must use https:// outside development.")
    if APP_ENV == "production":
        if not SESSION_COOKIE_SECURE or not CSRF_COOKIE_SECURE:
            problems.append("COOKIE_SECURE=true is required in production.")
        if SESSION_COOKIE_SAMESITE not in {"Lax", "Strict", "None"}:
            problems.append("COOKIE_SAMESITE must be Lax, Strict or None.")
        if SESSION_COOKIE_SAMESITE == "None" and not SESSION_COOKIE_SECURE:
            problems.append("SameSite=None requires Secure cookies.")
        if "*" in CORS_ALLOWED_ORIGINS and CORS_ALLOW_CREDENTIALS:
            problems.append("CORS wildcard origin cannot be combined with credentials.")
        if STORAGE_MODE != "s3":
            problems.append("Private S3-compatible evidence storage is required in production.")
        elif not (STORAGE_BUCKET and STORAGE_ACCESS_KEY_ID and STORAGE_SECRET_ACCESS_KEY):
            problems.append("Storage credentials are required when STORAGE_MODE=s3.")
    if SESSION_COOKIE_SAMESITE == "None" and not SESSION_COOKIE_SECURE:
        problems.append("SameSite=None requires Secure cookies.")
    if EVIDENCE_UPLOAD_TTL_SECONDS <= 0:
        problems.append("EVIDENCE_UPLOAD_TTL_SECONDS must be positive.")
    if MAX_EVIDENCE_PIXELS <= 0:
        problems.append("MAX_EVIDENCE_PIXELS must be positive.")
    if STORAGE_ADDRESSING_STYLE not in {"auto", "path", "virtual"}:
        problems.append("STORAGE_ADDRESSING_STYLE must be auto, path or virtual.")
    if problems:
        raise ImproperlyConfigured(
            f"Insecure configuration for APP_ENV={APP_ENV}: " + "; ".join(problems)
        )


validate_security()
