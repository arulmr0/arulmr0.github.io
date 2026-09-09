"""Money helpers.

All monetary values are stored as integers in the currency's minor unit
(paise, cents, ...). Floats are never used for money. See ADR-0004.
"""

from decimal import ROUND_HALF_UP, Decimal


def to_minor(amount: Decimal | float | str) -> int:
    """Convert a major-unit amount (e.g. 12.50) to minor units (1250)."""
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_major(minor: int) -> Decimal:
    """Convert minor units (1250) to a major-unit Decimal (12.50)."""
    return (Decimal(minor) / 100).quantize(Decimal("0.01"))


def percent_of(minor: int, percent: float) -> int:
    """Return ``percent`` of ``minor`` rounded half-up to the nearest minor unit."""
    return int(
        (Decimal(minor) * Decimal(str(percent)) / 100).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def multiply(minor: int, factor: float) -> int:
    """Multiply a minor amount by a (possibly fractional) factor, rounding half-up."""
    return int(
        (Decimal(minor) * Decimal(str(factor))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
