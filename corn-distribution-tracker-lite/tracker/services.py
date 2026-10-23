"""Domain services for the Lite edition.

All stock changes go through this module so the ledger, balances and activity
feed stay consistent. SQLite serialises writes; the select_for_update calls
document the lock points and work unchanged if the database is swapped later.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    Activity,
    Assignment,
    Campaign,
    Delivery,
    Role,
    Site,
    StockAccount,
    StockMovement,
    User,
)

ZERO = Decimal("0")


def format_kg(value: Decimal) -> str:
    """Compact kilogram text for activity details."""
    return f"{value:,.3f}".rstrip("0").rstrip(".")


def central_account() -> StockAccount:
    account, _ = StockAccount.objects.get_or_create(
        kind=StockAccount.Kind.CENTRAL,
        defaults={"name": "Central stock"},
    )
    return account


def distributor_account(user: User) -> StockAccount:
    account, _ = StockAccount.objects.get_or_create(
        kind=StockAccount.Kind.DISTRIBUTOR,
        owner=user,
        defaults={"name": f"{user.short_name} · distributor stock"},
    )
    return account


def site_account(site: Site) -> StockAccount:
    account, _ = StockAccount.objects.get_or_create(
        kind=StockAccount.Kind.SITE,
        site=site,
        defaults={"name": f"{site.code} · site stock"},
    )
    return account


def pending_kg_for(user: User) -> Decimal:
    total = Delivery.objects.filter(distributor=user, status=Delivery.Status.SUBMITTED).aggregate(
        total=Sum("quantity_kg")
    )["total"]
    return total or ZERO


def available_kg_for(user: User) -> Decimal:
    return distributor_account(user).balance_kg - pending_kg_for(user)


def distributor_held_kg() -> Decimal:
    accounts = StockAccount.objects.filter(kind=StockAccount.Kind.DISTRIBUTOR)
    return sum((account.balance_kg for account in accounts), ZERO)


def site_held_kg() -> Decimal:
    accounts = StockAccount.objects.filter(kind=StockAccount.Kind.SITE)
    return sum((account.balance_kg for account in accounts), ZERO)


def approved_kg(*, distributor: User | None = None) -> Decimal:
    rows = Delivery.objects.filter(status=Delivery.Status.APPROVED)
    if distributor is not None:
        rows = rows.filter(distributor=distributor)
    total = rows.aggregate(total=Sum("quantity_kg"))["total"]
    return total or ZERO


def target_kg(*, distributor: User | None = None) -> Decimal:
    rows = Assignment.objects.filter(
        status=Assignment.Status.ACTIVE,
        campaign__status=Campaign.Status.ACTIVE,
    )
    if distributor is not None:
        rows = rows.filter(distributor=distributor)
    total = rows.aggregate(total=Sum("target_kg"))["total"]
    return total or ZERO


def progress_percent(approved: Decimal, target: Decimal) -> int:
    if target <= 0:
        return 0
    return min(100, int((approved / target) * 100))


def record_activity(actor: User | None, action: str, detail: str) -> Activity:
    # The detail column is intentionally short and readable in the feed.
    return Activity.objects.create(actor=actor, action=action, detail=detail[:300])


def post_receipt(*, quantity_kg: Decimal, actor: User, note: str = "") -> StockMovement:
    if quantity_kg <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    with transaction.atomic():
        destination = central_account()
        movement = StockMovement.objects.create(
            kind=StockMovement.Kind.RECEIPT,
            destination=destination,
            quantity_kg=quantity_kg,
            note=note,
            created_by=actor,
        )
        record_activity(
            actor, "Stock receipt", f"{format_kg(quantity_kg)} kg received into central stock."
        )
    return movement


def post_allocation(
    *, distributor: User, quantity_kg: Decimal, actor: User, note: str = ""
) -> StockMovement:
    if distributor.role != Role.DISTRIBUTOR:
        raise ValidationError("Allocate stock to a distributor account.")
    if quantity_kg <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    with transaction.atomic():
        source = StockAccount.objects.select_for_update().get(pk=central_account().pk)
        if source.balance_kg < quantity_kg:
            raise ValidationError(
                f"Only {format_kg(source.balance_kg)} kg is available in central stock."
            )
        destination = distributor_account(distributor)
        movement = StockMovement.objects.create(
            kind=StockMovement.Kind.ALLOCATION,
            source=source,
            destination=destination,
            quantity_kg=quantity_kg,
            note=note,
            created_by=actor,
        )
        record_activity(
            actor,
            "Stock allocation",
            f"{format_kg(quantity_kg)} kg allocated to {distributor.short_name}.",
        )
    return movement


def submit_delivery(
    *,
    assignment: Assignment,
    distributor: User,
    quantity_kg: Decimal,
    notes: str = "",
    photo=None,
) -> Delivery:
    if assignment.distributor_id != distributor.id:
        raise ValidationError("That assignment does not belong to you.")
    if assignment.status != Assignment.Status.ACTIVE:
        raise ValidationError("That assignment is no longer active.")
    if assignment.campaign.status != Campaign.Status.ACTIVE:
        raise ValidationError("That campaign is no longer active.")
    if not assignment.site.is_active:
        raise ValidationError("That site is inactive and cannot receive new deliveries.")
    if quantity_kg <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    with transaction.atomic():
        account = StockAccount.objects.select_for_update().get(
            pk=distributor_account(distributor).pk
        )
        available = account.balance_kg - pending_kg_for(distributor)
        if quantity_kg > available:
            raise ValidationError(
                f"Only {format_kg(available)} kg is available after pending deliveries."
            )
        delivery = Delivery.objects.create(
            assignment=assignment,
            site=assignment.site,
            distributor=distributor,
            quantity_kg=quantity_kg,
            notes=notes,
            photo=photo,
        )
        record_activity(
            distributor,
            "Delivery submitted",
            f"{format_kg(quantity_kg)} kg for {assignment.site.code}.",
        )
    return delivery


def approve_delivery(*, delivery: Delivery, reviewer: User, note: str = "") -> Delivery:
    with transaction.atomic():
        locked = Delivery.objects.select_for_update().get(pk=delivery.pk)
        if locked.status != Delivery.Status.SUBMITTED:
            raise ValidationError("Only submitted deliveries can be approved.")
        source = StockAccount.objects.select_for_update().get(
            pk=distributor_account(locked.distributor).pk
        )
        if source.balance_kg < locked.quantity_kg:
            raise ValidationError(
                f"{locked.distributor.short_name} only holds {format_kg(source.balance_kg)} kg."
            )
        destination = site_account(locked.site)
        movement = StockMovement.objects.create(
            kind=StockMovement.Kind.DELIVERY,
            source=source,
            destination=destination,
            quantity_kg=locked.quantity_kg,
            note=note or f"Approved delivery to {locked.site.code}",
            created_by=reviewer,
        )
        locked.status = Delivery.Status.APPROVED
        locked.reviewed_at = timezone.now()
        locked.reviewed_by = reviewer
        locked.review_note = note
        locked.stock_movement = movement
        locked.save(
            update_fields=[
                "status",
                "reviewed_at",
                "reviewed_by",
                "review_note",
                "stock_movement",
                "updated_at",
            ]
        )
        record_activity(
            reviewer,
            "Delivery approved",
            f"{format_kg(locked.quantity_kg)} kg posted to {locked.site.code} for {locked.distributor.short_name}.",
        )
    return locked


def reject_delivery(*, delivery: Delivery, reviewer: User, note: str) -> Delivery:
    if not note.strip():
        raise ValidationError("A rejection reason is required.")
    with transaction.atomic():
        locked = Delivery.objects.select_for_update().get(pk=delivery.pk)
        if locked.status != Delivery.Status.SUBMITTED:
            raise ValidationError("Only submitted deliveries can be rejected.")
        locked.status = Delivery.Status.REJECTED
        locked.reviewed_at = timezone.now()
        locked.reviewed_by = reviewer
        locked.review_note = note
        locked.save(
            update_fields=["status", "reviewed_at", "reviewed_by", "review_note", "updated_at"]
        )
        record_activity(
            reviewer,
            "Delivery rejected",
            f"{format_kg(locked.quantity_kg)} kg for {locked.site.code}: {note}",
        )
    return locked
