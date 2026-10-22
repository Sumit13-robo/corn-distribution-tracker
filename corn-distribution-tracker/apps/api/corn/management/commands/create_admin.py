"""One-time controlled first-administrator bootstrap.

Usage:
    python manage.py create_admin --email ops@example.org
    INITIAL_ADMIN_PASSWORD_ENV=SETUP_PW python manage.py create_admin --email ops@example.org

The password is never passed on the command line or logged. The command refuses
to create a second administrator; use invitations for additional accounts.
"""

from __future__ import annotations

import getpass
import os
import sys

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from corn.errors import AppError
from corn.services import auth as auth_service


class Command(BaseCommand):
    help = "Create the first administrator, organization settings and central stock account."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Administrator email address")
        parser.add_argument("--display-name", default="Administrator")
        parser.add_argument(
            "--password-env",
            default="INITIAL_ADMIN_PASSWORD_ENV",
            help="Environment variable that holds the password (interactive prompt if unset).",
        )

    def handle(self, *args, **options):
        email = options["email"]
        display_name = options["display_name"]
        env_name = options["password_env"]
        password = os.environ.get(env_name, "")
        if password:
            confirm = password
        else:
            password = getpass.getpass("Password for the first admin: ")
            confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise CommandError("Passwords do not match.")
        try:
            with transaction.atomic():
                user = auth_service.create_first_admin(
                    email=email,
                    password=password,
                    display_name=display_name,
                )
        except AppError as exc:
            self.stderr.write(f"FAILED: {exc.message}")
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS(f"Administrator created: {user.email}"))
        self.stdout.write("Organization settings and the central stock account were ensured.")
        self.stdout.write(
            "Next: create campaigns/sites/assignments, invite distributors, "
            "and record the first stock receipt."
        )
