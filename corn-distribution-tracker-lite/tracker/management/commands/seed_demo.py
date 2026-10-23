"""Create a small synthetic world for clicking through the Lite workflow.

Passwords come from environment variables when supplied; otherwise a random
password is generated and printed once. The command is idempotent and never
resets an existing account's password.
"""

from __future__ import annotations

import os
import secrets
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from tracker.models import Assignment, Campaign, Delivery, Role, Site, StockMovement, User
from tracker.services import (
    central_account,
    distributor_account,
    post_allocation,
    post_receipt,
    site_account,
    submit_delivery,
)


class Command(BaseCommand):
    help = "Seed synthetic campaign, sites, distributors, assignments and stock."

    def handle(self, *args, **options):
        with transaction.atomic():
            admin, admin_password = self._user(
                "admin@example.org",
                "Local Administrator",
                Role.ADMIN,
                "LITE_ADMIN_PASSWORD",
                staff=True,
            )
            amina, amina_password = self._user(
                "amina@example.org", "Amina Deng", Role.DISTRIBUTOR, "LITE_AMINA_PASSWORD"
            )
            john, john_password = self._user(
                "john@example.org", "John Lado", Role.DISTRIBUTOR, "LITE_JOHN_PASSWORD"
            )

            campaign, _ = Campaign.objects.get_or_create(
                code="RAINS-26",
                defaults={
                    "name": "Rains distribution 2026",
                    "status": Campaign.Status.ACTIVE,
                    "notes": "Synthetic demo campaign.",
                },
            )
            site_one, _ = Site.objects.get_or_create(
                code="SITE-001",
                defaults={
                    "name": "Central School",
                    "region": "Central",
                    "address": "Synthetic address, Juba",
                },
            )
            site_two, _ = Site.objects.get_or_create(
                code="SITE-002",
                defaults={
                    "name": "Riverside Store",
                    "region": "Central",
                    "address": "Synthetic address, Juba",
                },
            )

            assignment_one, _ = Assignment.objects.get_or_create(
                campaign=campaign,
                site=site_one,
                distributor=amina,
                defaults={"target_kg": "500.000", "notes": "Demo assignment."},
            )
            Assignment.objects.get_or_create(
                campaign=campaign,
                site=site_two,
                distributor=john,
                defaults={"target_kg": "400.000", "notes": "Demo assignment."},
            )

            central_account()
            site_account(site_one)
            site_account(site_two)
            distributor_account(amina)
            distributor_account(john)

            if not StockMovement.objects.exists():
                post_receipt(
                    quantity_kg=Decimal("2000.000"),
                    actor=admin,
                    note="Opening synthetic stock",
                )
                post_allocation(
                    distributor=amina,
                    quantity_kg=Decimal("500.000"),
                    actor=admin,
                    note="Initial allocation",
                )
                post_allocation(
                    distributor=john,
                    quantity_kg=Decimal("400.000"),
                    actor=admin,
                    note="Initial allocation",
                )

            if not Delivery.objects.exists():
                submit_delivery(
                    assignment=assignment_one,
                    distributor=amina,
                    quantity_kg=Decimal("150.000"),
                    notes="Synthetic delivery waiting for review.",
                )

        self.stdout.write(self.style.SUCCESS("Lite demo data is ready."))
        self.stdout.write("")
        self._credential("Admin", admin.email, admin_password)
        self._credential("Distributor (Amina)", amina.email, amina_password)
        self._credential("Distributor (John)", john.email, john_password)
        self.stdout.write("")
        self.stdout.write("Start the server: python manage.py runserver 127.0.0.1:8001")
        self.stdout.write("Open: http://127.0.0.1:8001/")
        self.stdout.write("Existing accounts keep their current passwords and are not printed.")

    def _user(self, email, display_name, role, env_name, *, staff=False):
        password = os.environ.get(env_name) or secrets.token_urlsafe(12)
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "display_name": display_name,
                "role": role,
                "is_active": True,
                "is_staff": staff,
                "is_superuser": staff,
            },
        )
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user, password if created else "(existing account — password unchanged)"

    def _credential(self, label, email, password):
        self.stdout.write(f"{label}: {email} / {password}")
