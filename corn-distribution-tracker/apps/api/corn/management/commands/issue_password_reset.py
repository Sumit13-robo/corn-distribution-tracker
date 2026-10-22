"""Operator command for password-reset delivery.

There is no mail transport in this deployment. An operator with database/console
access can issue a single-use, one-hour reset link and hand it to the account
holder through the organization's secure channel. The raw token is printed once
and never stored or logged by the application.
"""

from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from corn.services import auth as auth_service


class Command(BaseCommand):
    help = "Issue a one-time password-reset token for an active account."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument(
            "--web-base-url",
            default="",
            help="Public SPA origin used to print a clickable reset link (optional).",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            raw = auth_service.issue_password_reset(email=options["email"])
        if raw is None:
            # Do not distinguish "unknown email" from "inactive account" in logs.
            self.stdout.write("No reset token was issued for that address.")
            return
        self.stdout.write(self.style.SUCCESS("One-time reset token issued (valid for one hour):"))
        self.stdout.write(raw)
        base = options["web_base_url"].strip().rstrip("/")
        if base:
            self.stdout.write(
                f"Reset link: {base}/reset-password?mode=reset&token={quote(raw)}"
            )
        else:
            self.stdout.write(
                "Pass --web-base-url to print a clickable link."
            )
        if not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING("Deliver this token only through an authenticated secure channel.")
            )
