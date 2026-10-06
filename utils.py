# utils.py
import calendar
from datetime import datetime

RANK_HIERARCHY = [
    'MASTER', 'CH.OFF', '2nd.OFF', '3rd.OFF', 
    'CH.ENG', '2nd.ENG', '3rd.ENG', 'ELECTRICIAN', 
    'BOSUN', 'FITTER', 'PUMP MAN', 'A/B', 'O/S', 
    'OILER', 'WIPER', 'COOK', 'MESS BOY', 'CADET'
]

def get_base_rank(rank_str):
    """استخراج الرتبة الأساسية بدون أرقام (مثال: 'MASTER 1' ترجع 'MASTER')"""
    if not rank_str:
        return 'OTHER'
    clean = str(rank_str).strip().upper()
    parts = clean.split()
    base = parts[0] if parts else 'OTHER'
    for r in RANK_HIERARCHY:
        if base == r or clean.startswith(r):
            return r
    return base

def get_rank_sort_key(rank_str):
    """إرجاع ترتيب الرتبة كـ Index في القائمة الهرمية"""
    base = get_base_rank(rank_str)
    try:
        return RANK_HIERARCHY.index(base)
    except ValueError:
        return len(RANK_HIERARCHY)

def calculate_days_30(start_date_str, end_date_str):
    """Count both endpoints under the 30-day maritime-month convention.

    A complete calendar month counts as 30 days (including February). Partial
    months count the actual inclusive interval, treating day 31 as day 30.
    Split multi-month intervals so a complete February is not undercounted.
    """
    if not start_date_str or not end_date_str or start_date_str == "-" or end_date_str == "-":
        return 0
    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return 0
    if start > end:
        return 0

    days = 0
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        last = calendar.monthrange(year, month)[1]
        first_day = start.day if (year, month) == (start.year, start.month) else 1
        last_day = end.day if (year, month) == (end.year, end.month) else last
        if first_day == 1 and last_day == last:
            days += 30
        else:
            days += max(0, min(last_day, 30) - min(first_day, 30) + 1)
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return days
