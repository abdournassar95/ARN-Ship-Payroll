# cash_service.py
"""
تعريف موحّد لرصيد صندوق القبطان (العيب F4 — مراجعة 2026-10-06، القسم 10).

المشكلة التي تحلّها:
    كان للنظام **تعريفان متضاربان** للنقد:

      • ``alert_service.check_low_cash``          → مجموع كل الشهور (تراكمي)
      • ``ui_master_cash.load_cash_data`` والتقرير → حركة الشهر وحده
        مع طباعة «عهدة سابقة» = 0 دائماً.

    والنتيجة أن تنبيه «رصيد الصندوق منخفض» قد لا يُطلق في اللحظة التي وُجد
    من أجلها، وأن كشف الشهر يعرض صفراً بينما الخزنة فيها آلاف.

التعريف الرسمي الواحد (المستخدم الآن في التنبيه والشاشة والتقرير):

    الرصيد = Σ(وارد الصندوق حتى نهاية الفترة)
             − Σ(صادر الصندوق حتى نهاية الفترة)
             − Σ(سلف البحارة المصروفة حتى نهاية الفترة)
             + Σ(السلف المصفّاة بمحاضر الاستلام حتى نهاية الفترة)

    و«العهدة السابقة» لأي شهر = الرصيد التراكمي حتى نهاية الشهر الذي قبله.

ARN Technology (c) 2026 — تطوير وبرمجة: عبده رجب نصار
"""
import calendar
from typing import Dict, Optional, Tuple

import db

CASH_IN_TYPES = ("وارد",)
CASH_OUT_TYPES = ("صادر",)


def month_bounds(year: int, month: int) -> Tuple[str, str]:
    """(أول يوم، آخر يوم) في الشهر المحدَّد — كلاهما بنسق ``YYYY-MM-DD``."""
    last_day = calendar.monthrange(int(year), int(month))[1]
    return (f"{int(year)}-{int(month):02d}-01",
            f"{int(year)}-{int(month):02d}-{last_day:02d}")


def period_key(year: int, month: int) -> int:
    """مفتاح عددي للمقارنة بين الفترات: ``year * 12 + month``."""
    return int(year) * 12 + int(month)


def _sum_general_cash(conn, where: str, args: tuple) -> Tuple[float, float]:
    row = conn.execute(
        f"SELECT COALESCE(SUM(CASE WHEN type='وارد' THEN amount ELSE 0 END), 0), "
        f"       COALESCE(SUM(CASE WHEN type='صادر' THEN amount ELSE 0 END), 0) "
        f"FROM general_cash {where}",
        args,
    ).fetchone()
    return float(row[0] or 0.0), float(row[1] or 0.0)


def _sum_crew_advances(conn, where: str, args: tuple) -> float:
    row = conn.execute(
        f"SELECT COALESCE(SUM(payment_cash), 0) FROM payroll_history {where}", args
    ).fetchone()
    return float(row[0] or 0.0)


def _sum_cleared(conn, where: str, args: tuple) -> float:
    row = conn.execute(
        f"SELECT COALESCE(SUM(cleared_cash), 0) FROM cash_reset_snapshot {where}", args
    ).fetchone()
    return float(row[0] or 0.0)


def carried_balance(year: int, month: int, db_path: Optional[str] = None) -> float:
    """«العهدة السابقة»: الرصيد التراكمي قبل بداية الشهر المحدَّد."""
    m_start, _ = month_bounds(year, month)
    key = period_key(year, month)
    with db.session(db_path) as conn:
        inflow, outflow = _sum_general_cash(conn, "WHERE date < ?", (m_start,))
        crew_adv = _sum_crew_advances(
            conn, "WHERE (payroll_year * 12 + payroll_month) < ?", (key,))
        cleared = _sum_cleared(
            conn, "WHERE (payroll_year * 12 + payroll_month) < ?", (key,))
    return round(inflow - outflow - crew_adv + cleared, 2)


def month_flow(year: int, month: int, db_path: Optional[str] = None) -> Dict[str, float]:
    """حركة الشهر وحدها: وارد/صادر الصندوق + سلف البحارة + المصفّى."""
    m_start, m_end = month_bounds(year, month)
    key = period_key(year, month)
    with db.session(db_path) as conn:
        inflow, outflow = _sum_general_cash(
            conn, "WHERE date >= ? AND date <= ?", (m_start, m_end))
        crew_adv = _sum_crew_advances(
            conn, "WHERE (payroll_year * 12 + payroll_month) = ?", (key,))
        cleared = _sum_cleared(
            conn, "WHERE (payroll_year * 12 + payroll_month) = ?", (key,))
    effective_adv = max(0.0, crew_adv - cleared)
    return {
        "in": round(inflow, 2),
        "out": round(outflow, 2),
        "crew_adv": round(crew_adv, 2),
        "cleared": round(cleared, 2),
        "effective_adv": round(effective_adv, 2),
        "month_net": round(inflow - outflow - effective_adv, 2),
    }


def cash_balance(year: Optional[int] = None, month: Optional[int] = None,
                 db_path: Optional[str] = None) -> float:
    """
    الرصيد الرسمي للصندوق.

    • بتحديد سنة وشهر ⇒ الرصيد التراكمي **حتى نهاية ذلك الشهر** (عهدة سابقة + حركة الشهر).
    • بلا تحديد       ⇒ الرصيد الحالي بكل الحركات المسجّلة.
    """
    with db.session(db_path) as conn:
        if year is not None and month is not None:
            _, m_end = month_bounds(year, month)
            inflow, outflow = _sum_general_cash(conn, "WHERE date <= ?", (m_end,))
            key = period_key(year, month)
        else:
            inflow, outflow = _sum_general_cash(conn, "", ())
            key = None
        if key is None:
            crew_adv = _sum_crew_advances(conn, "", ())
            cleared = _sum_cleared(conn, "", ())
        else:
            crew_adv = _sum_crew_advances(
                conn, "WHERE (payroll_year * 12 + payroll_month) <= ?", (key,))
            cleared = _sum_cleared(
                conn, "WHERE (payroll_year * 12 + payroll_month) <= ?", (key,))
    return round(inflow - outflow - crew_adv + cleared, 2)


def month_summary(year: int, month: int, db_path: Optional[str] = None) -> Dict[str, float]:
    """ملخص كامل جاهز للعرض/الطباعة: العهدة السابقة + حركة الشهر + الرصيد النهائي."""
    carried = carried_balance(year, month, db_path)
    flow = month_flow(year, month, db_path)
    return {
        "old_adv": carried,
        "in": flow["in"],
        "out": flow["out"],
        "effective_adv": flow["effective_adv"],
        "net": round(carried + flow["month_net"], 2),
    }
