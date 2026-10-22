"""Analytics response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from app.schemas.common import ApiModel


class StockPositionOut(ApiModel):
    central_on_hand_kg: Decimal
    distributor_held_kg: Decimal
    site_stock_kg: Decimal
    reserved_pending_kg: Decimal


class EvidenceCompletenessOut(ApiModel):
    approved_with_evidence: int
    approved_total: int
    ratio: float | None = None


class OverviewOut(ApiModel):
    filters: dict
    stock: StockPositionOut
    submitted_pending_kg: Decimal
    approved_delivered_kg: Decimal
    rejected_kg: Decimal
    open_review_count: int
    target_kg: Decimal
    remaining_target_kg: Decimal
    over_target_kg: Decimal
    evidence_completeness: EvidenceCompletenessOut
    flagged_record_count: int
    unit: str


class DistributorPerfOut(ApiModel):
    distributor_user_id: uuid.UUID
    display_name: str
    email: str
    is_active: bool
    target_kg: Decimal
    submitted_kg: Decimal
    approved_kg: Decimal
    pending_kg: Decimal
    rejected_kg: Decimal
    remaining_target_kg: Decimal
    over_target_kg: Decimal
    stock_balance_kg: Decimal
    flagged_submissions: int
    approved_with_exception: int
    denominator_note: str


class SitePerfOut(ApiModel):
    site_id: uuid.UUID
    site_code: str
    site_name: str
    is_active: bool
    target_kg: Decimal
    approved_kg: Decimal
    pending_kg: Decimal
    rejected_kg: Decimal
    remaining_target_kg: Decimal
    last_visit_at: datetime | None = None
    evidence_status: str
    denominator_note: str


class MapSiteOut(ApiModel):
    id: uuid.UUID
    site_code: str
    name: str
    latitude: Decimal
    longitude: Decimal
    is_active: bool
    target_kg: Decimal
    approved_kg: Decimal
    pending_kg: Decimal
    remaining_target_kg: Decimal
    submission_count: int
    status: str
    last_visit_at: datetime | None = None
    has_flagged_evidence: bool
