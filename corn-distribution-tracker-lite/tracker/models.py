"""Small, explicit domain model for the Lite edition.

The same core workflow as the full app is preserved:

    central stock receipt -> distributor allocation -> delivery submission
    -> admin review -> approved delivery posts distributor -> site stock.

Quantities are Decimal kilograms. Balances are derived from the append-only
stock-movement rows rather than cached on accounts, which keeps this edition
easy to audit and reason about.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    DISTRIBUTOR = "DISTRIBUTOR", "Distributor"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).strip().lower()
        extra.setdefault("role", Role.DISTRIBUTOR)
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("display_name", "Administrator")
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DISTRIBUTOR)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]
    EMAIL_FIELD = "email"

    objects = UserManager()

    class Meta:
        ordering = ["display_name", "email"]

    def __str__(self) -> str:
        return self.display_name or self.email

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def short_name(self) -> str:
        return self.display_name or self.email.split("@")[0]


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Campaign(TimeStamped):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class Site(TimeStamped):
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40, unique=True)
    region = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class Assignment(TimeStamped):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETE = "COMPLETE", "Complete"

    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name="assignments")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="assignments")
    distributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assignments",
        limit_choices_to={"role": Role.DISTRIBUTOR},
    )
    target_kg = models.DecimalField(
        max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))]
    )
    due_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "site", "distributor"],
                name="unique_lite_assignment",
            )
        ]

    def __str__(self) -> str:
        return f"{self.site.code} · {self.distributor.short_name}"

    @property
    def approved_kg(self) -> Decimal:
        total = self.deliveries.filter(status=Delivery.Status.APPROVED).aggregate(
            total=models.Sum("quantity_kg")
        )["total"]
        return total or Decimal("0")

    @property
    def pending_kg(self) -> Decimal:
        total = self.deliveries.filter(status=Delivery.Status.SUBMITTED).aggregate(
            total=models.Sum("quantity_kg")
        )["total"]
        return total or Decimal("0")

    @property
    def remaining_kg(self) -> Decimal:
        return max(self.target_kg - self.approved_kg, Decimal("0"))

    @property
    def progress_percent(self) -> int:
        if self.target_kg <= 0:
            return 0
        return min(100, int((self.approved_kg / self.target_kg) * 100))


class StockAccount(TimeStamped):
    class Kind(models.TextChoices):
        CENTRAL = "CENTRAL", "Central"
        DISTRIBUTOR = "DISTRIBUTOR", "Distributor"
        SITE = "SITE", "Site"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    name = models.CharField(max_length=160)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="stock_accounts",
    )
    site = models.ForeignKey(
        Site,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="stock_accounts",
    )

    class Meta:
        ordering = ["kind", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind"],
                condition=Q(kind="CENTRAL"),
                name="unique_lite_central_account",
            ),
            models.UniqueConstraint(
                fields=["owner"],
                condition=Q(kind="DISTRIBUTOR", owner__isnull=False),
                name="unique_lite_distributor_account",
            ),
            models.UniqueConstraint(
                fields=["site"],
                condition=Q(kind="SITE", site__isnull=False),
                name="unique_lite_site_account",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def balance_kg(self) -> Decimal:
        incoming = self.incoming.aggregate(total=models.Sum("quantity_kg"))["total"] or Decimal("0")
        outgoing = self.outgoing.aggregate(total=models.Sum("quantity_kg"))["total"] or Decimal("0")
        return incoming - outgoing


class StockMovement(models.Model):
    class Kind(models.TextChoices):
        RECEIPT = "RECEIPT", "Receipt"
        ALLOCATION = "ALLOCATION", "Allocation"
        DELIVERY = "DELIVERY", "Delivery"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    source = models.ForeignKey(
        StockAccount,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outgoing",
    )
    destination = models.ForeignKey(
        StockAccount,
        on_delete=models.PROTECT,
        related_name="incoming",
    )
    quantity_kg = models.DecimalField(
        max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))]
    )
    note = models.CharField(max_length=300, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} · {self.quantity_kg} kg"


def validate_photo_size(upload) -> None:
    limit = 5 * 1024 * 1024
    if upload.size > limit:
        raise ValidationError("Evidence photos must be 5 MB or smaller.")


class Delivery(TimeStamped):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Awaiting review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT, related_name="deliveries")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="deliveries")
    distributor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="deliveries"
    )
    quantity_kg = models.DecimalField(
        max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))]
    )
    notes = models.TextField(blank=True)
    photo = models.FileField(
        upload_to="delivery_photos/%Y/%m/",
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_photo_size,
        ],
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_deliveries",
    )
    review_note = models.TextField(blank=True)
    stock_movement = models.OneToOneField(
        StockMovement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delivery",
    )

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity_kg__gt=0), name="lite_delivery_quantity_positive"
            )
        ]
        indexes = [
            models.Index(fields=["status"], name="ix_lite_delivery_status"),
            models.Index(fields=["distributor", "status"], name="ix_lite_delivery_owner_status"),
        ]

    def __str__(self) -> str:
        return f"{self.site.code} · {self.quantity_kg} kg · {self.get_status_display()}"

    @property
    def has_photo(self) -> bool:
        return bool(self.photo)


class Activity(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    action = models.CharField(max_length=80)
    detail = models.CharField(max_length=300)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.action}: {self.detail}"
