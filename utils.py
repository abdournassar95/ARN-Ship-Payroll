# utils.py
import calendar
from datetime import datetime

KNOWN_ROLE_VALUES = ["Admin", "Captain", "Accountant", "Officer"]

# تطبيع شائع للأحرف اللاتينية للأدوار (admin ⇒ Admin) دون إسقاط أي قيمة غير معروفة
_ROLE_ALIASES = {r.lower(): r for r in KNOWN_ROLE_VALUES}

RANK_HIERARCHY = [
    'MASTER', 'CH.OFF', '2nd.OFF', '3rd.OFF', 
    'CH.ENG', '2nd.ENG', '3rd.ENG', 'ELECTRICIAN', 
    'BOSUN', 'FITTER', 'PUMP MAN', 'A/B', 'O/S', 
    'OILER', 'WIPER', 'COOK', 'MESS BOY', 'CADET'
]

def normalize_role(role_str):
    """
    تطبيع قيمة الصلاحية دون إسقاط معلومة:

      • ``'admin'`` أو ``'ADMIN'``  ⇒ ``'Admin'``  (توحيد حالة الأحرف للقيَم المعروفة)
      • ``'Officer'``               ⇒ ``'Officer'`` (قيمة غير معروفة؟ تبقى كما هي — لا تُرقّى صامتاً)
      • ``''`` / ``None``           ⇒ ``None``      (يجب على المستدعي رفض الإدخال)

    Returns:
        str | None: القيمة المطبَّعة أو ``None`` إذا كان الإدخال فارغاً.
    """
    if role_str is None:
        return None
    value = str(role_str).strip()
    if not value:
        return None
    return _ROLE_ALIASES.get(value.lower(), value)


def is_known_role(role_str):
    """هل القيمة ضمن الصلاحيات المعروفة (بعد التطبيع)؟"""
    return normalize_role(role_str) in KNOWN_ROLE_VALUES


def parse_non_negative(text, field_name="القيمة"):
    """
    تحويل نص إلى رقم غير سالب، أو رفع ``ValueError`` برسالة عربية واضحة.

    تُستخدم في كل مسارات الإدخال المالي لمنع دخول قيم سالبة إلى الرواتب
    (العيب F2: الإضافي/الخصم/السلف قيم موجبة دائماً، والإشارة من نوع الحقل لا من الرقم).
    """
    if text is None:
        raise ValueError(f"لا يمكن ترك «{field_name}» فارغاً.")
    raw = str(text).strip().replace(",", "")
    if not raw:
        raise ValueError(f"لا يمكن ترك «{field_name}» فارغاً.")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"قيمة غير رقمية في «{field_name}»: {text!r}")
    if value < 0:
        raise ValueError(f"لا يُقبل رقم سالب في «{field_name}» ({value}).")
    return value


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