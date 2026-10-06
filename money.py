"""Monetary arithmetic policy: two decimal places, ROUND_HALF_UP.

Read legacy SQLite REAL values via str() (not Decimal(float)); do not change
existing database schema or public UI/report payloads in this stage.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal('0.01')
ZERO = Decimal('0.00')


def amount(value):
    """Convert a stored/input value to Decimal without binary float arithmetic."""
    try:
        result = Decimal(str(value if value is not None and value != '' else 0))
        if not result.is_finite():
            raise ValueError('Amount must be finite')
        return result
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'Invalid amount: {value!r}') from exc


def cents(value):
    return amount(value).quantize(CENT, rounding=ROUND_HALF_UP)


def daily_wage(monthly, days):
    return cents(amount(monthly) * amount(days) / Decimal(30))
