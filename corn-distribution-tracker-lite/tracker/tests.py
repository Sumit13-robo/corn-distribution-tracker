"""Tests for the Lite edition: permissions, stock rules and the core workflow."""

from __future__ import annotations

import base64
import shutil
import tempfile
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Activity,
    Assignment,
    Campaign,
    Delivery,
    Role,
    Site,
    StockAccount,
    StockMovement,
)
from .services import (
    approve_delivery,
    available_kg_for,
    central_account,
    distributor_account,
    post_allocation,
    post_receipt,
    reject_delivery,
    site_account,
    submit_delivery,
    target_kg,
)

User = get_user_model()

PHOTO_ROOT = tempfile.mkdtemp(prefix="corn-lite-tests-")


def tearDownModule():
    shutil.rmtree(PHOTO_ROOT, ignore_errors=True)


class LiteFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email="admin@example.org",
            password="AdminTest!234",
            display_name="Admin Person",
            role=Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        cls.amina = User.objects.create_user(
            email="amina@example.org",
            password="AminaTest!234",
            display_name="Amina Deng",
            role=Role.DISTRIBUTOR,
        )
        cls.john = User.objects.create_user(
            email="john@example.org",
            password="JohnTest!234",
            display_name="John Lado",
            role=Role.DISTRIBUTOR,
        )
        cls.campaign = Campaign.objects.create(code="TEST-26", name="Test campaign")
        cls.site = Site.objects.create(code="SITE-100", name="Test site", region="Central")
        cls.assignment = Assignment.objects.create(
            campaign=cls.campaign,
            site=cls.site,
            distributor=cls.amina,
            target_kg=Decimal("500.000"),
        )
        central_account()
        site_account(cls.site)
        distributor_account(cls.amina)
        distributor_account(cls.john)
        post_receipt(quantity_kg=Decimal("1000.000"), actor=cls.admin, note="Opening")
        post_allocation(
            distributor=cls.amina,
            quantity_kg=Decimal("400.000"),
            actor=cls.admin,
            note="Opening allocation",
        )
        post_allocation(
            distributor=cls.john,
            quantity_kg=Decimal("100.000"),
            actor=cls.admin,
            note="Opening allocation",
        )

    def setUp(self):
        cache.clear()


