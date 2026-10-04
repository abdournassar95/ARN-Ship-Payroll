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
    """خوارزمية حساب الأيام البحرية (الشهر 30 يوماً دائمًا)"""
    if not start_date_str or not end_date_str or start_date_str == "-" or end_date_str == "-":
        return 0
    try:
        d1 = datetime.strptime(start_date_str, "%Y-%m-%d")
        d2 = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        y1, m1, day1 = d1.year, d1.month, d1.day
        y2, m2, day2 = d2.year, d2.month, d2.day
        
        if day1 == 31: day1 = 30
        if day2 == 31: day2 = 30
        
        _, last_day = calendar.monthrange(y2, m2)
        if day1 == 1 and day2 == last_day:
            return ((y2 - y1) * 12 + (m2 - m1) + 1) * 30
            
        days = ((y2 - y1) * 360) + ((m2 - m1) * 30) + (day2 - day1) + 1
        return days if days > 0 else 0
    except Exception:
        return 0