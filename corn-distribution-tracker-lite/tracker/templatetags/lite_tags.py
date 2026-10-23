"""Small presentation helpers kept out of templates."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

STATUS_CLASSES = {
    "ACTIVE": "success",
    "APPROVED": "success",
    "RECEIPT": "success",
    "SUBMITTED": "pending",
    "ALLOCATION": "info",
    "DELIVERY": "pending",
    "COMPLETE": "info",
    "REJECTED": "danger",
    "CLOSED": "danger",
    "CENTRAL": "info",
    "DISTRIBUTOR": "brand",
    "SITE": "neutral",
}


@register.filter
def status_class(value: str) -> str:
    return STATUS_CLASSES.get(str(value), "neutral")


@register.filter
def initials(user) -> str:
    name = getattr(user, "display_name", "") or getattr(user, "email", "")
    parts = [part for part in name.replace("@", " ").split() if part]
    if not parts:
        return "?"
    return "".join(part[0] for part in parts[:2]).upper()


@register.filter
def subtract(value, arg):
    try:
        return value - arg
    except (TypeError, ValueError):
        return value


@register.filter
def kg(value) -> str:
    """Format a Decimal kilogram value without noisy trailing zeros."""
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    text = f"{number:,.3f}".rstrip("0").rstrip(".")
    return text or "0"