class WorkflowTests(LiteFixture):
    def test_receipt_and_allocation_balances_are_derived(self):
        self.assertEqual(central_account().balance_kg, Decimal("500.000"))
        self.assertEqual(distributor_account(self.amina).balance_kg, Decimal("400.000"))
        self.assertEqual(distributor_account(self.john).balance_kg, Decimal("100.000"))
        self.assertEqual(available_kg_for(self.amina), Decimal("400.000"))

    def test_allocation_cannot_overdraw_central_stock(self):
        with self.assertRaisesMessage(ValidationError, "Only 500 kg"):
            post_allocation(
                distributor=self.john,
                quantity_kg=Decimal("501.000"),
                actor=self.admin,
            )
        self.assertEqual(central_account().balance_kg, Decimal("500.000"))

    def test_submission_reserves_stock_and_cannot_be_double_spent(self):
        delivery = submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("150.000"),
            notes="First update",
        )
        self.assertEqual(delivery.status, Delivery.Status.SUBMITTED)
        self.assertEqual(available_kg_for(self.amina), Decimal("250.000"))
        with self.assertRaisesMessage(ValidationError, "Only 250 kg"):
            submit_delivery(
                assignment=self.assignment,
                distributor=self.amina,
                quantity_kg=Decimal("251.000"),
            )

    def test_approval_posts_stock_and_links_the_ledger_row(self):
        delivery = submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("150.000"),
        )
        approved = approve_delivery(delivery=delivery, reviewer=self.admin, note="Looks right")
        self.assertEqual(approved.status, Delivery.Status.APPROVED)
        self.assertIsNotNone(approved.stock_movement_id)
        self.assertEqual(approved.reviewed_by, self.admin)
        self.assertEqual(distributor_account(self.amina).balance_kg, Decimal("250.000"))
        self.assertEqual(site_account(self.site).balance_kg, Decimal("150.000"))
        self.assertEqual(available_kg_for(self.amina), Decimal("250.000"))
        self.assertTrue(StockMovement.objects.filter(pk=approved.stock_movement_id).exists())
        with self.assertRaisesMessage(ValidationError, "Only submitted deliveries"):
            approve_delivery(delivery=approved, reviewer=self.admin)

    def test_rejection_releases_reservation_without_moving_stock(self):
        delivery = submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("150.000"),
        )
        rejected = reject_delivery(delivery=delivery, reviewer=self.admin, note="Photo unreadable")
        self.assertEqual(rejected.status, Delivery.Status.REJECTED)
        self.assertEqual(rejected.review_note, "Photo unreadable")
        self.assertEqual(distributor_account(self.amina).balance_kg, Decimal("400.000"))
        self.assertEqual(available_kg_for(self.amina), Decimal("400.000"))
        self.assertEqual(site_account(self.site).balance_kg, Decimal("0.000"))
        self.assertFalse(StockMovement.objects.filter(kind=StockMovement.Kind.DELIVERY).exists())

    def test_rejection_requires_a_reason(self):
        delivery = submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("25.000"),
        )
        with self.assertRaisesMessage(ValidationError, "rejection reason"):
            reject_delivery(delivery=delivery, reviewer=self.admin, note="   ")
        self.assertEqual(delivery.status, Delivery.Status.SUBMITTED)

    def test_inactive_assignment_and_campaign_block_submission(self):
        self.assignment.status = Assignment.Status.COMPLETE
        self.assignment.save(update_fields=["status"])
        with self.assertRaisesMessage(ValidationError, "no longer active"):
            submit_delivery(
                assignment=self.assignment,
                distributor=self.amina,
                quantity_kg=Decimal("10.000"),
            )

        self.assignment.status = Assignment.Status.ACTIVE
        self.assignment.save(update_fields=["status"])
        self.campaign.status = Campaign.Status.CLOSED
        self.campaign.save(update_fields=["status"])
        with self.assertRaisesMessage(ValidationError, "campaign is no longer active"):
            submit_delivery(
                assignment=self.assignment,
                distributor=self.amina,
                quantity_kg=Decimal("10.000"),
            )
        self.assertEqual(target_kg(distributor=self.amina), Decimal("0"))
        self.assertEqual(target_kg(), Decimal("0"))

    def test_inactive_site_blocks_submission(self):
        Site.objects.filter(pk=self.site.pk).update(is_active=False)
        assignment = Assignment.objects.select_related("site", "campaign").get(
            pk=self.assignment.pk
        )
        with self.assertRaisesMessage(ValidationError, "site is inactive"):
            submit_delivery(
                assignment=assignment,
                distributor=self.amina,
                quantity_kg=Decimal("10.000"),
            )
        self.assertEqual(available_kg_for(self.amina), Decimal("400.000"))

    def test_activity_is_recorded_for_stock_changes(self):
        self.assertTrue(Activity.objects.filter(action="Stock receipt").exists())
        self.assertTrue(Activity.objects.filter(action="Stock allocation").exists())


