"""Django ORM models for the Corn Distribution Tracker.

Schema parity notes:
- quantities are NUMERIC(14,3) kg and serialized as decimal strings;
- pending SUBMITTED records are reservations, never postings;
- stock_movements and audit_events are append-only (DB triggers in migration 0002);
- evidence objects live in private storage; rows hold only metadata.

The schema is a Django-native replacement for the former Alembic schema. It is
intentionally close to the documented domain model so the API contract and
business rules remain unchanged.
"""

from __future__ import annotations

import uuid
from typing import ClassVar, cast

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .enums import (
    AccountType,
    AssignmentStatus,
    CampaignStatus,
    CaptureSource,
    DisplayUnit,
    EvidenceLifecycle,
    GeoStatus,
    IntentPurpose,
    MovementType,
    RecordStatus,
    Role,
)


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra):
        if not email:
            raise ValueError("An email address is required.")
        user = cast("User", self.model(email=self.normalize_email(email).strip().lower(), **extra))
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_active", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=320, unique=True)
    display_name = models.CharField(max_length=120)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DISTRIBUTOR)
    is_active = models.BooleanField(default=False)
    must_reset_password = models.BooleanField(default=False)
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []
    EMAIL_FIELD = "email"

    objects = UserManager()

    class Meta:
        db_table = "users"
        ordering = ["display_name", "email"]

    def __str__(self) -> str:
        return f"{self.display_name} <{self.email}>"

    @property
    def email_normalized(self) -> str:
        """Compatibility alias used by the original service layer."""
        return self.email

    @property
    def last_login_at(self):
        return self.last_login

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN


class Campaign(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    reference_code = models.CharField(max_length=40, unique=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT)
    timezone = models.CharField(max_length=64, default="UTC")
    notes = models.CharField(max_length=2000, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "campaigns"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference_code} - {self.name}"


class DistributionSite(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    site_code = models.CharField(max_length=40, unique=True)
    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sites",
    )
    address_text = models.CharField(max_length=500, null=True, blank=True)
    region = models.CharField(max_length=120, null=True, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
    geofence_radius_m = models.PositiveIntegerField(default=200)
    max_acceptable_accuracy_m = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "distribution_sites"
        ordering = ["site_code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(latitude__gte=-90, latitude__lte=90), name="site_lat_range"
            ),
            models.CheckConstraint(
                condition=Q(longitude__gte=-180, longitude__lte=180), name="site_lng_range"
            ),
            models.CheckConstraint(condition=Q(geofence_radius_m__gt=0), name="site_geofence_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.site_code} - {self.name}"


class DistributorAssignment(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.SET_NULL, related_name="assignments"
    )
    site = models.ForeignKey(DistributionSite, on_delete=models.CASCADE, related_name="assignments")
    distributor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignments"
    )
    target_quantity_kg = models.DecimalField(max_digits=14, decimal_places=3)
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=AssignmentStatus.choices, default=AssignmentStatus.ACTIVE
    )
    notes = models.CharField(max_length=1000, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "distributor_assignments"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(target_quantity_kg__gt=0), name="assignment_target_positive"
            ),
            models.UniqueConstraint(
                fields=["campaign", "site", "distributor_user"],
                condition=Q(status__in=["ACTIVE", "PAUSED"]),
                name="uq_assignment_open",
            ),
        ]
        indexes = [models.Index(fields=["distributor_user"], name="ix_assignments_distributor")]

    def __str__(self) -> str:
        return f"Assignment {self.id}"


