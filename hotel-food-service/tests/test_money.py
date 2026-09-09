from decimal import Decimal

from app.core.money import multiply, percent_of, to_major, to_minor


def test_round_trip():
    assert to_minor("12.50") == 1250
    assert to_major(1250) == Decimal("12.50")


def test_percent_rounds_half_up():
    assert percent_of(1000, 5) == 50
    assert percent_of(1001, 5) == 50  # 50.05 -> 50
    assert percent_of(1010, 5) == 51  # 50.5 -> 51


def test_multiply_fractional():
    assert multiply(9000, 0.2) == 1800
    assert multiply(333, 0.5) == 167  # 166.5 rounds half-up
