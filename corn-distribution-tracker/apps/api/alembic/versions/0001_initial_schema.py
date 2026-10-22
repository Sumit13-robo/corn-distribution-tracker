"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-21 23:09:50.497395

Notes:
- Optional PostGIS: the deployment database may have PostGIS; when present the
  extension is created. Sites use validated numeric WGS84 columns for bbox and
  geodesic distance (see docs/architecture/STACK_AND_REPO.md SRID note).
- Append-only enforcement: stock_movements and audit_events get triggers that
  reject UPDATE/DELETE, making the ledger tamper-evident at the database level.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email_normalized", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=True),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "DISTRIBUTOR", name="user_role", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("must_reset_password", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email_normalized"), "users", ["email_normalized"], unique=True)
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("reference_code", sa.String(length=40), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT", "ACTIVE", "PAUSED", "CLOSED", name="campaign_status", native_enum=False, length=20
            ),
            nullable=False,
        ),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_campaigns_created_by_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaigns")),
        sa.UniqueConstraint("reference_code", name=op.f("uq_campaigns_reference_code")),
    )
    op.create_table(
        "distribution_sites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("site_code", sa.String(length=40), nullable=False),
        sa.Column("address_text", sa.String(length=500), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("geofence_radius_m", sa.Integer(), nullable=False),
        sa.Column("max_acceptable_accuracy_m", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.CheckConstraint(
            "geofence_radius_m > 0", name=op.f("ck_distribution_sites_site_geofence_positive")
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name=op.f("ck_distribution_sites_site_lat_range")
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name=op.f("ck_distribution_sites_site_lng_range")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_distribution_sites_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_distribution_sites")),
        sa.UniqueConstraint("site_code", name=op.f("uq_distribution_sites_site_code")),
    )
    op.create_table(
        "distributor_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("distributor_user_id", sa.Uuid(), nullable=False),
        sa.Column("target_quantity_kg", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "PAUSED", "COMPLETE", name="assignment_status", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.CheckConstraint(
            "target_quantity_kg > 0", name=op.f("ck_distributor_assignments_assignment_target_positive")
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_distributor_assignments_campaign_id_campaigns"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_distributor_assignments_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["distributor_user_id"],
            ["users.id"],
            name=op.f("fk_distributor_assignments_distributor_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["distribution_sites.id"],
            name=op.f("fk_distributor_assignments_site_id_distribution_sites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_distributor_assignments")),
    )
    op.create_index(
        op.f("ix_distributor_assignments_distributor_user_id"),
        "distributor_assignments",
        ["distributor_user_id"],
        unique=False,
    )
    op.create_index(
        "uq_assignment_open",
        "distributor_assignments",
        ["campaign_id", "site_id", "distributor_user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('ACTIVE', 'PAUSED')"),
    )
    op.create_table(
        "distribution_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("distributor_user_id", sa.Uuid(), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "SUBMITTED",
                "APPROVED",
                "REJECTED",
                "CANCELLED",
                name="record_status",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("client_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("review_reason", sa.String(length=2000), nullable=True),
        sa.Column("stock_movement_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("location_latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("location_longitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("location_accuracy_m", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("location_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_reported_location_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("distance_to_site_m", sa.Numeric(precision=12, scale=1), nullable=True),
        sa.Column(
            "geo_status",
            sa.Enum(
                "PASS", "WARNING", "EXCEPTION", "UNAVAILABLE", name="geo_status", native_enum=False, length=20
            ),
            nullable=False,
        ),
        sa.Column("geo_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("review_exception_reason", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.CheckConstraint(
            "(location_latitude IS NULL AND location_longitude IS NULL) OR "
            "(location_latitude >= -90 AND location_latitude <= 90 AND "
            "location_longitude >= -180 AND location_longitude <= 180)",
            name=op.f("ck_distribution_records_record_coordinate_range"),
        ),
        sa.CheckConstraint("quantity_kg > 0", name=op.f("ck_distribution_records_record_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["distributor_assignments.id"],
            name=op.f("fk_distribution_records_assignment_id_distributor_assignments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_distribution_records_campaign_id_campaigns"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["distributor_user_id"],
            ["users.id"],
            name=op.f("fk_distribution_records_distributor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name=op.f("fk_distribution_records_reviewed_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["distribution_sites.id"],
            name=op.f("fk_distribution_records_site_id_distribution_sites"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_distribution_records")),
        sa.UniqueConstraint("distributor_user_id", "idempotency_key", name="uq_record_idempotency"),
        sa.UniqueConstraint("stock_movement_id", name=op.f("uq_distribution_records_stock_movement_id")),
    )
    op.create_index("ix_distribution_records_campaign", "distribution_records", ["campaign_id"], unique=False)
    op.create_index(
        "ix_distribution_records_distributor_status",
        "distribution_records",
        ["distributor_user_id", "status"],
        unique=False,
    )
    op.create_index("ix_distribution_records_site", "distribution_records", ["site_id"], unique=False)
    op.create_index("ix_distribution_records_status", "distribution_records", ["status"], unique=False)
    op.create_table(
        "inventory_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "account_type",
            sa.Enum("CENTRAL", "DISTRIBUTOR", "SITE", name="account_type", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name=op.f("fk_inventory_accounts_owner_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["distribution_sites.id"],
            name=op.f("fk_inventory_accounts_site_id_distribution_sites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_accounts")),
    )
    op.create_index(
        "uq_central_account",
        "inventory_accounts",
        ["account_type"],
        unique=True,
        postgresql_where=sa.text("account_type = 'CENTRAL'"),
    )
    op.create_index(
        "uq_distributor_account",
        "inventory_accounts",
        ["owner_user_id"],
        unique=True,
        postgresql_where=sa.text("account_type = 'DISTRIBUTOR' AND owner_user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_site_account",
        "inventory_accounts",
        ["site_id"],
        unique=True,
        postgresql_where=sa.text("account_type = 'SITE' AND site_id IS NOT NULL"),
    )
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "movement_type",
            sa.Enum(
                "RECEIPT",
                "TRANSFER",
                "DELIVERY",
                "RETURN",
                "LOSS",
                "ADJUSTMENT",
                "REVERSAL",
                name="movement_type",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("source_account_id", sa.Uuid(), nullable=True),
        sa.Column("destination_account_id", sa.Uuid(), nullable=True),
        sa.Column("quantity_kg", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("reference_type", sa.String(length=40), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("distribution_reference_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reversal_of_id", sa.Uuid(), nullable=True),
        sa.Column("movement_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Movement semantics are encoded as implications: for any row, each check
        # must be TRUE or NULL (never FALSE). Writing them as plain conjunctions
        # (e.g. `type='LOSS' AND ...`) would reject every row of every other type.
        sa.CheckConstraint(
            "(movement_type <> 'LOSS' OR (source_account_id IS NOT NULL AND destination_account_id IS NULL))",
            name=op.f("ck_stock_movements_loss_semantics"),
        ),
        sa.CheckConstraint(
            "(movement_type <> 'RECEIPT' OR (source_account_id IS NULL "
            "AND destination_account_id IS NOT NULL))",
            name=op.f("ck_stock_movements_receipt_semantics"),
        ),
        # Transfer semantics: two-sided inventory moves between distinct accounts.
        # REVERSAL is excluded here because a reversal mirrors the reversed movement's
        # shape: two-sided for transfers, source-only when undoing a RECEIPT, and
        # destination-only when undoing a LOSS (see reverse_movement in
        # app/services/inventory_service.py).
        sa.CheckConstraint(
            "(movement_type NOT IN ('TRANSFER', 'DELIVERY', 'RETURN', 'ADJUSTMENT') OR "
            "(source_account_id IS NOT NULL AND destination_account_id IS NOT NULL "
            "AND source_account_id <> destination_account_id))",
            name=op.f("ck_stock_movements_transfer_semantics"),
        ),
        sa.CheckConstraint(
            "(movement_type <> 'REVERSAL' OR (source_account_id IS NOT NULL "
            "OR destination_account_id IS NOT NULL))",
            name=op.f("ck_stock_movements_reversal_semantics"),
        ),
        sa.CheckConstraint("quantity_kg > 0", name=op.f("ck_stock_movements_movement_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_stock_movements_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["destination_account_id"],
            ["inventory_accounts.id"],
            name=op.f("fk_stock_movements_destination_account_id_inventory_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["distribution_reference_id"],
            ["distribution_records.id"],
            name=op.f("fk_stock_movements_distribution_reference_id_distribution_records"),
        ),
        sa.ForeignKeyConstraint(
            ["reversal_of_id"],
            ["stock_movements.id"],
            name=op.f("fk_stock_movements_reversal_of_id_stock_movements"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_account_id"],
            ["inventory_accounts.id"],
            name=op.f("fk_stock_movements_source_account_id_inventory_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_movements")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_stock_movements_idempotency_key")),
        sa.UniqueConstraint("reversal_of_id", name=op.f("uq_stock_movements_reversal_of_id")),
    )
    op.create_index(
        "ix_stock_movements_destination", "stock_movements", ["destination_account_id"], unique=False
    )
    op.create_index("ix_stock_movements_idempotency", "stock_movements", ["idempotency_key"], unique=True)
    op.create_index("ix_stock_movements_source", "stock_movements", ["source_account_id"], unique=False)
    op.create_index(
        "uq_movement_delivery_reference",
        "stock_movements",
        ["distribution_reference_id"],
        unique=True,
        postgresql_where=None,
    )
    op.create_table(
        "photo_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("distribution_record_id", sa.Uuid(), nullable=True),
        sa.Column("uploader_user_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=256), nullable=False),
        sa.Column("thumbnail_key", sa.String(length=256), nullable=True),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hex", sa.String(length=64), nullable=False),
        sa.Column(
            "capture_source",
            sa.Enum(
                "CAMERA", "FILE_PICKER", "OFFLINE_CAMERA", name="capture_source", native_enum=False, length=20
            ),
            nullable=False,
        ),
        sa.Column("client_captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_received_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("exif_latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("exif_longitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("exif_taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_check_result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("duplicate_of_id", sa.Uuid(), nullable=True),
        sa.Column(
            "lifecycle_status",
            sa.Enum(
                "PENDING",
                "ACTIVE",
                "SUPERSEDED",
                "DELETED",
                name="evidence_lifecycle",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_photo_evidence_evidence_size_positive")),
        sa.ForeignKeyConstraint(
            ["distribution_record_id"],
            ["distribution_records.id"],
            name=op.f("fk_photo_evidence_distribution_record_id_distribution_records"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_id"],
            ["photo_evidence.id"],
            name=op.f("fk_photo_evidence_duplicate_of_id_photo_evidence"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["uploader_user_id"],
            ["users.id"],
            name=op.f("fk_photo_evidence_uploader_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_photo_evidence")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_photo_evidence_storage_key")),
    )
    op.create_index("ix_photo_evidence_hash", "photo_evidence", ["sha256_hex"], unique=False)
    op.create_index("ix_photo_evidence_record", "photo_evidence", ["distribution_record_id"], unique=False)
    op.create_table(
        "upload_intents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum("DISTRIBUTION_EVIDENCE", name="intent_purpose", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("max_bytes", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("storage_key", sa.String(length=256), nullable=True),
        sa.Column("received_bytes", sa.Integer(), nullable=True),
        sa.Column("received_sha256_hex", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_upload_intents_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_upload_intents")),
    )
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email_normalized", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "DISTRIBUTOR", name="user_role", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_invitations_created_by_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_invitations_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invitations")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_invitations_token_hash")),
    )
    op.create_index(
        op.f("ix_invitations_email_normalized"), "invitations", ["email_normalized"], unique=False
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_password_reset_tokens_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_password_reset_tokens_token_hash")),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_refresh_tokens_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"], unique=False)
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=2000), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent_abridged", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_events_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"], unique=False)
    op.create_index("ix_audit_events_actor", "audit_events", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_events_occurred", "audit_events", ["occurred_at"], unique=False)
    op.create_index("ix_audit_events_target", "audit_events", ["target_type", "target_id"], unique=False)
    op.create_table(
        "organization_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column(
            "default_display_unit",
            sa.Enum("KG", "QUINTAL", "TONNE", "BAG", name="display_unit", native_enum=False, length=12),
            nullable=False,
        ),
        sa.Column("kg_per_bag", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("default_geofence_radius_m", sa.Integer(), nullable=False),
        sa.Column("max_acceptable_gps_accuracy_m", sa.Integer(), nullable=False),
        sa.Column("max_location_age_seconds", sa.Integer(), nullable=False),
        sa.Column("max_capture_time_drift_seconds", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()", nullable=True),
        sa.CheckConstraint(
            "default_geofence_radius_m > 0", name=op.f("ck_organization_settings_geofence_radius_positive")
        ),
        sa.CheckConstraint(
            "kg_per_bag IS NULL OR (kg_per_bag > 0 AND kg_per_bag <= 1000)",
            name=op.f("ck_organization_settings_kg_per_bag_range"),
        ),
        sa.CheckConstraint(
            "max_acceptable_gps_accuracy_m > 0", name=op.f("ck_organization_settings_gps_accuracy_positive")
        ),
        sa.CheckConstraint(
            "max_capture_time_drift_seconds > 0", name=op.f("ck_organization_settings_capture_drift_positive")
        ),
        sa.CheckConstraint(
            "max_location_age_seconds > 0", name=op.f("ck_organization_settings_location_age_positive")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name=op.f("fk_organization_settings_updated_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_settings")),
    )
    op.create_foreign_key(
        "fk_distribution_records_stock_movement_id_stock_movements",
        "distribution_records",
        "stock_movements",
        ["stock_movement_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Optional PostGIS extension (skip gracefully when unavailable in dev).
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'postgis') THEN
                CREATE EXTENSION IF NOT EXISTS postgis;
            ELSE
                RAISE NOTICE 'PostGIS not available; spatial features use validated numeric coordinates.';
            END IF;
        END $$;
        """
    )

    # Append-only ledger + audit: DB-level protection against UPDATE/DELETE.
    for table in ("stock_movements", "audit_events"):
        op.execute(
            f"""
            CREATE OR REPLACE FUNCTION prevent_ledger_mutation_{table}() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION '% is append-only: % operations are not permitted', TG_TABLE_NAME, TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER ledger_append_only_{table}
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION prevent_ledger_mutation_{table}();
            """
        )


def downgrade() -> None:
    for table in ("stock_movements", "audit_events"):
        op.execute(f"DROP TRIGGER IF EXISTS ledger_append_only_{table} ON {table};")
        op.execute(f"DROP FUNCTION IF EXISTS prevent_ledger_mutation_{table}();")
    op.drop_constraint(
        "fk_distribution_records_stock_movement_id_stock_movements",
        "distribution_records",
        type_="foreignkey",
    )
    op.drop_index("uq_movement_delivery_reference", table_name="stock_movements")
    op.drop_index("ix_stock_movements_source", table_name="stock_movements")
    op.drop_index("ix_stock_movements_idempotency", table_name="stock_movements")
    op.drop_index("ix_stock_movements_destination", table_name="stock_movements")
    op.drop_table("stock_movements")
    # photo_evidence references distribution_records, so it must be dropped first.
    op.drop_index("ix_photo_evidence_record", table_name="photo_evidence")
    op.drop_index("ix_photo_evidence_hash", table_name="photo_evidence")
    op.drop_table("photo_evidence")
    op.drop_index("ix_distribution_records_status", table_name="distribution_records")
    op.drop_index("ix_distribution_records_site", table_name="distribution_records")
    op.drop_index("ix_distribution_records_distributor_status", table_name="distribution_records")
    op.drop_index("ix_distribution_records_campaign", table_name="distribution_records")
    op.drop_table("distribution_records")
    op.drop_index(
        "uq_assignment_open",
        table_name="distributor_assignments",
        postgresql_where=sa.text("status IN ('ACTIVE', 'PAUSED')"),
    )
    op.drop_index(
        op.f("ix_distributor_assignments_distributor_user_id"), table_name="distributor_assignments"
    )
    op.drop_table("distributor_assignments")
    op.drop_index(
        "uq_site_account",
        table_name="inventory_accounts",
        postgresql_where=sa.text("account_type = 'SITE' AND site_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_distributor_account",
        table_name="inventory_accounts",
        postgresql_where=sa.text("account_type = 'DISTRIBUTOR' AND owner_user_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_central_account",
        table_name="inventory_accounts",
        postgresql_where=sa.text("account_type = 'CENTRAL'"),
    )
    op.drop_table("inventory_accounts")
    op.drop_table("upload_intents")
    op.drop_table("password_reset_tokens")
    op.drop_table("organization_settings")
    op.drop_index(op.f("ix_invitations_email_normalized"), table_name="invitations")
    op.drop_table("invitations")
    op.drop_index("ix_audit_events_target", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred", table_name="audit_events")
    op.drop_index("ix_audit_events_actor", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("distribution_sites")
    op.drop_table("campaigns")
    op.drop_index(op.f("ix_refresh_tokens_family_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_users_email_normalized"), table_name="users")
    op.drop_table("users")
    # ### end Alembic commands ###
