"""Canonical v1 money policy: exact, whole Iranian toman values."""

from decimal import Decimal, InvalidOperation


MONEY_MAX_DIGITS = 18
MONEY_DECIMAL_PLACES = 0
MONEY_QUANTUM = Decimal("1")
MIN_MONEY = Decimal("1")
MAX_MONEY = Decimal("999999999999999999")


def normalize_money(value, *, allow_zero=False):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    minimum = Decimal("0") if allow_zero else MIN_MONEY
    if (
        not amount.is_finite()
        or amount < minimum
        or amount > MAX_MONEY
        or amount != amount.to_integral_value()
    ):
        return None
    return amount.quantize(MONEY_QUANTUM)
