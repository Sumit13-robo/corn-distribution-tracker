#!/usr/bin/env python3
"""Recreate the isolated E2E database before Playwright starts the API.

The maintenance connection is derived from E2E_DATABASE_URL by replacing the
database name with ``postgres``. The target name is validated so it can be
safely quoted in DDL. Everything in this database is synthetic test data.
"""

from __future__ import annotations

import os
import re
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

raw = os.environ.get("E2E_DATABASE_URL", "postgresql+psycopg://localhost:5432/corn_tracker_e2e")
url = make_url(raw)
database = url.database or ""
if not re.fullmatch(r"[A-Za-z0-9_]+", database):
    sys.exit(f"Refusing unsafe E2E database name: {database!r}")
if "e2e" not in database.lower():
    sys.exit(
        f"Refusing to drop {database!r}: the E2E database name must contain 'e2e' "
        "to prevent accidentally targeting a real database."
    )

maintenance_url = url.set(database="postgres")
engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT", future=True)
with engine.connect() as conn:
    conn.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
    conn.execute(text(f'CREATE DATABASE "{database}"'))
engine.dispose()
print(f"E2E database recreated: {database}")