class AccessTests(LiteFixture):
    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_distributor_cannot_reach_admin_pages(self):
        self.client.force_login(self.amina)
        for name in ("campaigns", "sites", "people", "assignments", "inventory", "activity"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_admin_cannot_reach_distributor_submission_form(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("delivery_create")).status_code, 403)

    def test_distributor_only_sees_own_deliveries(self):
        mine = submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("10.000"),
        )
        john_assignment = Assignment.objects.create(
            campaign=self.campaign,
            site=self.site,
            distributor=self.john,
            target_kg=Decimal("100.000"),
        )
        theirs = submit_delivery(
            assignment=john_assignment,
            distributor=self.john,
            quantity_kg=Decimal("5.000"),
        )
        self.client.force_login(self.amina)
        response = self.client.get(reverse("deliveries"))
        self.assertContains(response, "Amina Deng")
        self.assertNotContains(response, "John Lado")
        self.assertEqual(
            self.client.get(reverse("delivery_detail", args=[theirs.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.get(reverse("delivery_photo", args=[theirs.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.get(reverse("delivery_detail", args=[mine.pk])).status_code, 200
        )

    def test_admin_can_see_every_delivery(self):
        submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("12.000"),
        )
        john_assignment = Assignment.objects.create(
            campaign=self.campaign,
            site=self.site,
            distributor=self.john,
            target_kg=Decimal("100.000"),
        )
        submit_delivery(
            assignment=john_assignment,
            distributor=self.john,
            quantity_kg=Decimal("5.000"),
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("deliveries"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Amina Deng")
        self.assertContains(response, "John Lado")


class ViewSmokeTests(LiteFixture):
    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_admin_pages_render(self):
        submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("15.000"),
        )
        self.client.force_login(self.admin)
        names = [
            "dashboard",
            "campaigns",
            "campaign_create",
            "sites",
            "site_create",
            "people",
            "distributor_create",
            "assignments",
            "assignment_create",
            "inventory",
            "receipt_create",
            "allocation_create",
            "deliveries",
            "activity",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        detail = Delivery.objects.get()
        self.assertEqual(
            self.client.get(reverse("delivery_detail", args=[detail.pk])).status_code, 200
        )

    def test_distributor_pages_render(self):
        self.client.force_login(self.amina)
        for name in ("dashboard", "deliveries", "delivery_create"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_review_post_approves_and_posts_stock(self):
        delivery = submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("20.000"),
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("delivery_review", args=[delivery.pk]),
            {"decision": "APPROVE", "note": "Approved in test"},
        )
        self.assertRedirects(response, reverse("delivery_detail", args=[delivery.pk]))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, Delivery.Status.APPROVED)
        self.assertEqual(site_account(self.site).balance_kg, Decimal("20.000"))

    def test_distributor_cannot_post_a_review(self):
        delivery = submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("20.000"),
        )
        self.client.force_login(self.amina)
        response = self.client.post(
            reverse("delivery_review", args=[delivery.pk]),
            {"decision": "APPROVE", "note": "Self approval"},
        )
        self.assertEqual(response.status_code, 403)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, Delivery.Status.SUBMITTED)


@override_settings(MEDIA_ROOT=PHOTO_ROOT)
class FormTests(LiteFixture):
    PNG_1PX = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    def test_admin_creates_a_distributor_with_a_strong_password(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("distributor_create"),
            {
                "email": "new@example.org",
                "display_name": "New Person",
                "password1": "StrongPass!234",
                "password2": "StrongPass!234",
            },
        )
        self.assertRedirects(response, reverse("people"))
        user = User.objects.get(email="new@example.org")
        self.assertEqual(user.role, Role.DISTRIBUTOR)
        self.assertTrue(user.check_password("StrongPass!234"))
        self.assertTrue(StockAccount.objects.filter(owner=user).exists())

    def test_admin_distributor_form_rejects_a_weak_password(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("distributor_create"),
            {
                "email": "weak@example.org",
                "display_name": "Weak Password",
                "password1": "12345678",
                "password2": "12345678",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="weak@example.org").exists())
        self.assertContains(response, "This password is too common.")

    def test_delivery_form_accepts_a_real_image(self):
        upload = SimpleUploadedFile("evidence.png", self.PNG_1PX, content_type="image/png")
        self.client.force_login(self.amina)
        response = self.client.post(
            reverse("delivery_create"),
            {
                "assignment": self.assignment.pk,
                "quantity_kg": "25.000",
                "notes": "With evidence",
                "photo": upload,
            },
        )
        self.assertEqual(response.status_code, 302)
        delivery = Delivery.objects.get()
        self.assertTrue(delivery.photo)
        self.assertEqual(delivery.quantity_kg, Decimal("25.000"))

    def test_delivery_form_rejects_a_non_image(self):
        upload = SimpleUploadedFile(
            "evidence.jpg", b"not really an image", content_type="image/jpeg"
        )
        self.client.force_login(self.amina)
        response = self.client.post(
            reverse("delivery_create"),
            {
                "assignment": self.assignment.pk,
                "quantity_kg": "25.000",
                "notes": "Fake evidence",
                "photo": upload,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload a valid image")
        self.assertFalse(Delivery.objects.exists())


class AuthenticationTests(LiteFixture):
    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {"username": "admin@example.org", "password": "AdminTest!234"},
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_invalid_login_returns_401(self):
        response = self.client.post(
            reverse("login"),
            {"username": "admin@example.org", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertContains(response, "Sign-in failed", status_code=401)

    def test_successful_login_clears_previous_failures(self):
        for _ in range(4):
            self.client.post(
                reverse("login"),
                {"username": "admin@example.org", "password": "wrong"},
                REMOTE_ADDR="203.0.113.10",
            )
        response = self.client.post(
            reverse("login"),
            {"username": "admin@example.org", "password": "AdminTest!234"},
            REMOTE_ADDR="203.0.113.10",
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIsNone(cache.get("lite-login:203.0.113.10"))

    def test_failed_attempts_are_throttled(self):
        for _ in range(5):
            self.client.post(
                reverse("login"),
                {"username": "admin@example.org", "password": "wrong"},
                REMOTE_ADDR="203.0.113.11",
            )
        response = self.client.post(
            reverse("login"),
            {"username": "admin@example.org", "password": "wrong"},
            REMOTE_ADDR="203.0.113.11",
        )
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many sign-in attempts", status_code=429)

    def test_logout_requires_post(self):
        self.client.force_login(self.amina)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))


@override_settings(MEDIA_ROOT=PHOTO_ROOT)
class PhotoAccessTests(LiteFixture):
    def _delivery_with_photo(self):
        upload = SimpleUploadedFile(
            "evidence.jpg",
            b"\xff\xd8\xff\xe0 fake jpeg bytes",
            content_type="image/jpeg",
        )
        return submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("10.000"),
            photo=upload,
        )

    def test_owner_and_admin_can_read_private_photo(self):
        delivery = self._delivery_with_photo()
        for user in (self.amina, self.admin):
            self.client.force_login(user)
            response = self.client.get(reverse("delivery_photo", args=[delivery.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_other_distributor_cannot_read_photo(self):
        delivery = self._delivery_with_photo()
        self.client.force_login(self.john)
        self.assertEqual(
            self.client.get(reverse("delivery_photo", args=[delivery.pk])).status_code, 404
        )

    def test_photo_remains_available_after_approval(self):
        delivery = self._delivery_with_photo()
        approve_delivery(delivery=delivery, reviewer=self.admin, note="Photo checked")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("delivery_photo", args=[delivery.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_missing_photo_returns_404(self):
        delivery = submit_delivery(
            assignment=self.assignment,
            distributor=self.amina,
            quantity_kg=Decimal("11.000"),
        )
        self.client.force_login(self.amina)
        self.assertEqual(
            self.client.get(reverse("delivery_photo", args=[delivery.pk])).status_code, 404
        )


class SeedCommandTests(TestCase):
    def test_seed_is_idempotent_and_creates_the_demo_workflow(self):
        output = StringIO()
        with patch.dict(
            "os.environ",
            {
                "LITE_ADMIN_PASSWORD": "SeedAdmin!234",
                "LITE_AMINA_PASSWORD": "SeedAmina!234",
                "LITE_JOHN_PASSWORD": "SeedJohn!234",
            },
        ):
            call_command("seed_demo", stdout=output)
        self.assertTrue(User.objects.filter(email="admin@example.org").exists())
        self.assertEqual(StockMovement.objects.count(), 3)
        self.assertEqual(Delivery.objects.count(), 1)
        self.assertEqual(central_account().balance_kg, Decimal("1100.000"))

        with patch.dict("os.environ", {}, clear=True):
            call_command("seed_demo", stdout=output)
        self.assertEqual(StockMovement.objects.count(), 3)
        self.assertEqual(Delivery.objects.count(), 1)
        self.assertEqual(User.objects.count(), 3)
        admin = User.objects.get(email="admin@example.org")
        self.assertTrue(admin.check_password("SeedAdmin!234"))
        self.assertTrue(admin.is_staff)
