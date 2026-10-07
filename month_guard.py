# month_guard.py
"""
حرس الإقفال الشهري — نقطة فحص واحدة لكل مسار كتابة مالي (العيب F3).

المشكلة التي تحلّها:
    كان ``ui_master_cash`` وحده يفحص ``is_month_closed()`` قبل الكتابة، بينما
    ``ui_accounting`` (وغيره) يكتب في ``payroll_history`` بلا أي فحص — أي أن
    رواتب شهر سبق إقفاله وتسليمه للطاقم يمكن تعديلها صامتاً، فينشأ فرق بين
    كشف مُوقَّع وكشف مُعاد طبعه. كما أن «تسوية 🔒» (``PaidMonthsData``) لم تكن
    محمية بأي فحص صلاحية.

الحل: دوال صغيرة تُستدعى قبل أي كتابة على بيانات شهرية:
    • ``is_month_closed`` / ``closed_months`` — قراءة حالة الإقفال
    • ``assert_month_open`` — ترفع ``MonthClosedError`` برسالة عربية واضحة
    • ``assert_months_open`` — نسخة لقائمة أشهر (يكفي شهر واحد مقفل للإيقاف)

ARN Technology (c) 2026 — تطوير وبرمجة: عبده رجب نصار
"""
from typing import Iterable, Optional, Sequence, Set, Tuple

import db

MONTH_NAMES_AR = {
    1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل', 5: 'مايو', 6: 'يونيو',
    7: 'يوليو', 8: 'أغسطس', 9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر',
}


class MonthClosedError(Exception):
    """يُرفع عند محاولة الكتابة في شهر مالي مقفل."""

    def __init__(self, months: Sequence[Tuple[int, int]]):
        self.months = list(months)
        labels = "، ".join(f"{MONTH_NAMES_AR.get(m, m)} {y}" for y, m in self.months)
        super().__init__(
            f"الشهر {labels} مقفل محاسبياً — لا يمكن التعديل. "
            "افتحه أولاً من شاشة صندوق القبطان."
        )


def closed_months(db_path: Optional[str] = None) -> Set[Tuple[int, int]]:
    """كل الأشهر المقفلة كمُجموعة ``{(year, month)}``."""
    try:
        with db.session(db_path) as conn:
            rows = conn.execute("SELECT year, month FROM cash_closed_months").fetchall()
        return {(int(r[0]), int(r[1])) for r in rows}
    except Exception:
        return set()


def is_month_closed(year: int, month: int, db_path: Optional[str] = None) -> bool:
    """هل الشهر (year, month) مقفل محاسبياً؟"""
    try:
        with db.session(db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM cash_closed_months WHERE year = ? AND month = ? LIMIT 1",
                (int(year), int(month)),
            ).fetchone()
        return row is not None
    except Exception:
        return False


def assert_month_open(year: int, month: int, db_path: Optional[str] = None) -> None:
    """يرفع ``MonthClosedError`` إذا كان الشهر مقفلاً (وإلا لا يفعل شيئاً)."""
    if is_month_closed(year, month, db_path):
        raise MonthClosedError([(int(year), int(month))])


def assert_months_open(months: Iterable[Tuple[int, int]],
                       db_path: Optional[str] = None) -> None:
    """يرفع ``MonthClosedError`` إذا كان أي من الأشهر مقفلاً (تقرير واحد بالجميع)."""
    closed = closed_months(db_path)
    blocked = sorted({(int(y), int(m)) for y, m in months if (int(y), int(m)) in closed})
    if blocked:
        raise MonthClosedError(blocked)


def close_month(year: int, month: int, db_path: Optional[str] = None) -> bool:
    """إقفال شهر (تُعيد True إن نجح الإقفال أو كان مقفلاً أصلاً)."""
    try:
        with db.session(db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO cash_closed_months (month, year) VALUES (?, ?)",
                (int(month), int(year)),
            )
        return True
    except Exception:
        return False


def open_month(year: int, month: int, db_path: Optional[str] = None) -> bool:
    """إلغاء إقفال شهر (تُعيد True إن نجح)."""
    try:
        with db.session(db_path) as conn:
            conn.execute(
                "DELETE FROM cash_closed_months WHERE month = ? AND year = ?",
                (int(month), int(year)),
            )
        return True
    except Exception:
        return False
