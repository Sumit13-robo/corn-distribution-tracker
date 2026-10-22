#!/usr/bin/env python3
"""Recreate the isolated E2E database before Playwright migrates it.

The maintenance connection is derived from E2E_DATABASE_URL by replacing the
database name with ``postgres``. The target name is validated so it can be
safely quoted in DDL. Everything in this database is synthetic test data.
"""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import unquote, urlparse

import psycopg
from psycopg import sql

raw = os.environ.get(
    "E2E_DATABASE_URL", "postgresql+psycopg://corn:corn@localhost:5432/corn_tracker_e2e"
)
if raw.startswith("postgresql+psycopg://"):
    raw = raw.replace("postgresql+psycopg://", "postgresql://", 1)
parsed = urlparse(raw)
database = parsed.path.lstrip("/")
if parsed.scheme not in {"postgres", "postgresql"}:
    sys.exit(f"Refusing non-PostgreSQL E2E database URL: {parsed.scheme!r}")
if not re.fullmatch(r"[A-Za-z0-9_]+", database):
    sys.exit(f"Refusing unsafe E2E database name: {database!r}")
if "e2e" not in database.lower():
    sys.exit(
        f"Refusing to drop {database!r}: the E2E database name must contain 'e2e' "
        "to prevent accidentally targeting a real database."
    )

maintenance = parsed._replace(path="/postgres", query="", fragment="").geturl()
with psycopg.connect(maintenance, autocommit=True) as conn:
    conn.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(database)))
    conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
print(f"E2E database recreated: {database}")
