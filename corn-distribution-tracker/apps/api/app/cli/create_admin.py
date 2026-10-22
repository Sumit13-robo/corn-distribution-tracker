"""One-time controlled first-admin bootstrap CLI.

Usage:
  python -m app.cli.create_admin --email ops@example.org            # prompts for password
  INITIAL_ADMIN_PASSWORD_ENV=SETUP_PW python -m app.cli.create_admin --email ops@example.org

The password is never passed on the command line, never logged, and the command refuses
to run when an administrator already exists (public role elevation is impossible).
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from app.core.errors import AppError
from app.db.session import new_session
from app.services import auth_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the first administrator account (one-time).")
    parser.add_argument("--email", required=True, help="Administrator email")
    parser.add_argument("--display-name", default="Administrator")
    args = parser.parse_args()

    env_var = os.environ.get("INITIAL_ADMIN_PASSWORD_ENV")
    if env_var:
        password = os.environ.get(env_var, "")
        if not password:
            print(f"Environment variable {env_var} is not set.", file=sys.stderr)
            return 2
        confirm = password
    else:
        password = getpass.getpass("Password for the first admin: ")
        confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 2

    db = new_session()
    try:
        user = auth_service.create_first_admin(
            db, email=args.email, password=password, display_name=args.display_name
        )
        auth_service.ensure_core_org_rows(db)
        db.commit()
        print(f"Administrator created: {user.email_normalized}")
        print("Organization settings and the central stock account were ensured.")
        print(
            "Next: create campaigns/sites/assignments, invite distributors, "
            "and record the first stock receipt."
        )
        return 0
    except AppError as exc:
        db.rollback()
        print(f"FAILED: {exc.message}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