class DistributionRecord(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.SET_NULL, related_name="records"
    )
    assignment = models.ForeignKey(
        DistributorAssignment, on_delete=models.RESTRICT, related_name="records"
    )
    site = models.ForeignKey(DistributionSite, on_delete=models.RESTRICT, related_name="records")
    distributor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name="distribution_records"
    )
    quantity_kg = models.DecimalField(max_digits=14, decimal_places=3)
    status = models.CharField(max_length=20, choices=RecordStatus.choices, default=RecordStatus.SUBMITTED)
    idempotency_key = models.CharField(max_length=64)
    client_created_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_distribution_records",
    )
    review_reason = models.CharField(max_length=2000, null=True, blank=True)
    stock_movement = models.OneToOneField(
        "StockMovement",
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="approved_record",
    )
    notes = models.CharField(max_length=2000, null=True, blank=True)
    location_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    location_accuracy_m = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location_timestamp = models.DateTimeField(null=True, blank=True)
    device_reported_location_time = models.DateTimeField(null=True, blank=True)
    distance_to_site_m = models.DecimalField(max_digits=12, decimal_places=1, null=True, blank=True)
    geo_status = models.CharField(max_length=20, choices=GeoStatus.choices, default=GeoStatus.UNAVAILABLE)
    geo_flags = models.JSONField(default=list, blank=True)
    review_exception_reason = models.CharField(max_length=2000, null=True, blank=True)

    class Meta:
        db_table = "distribution_records"
        ordering = ["-submitted_at"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity_kg__gt=0), name="record_quantity_positive"),
            models.CheckConstraint(
                condition=(
                    Q(location_latitude__isnull=True, location_longitude__isnull=True)
                    | Q(
                        location_latitude__gte=-90,
                        location_latitude__lte=90,
                        location_longitude__gte=-180,
                        location_longitude__lte=180,
                    )
                ),
                name="record_coordinate_range",
            ),
            models.UniqueConstraint(
                fields=["distributor_user", "idempotency_key"], name="uq_record_idempotency"
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="ix_records_status"),
            models.Index(fields=["distributor_user", "status"], name="ix_records_distributor_status"),
            models.Index(fields=["site"], name="ix_records_site"),
            models.Index(fields=["campaign"], name="ix_records_campaign"),
        ]


class UploadIntent(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="upload_intents"
    )
    purpose = models.CharField(
        max_length=32, choices=IntentPurpose.choices, default=IntentPurpose.DISTRIBUTION_EVIDENCE
    )
    content_type = models.CharField(max_length=64)
    max_bytes = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    storage_key = models.CharField(max_length=256, null=True, blank=True)
    received_bytes = models.PositiveIntegerField(null=True, blank=True)
    received_sha256_hex = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "upload_intents"
        ordering = ["-created_at"]


class PhotoEvidence(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    distribution_record = models.ForeignKey(
        DistributionRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name="evidence"
    )
    uploader_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name="uploaded_evidence"
    )
    storage_key = models.CharField(max_length=256, unique=True)
    thumbnail_key = models.CharField(max_length=256, null=True, blank=True)
    content_type = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    sha256_hex = models.CharField(max_length=64)
    capture_source = models.CharField(max_length=20, choices=CaptureSource.choices)
    client_captured_at = models.DateTimeField(null=True, blank=True)
    server_received_at = models.DateTimeField(default=timezone.now)
    exif_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    exif_longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    exif_taken_at = models.DateTimeField(null=True, blank=True)
    metadata_check_result = models.JSONField(default=dict, blank=True)
    validation_flags = models.JSONField(default=list, blank=True)
    duplicate_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates"
    )
    lifecycle_status = models.CharField(
        max_length=20, choices=EvidenceLifecycle.choices, default=EvidenceLifecycle.ACTIVE
    )

    class Meta:
        db_table = "photo_evidence"
        ordering = ["-server_received_at"]
        constraints = [models.CheckConstraint(condition=Q(size_bytes__gt=0), name="evidence_size_positive")]
        indexes = [
            models.Index(fields=["sha256_hex"], name="ix_evidence_hash"),
            models.Index(fields=["distribution_record"], name="ix_evidence_record"),
        ]


class StockAccount(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="stock_accounts",
    )
    site = models.ForeignKey(
        DistributionSite, null=True, blank=True, on_delete=models.CASCADE, related_name="stock_accounts"
    )
    name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "inventory_accounts"
        ordering = ["account_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["account_type"],
                condition=Q(account_type=AccountType.CENTRAL),
                name="uq_central_account",
            ),
            models.UniqueConstraint(
                fields=["owner_user"],
                condition=Q(account_type=AccountType.DISTRIBUTOR, owner_user__isnull=False),
                name="uq_distributor_account",
            ),
            models.UniqueConstraint(
                fields=["site"],
                condition=Q(account_type=AccountType.SITE, site__isnull=False),
                name="uq_site_account",
            ),
        ]


