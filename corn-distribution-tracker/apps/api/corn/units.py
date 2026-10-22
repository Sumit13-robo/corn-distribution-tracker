"""Decimal-safe unit conversion; canonical storage is kg at gram precision."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .enums import DisplayUnit
from .errors import AppError, UnprocessableEntityError

KG_SCALE = Decimal("0.001")

UNIT_TO_KG: dict[str, Decimal | None] = {
    DisplayUnit.KG.value: Decimal(1),
    DisplayUnit.QUINTAL.value: Decimal(100),
    DisplayUnit.TONNE.value: Decimal(1000),
    DisplayUnit.BAG.value: None,
}


def parse_decimal(value: str | int | float | Decimal, field: str = "quantity") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise AppError(f"{field} is not a valid number", details=[{"field": field}]) from None


def convert_to_kg(quantity: Decimal | str | int | float, unit: str, kg_per_bag: Decimal | None) -> Decimal:
    if not isinstance(quantity, Decimal):
        quantity = parse_decimal(quantity)
    if quantity <= 0:
        raise UnprocessableEntityError(
            "Quantity must be greater than zero",
            code="VALIDATION_ERROR",
            details=[{"field": "quantity"}],
        )
    factor = UNIT_TO_KG.get(unit)
    if factor is None and unit == DisplayUnit.BAG.value:
        if kg_per_bag is None or kg_per_bag <= 0:
            raise UnprocessableEntityError(
                "Bag unit requires a configured kg-per-bag value; set it in Settings as an administrator.",
                code="VALIDATION_ERROR",
                details=[{"field": "unit"}],
            )
        factor = kg_per_bag
    if factor is None:
        raise UnprocessableEntityError(f"Unsupported unit: {unit}", details=[{"field": "unit"}])
    kg = quantity * factor
    quantized = kg.quantize(KG_SCALE, rounding=ROUND_HALF_UP)
    if quantized != kg:
        raise UnprocessableEntityError(
            "Quantity is more precise than one gram; reduce decimals.",
            code="VALIDATION_ERROR",
            details=[{"field": "quantity"}],
        )
    return quantized


def kg_to_display(quantity_kg: Decimal, unit: DisplayUnit | str, kg_per_bag: Decimal | None) -> Decimal:
    unit = DisplayUnit(unit)
    if unit == DisplayUnit.KG:
        return quantity_kg
    if unit == DisplayUnit.QUINTAL:
        return (quantity_kg / Decimal(100)).quantize(Decimal("0.001"))
    if unit == DisplayUnit.TONNE:
        return (quantity_kg / Decimal(1000)).quantize(Decimal("0.001"))
    if unit == DisplayUnit.BAG:
        if not kg_per_bag or kg_per_bag <= 0:
            raise AppError("Bag display requires a configured kg-per-bag value.")
        return (quantity_kg / kg_per_bag).quantize(Decimal("0.01"))
    raise AppError(f"Unsupported display unit: {unit}")


def unit_factor_label(unit: DisplayUnit | str, kg_per_bag: Decimal | None) -> str:
    unit = DisplayUnit(unit)
    if unit == DisplayUnit.KG:
        return "1 unit = 1 kg"
    if unit == DisplayUnit.QUINTAL:
        return "1 quintal = 100 kg"
    if unit == DisplayUnit.TONNE:
        return "1 tonne = 1000 kg"
    if unit == DisplayUnit.BAG:
        if not kg_per_bag:
            return "bags require configured weight"
        return f"1 bag = {format(kg_per_bag.normalize(), 'f')} kg"
    return unit.value