class StockMovement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    source_account = models.ForeignKey(
        StockAccount, null=True, blank=True, on_delete=models.PROTECT, related_name="outgoing_movements"
    )
    destination_account = models.ForeignKey(
        StockAccount, null=True, blank=True, on_delete=models.PROTECT, related_name="incoming_movements"
    )
    quantity_kg = models.DecimalField(max_digits=14, decimal_places=3)
    reference_type = models.CharField(max_length=40)
    reference_id = models.UUIDField(null=True, blank=True)
    distribution_reference = models.ForeignKey(
        DistributionRecord,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    idempotency_key = models.CharField(max_length=128, unique=True, null=True, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reason = models.TextField(null=True, blank=True)
    reversal_of = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.RESTRICT, related_name="reversal"
    )
    movement_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "stock_movements"
        ordering = ["-posted_at"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity_kg__gt=0), name="movement_quantity_positive"),
            models.CheckConstraint(
                condition=(
                    ~Q(movement_type=MovementType.RECEIPT)
                    | Q(source_account__isnull=True, destination_account__isnull=False)
                ),
                name="receipt_semantics",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(movement_type=MovementType.LOSS)
                    | Q(source_account__isnull=False, destination_account__isnull=True)
                ),
                name="loss_semantics",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(movement_type__in=["TRANSFER", "DELIVERY", "RETURN", "ADJUSTMENT"])
                    | (
                        Q(source_account__isnull=False, destination_account__isnull=False)
                        & ~Q(source_account=models.F("destination_account"))
                    )
                ),
                name="transfer_semantics",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(movement_type=MovementType.REVERSAL)
                    | Q(source_account__isnull=False)
                    | Q(destination_account__isnull=False)
                ),
                name="reversal_semantics",
            ),
            models.UniqueConstraint(
                fields=["distribution_reference"],
                condition=Q(distribution_reference__isnull=False),
                name="uq_movement_delivery_reference",
            ),
        ]
        indexes = [
            models.Index(fields=["destination_account"], name="ix_movements_destination"),
            models.Index(fields=["source_account"], name="ix_movements_source"),
        ]


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=40)
    target_id = models.UUIDField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    request_id = models.CharField(max_length=64, null=True, blank=True)
    reason = models.CharField(max_length=2000, null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.CharField(max_length=64, null=True, blank=True)
    user_agent_abridged = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = "audit_events"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["occurred_at"], name="ix_audit_events_occurred"),
            models.Index(fields=["action"], name="ix_audit_events_action"),
            models.Index(fields=["target_type", "target_id"], name="ix_audit_events_target"),
            models.Index(fields=["actor_user"], name="ix_audit_events_actor"),
        ]


class OrganizationSettings(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timezone = models.CharField(max_length=64, default="UTC")
    default_display_unit = models.CharField(
        max_length=12, choices=DisplayUnit.choices, default=DisplayUnit.KG
    )
    kg_per_bag = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    default_geofence_radius_m = models.PositiveIntegerField(default=200)
    max_acceptable_gps_accuracy_m = models.PositiveIntegerField(default=100)
    max_location_age_seconds = models.PositiveIntegerField(default=300)
    max_capture_time_drift_seconds = models.PositiveIntegerField(default=600)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "organization_settings"
        verbose_name_plural = "organization settings"
        constraints = [
            models.CheckConstraint(
                condition=Q(kg_per_bag__isnull=True) | Q(kg_per_bag__gt=0, kg_per_bag__lte=1000),
                name="kg_per_bag_range",
            ),
            models.CheckConstraint(
                condition=Q(default_geofence_radius_m__gt=0), name="geofence_radius_positive"
            ),
            models.CheckConstraint(
                condition=Q(max_acceptable_gps_accuracy_m__gt=0), name="gps_accuracy_positive"
            ),
            models.CheckConstraint(
                condition=Q(max_location_age_seconds__gt=0), name="location_age_positive"
            ),
            models.CheckConstraint(
                condition=Q(max_capture_time_drift_seconds__gt=0), name="capture_drift_positive"
            ),
        ]


class Invitation(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=320)
    display_name = models.CharField(max_length=120)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DISTRIBUTOR)
    token_hash = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invitations",
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "invitations"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email"], name="ix_invitations_email")]


class PasswordResetToken(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "password_reset_tokens"
        ordering = ["-created_at"]
