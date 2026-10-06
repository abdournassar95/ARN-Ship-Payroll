# crew_service.py
"""
خدمات إدارة سجلات البحارة — الحذف الآمن الشامل وتهيئة النظام.

المشكلة التي تحلّها هذه الوحدة:
    كان الحذف في الواجهة يحذف جدولَي ``CrewWages`` و``payroll_history`` فقط،
    ويترك وثائق البحار (``crew_documents``) ولقطات عهدته (``cash_reset_snapshot``)
    وتنبيهاته (``alerts_history``). وبما أن قيد ``ON DELETE CASCADE`` في SQLite
    لا يعمل إلا عند تفعيل ``PRAGMA foreign_keys=ON`` (وهو غير مفعّل افتراضياً)،
    تصبح هذه السجلات يتيمة وتُنسَب لاحقاً لأي بحار جديد يحمل نفس رقم السجل.

    تعمل هذه الوحدة داخل معاملة واحدة، وتُفعّل قيود المفاتيح الأجنبية كمصداق أخير،
    وتُرجع ملخصاً رقمياً بما تم حذفه (للاستخدام في سجل التدقيق أو في الاختبارات).

ARN Technology (c) 2026 — تطوير وبرمجة: عبده رجب نصار
"""
import sqlite3
from contextlib import closing
from typing import Dict, List

# الجداول التي تُفرَّغ عند «تهيئة النظام» (مع الإبقاء على المستخدمين والإعدادات وقواعد التنبيهات)
RESET_TABLES: List[str] = [
    'CrewWages',
    'payroll_history',
    'general_cash',
    'cash_closed_months',
    'cash_reset_snapshot',
    'crew_documents',
    'alerts_history',
]


def _connect(db_path: str) -> sqlite3.Connection:
    """اتصال قاعدة بيانات مع تفعيل قيود المفاتيح الأجنبية."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def delete_crew_cascade(db_path: str, crew_id: int) -> Dict[str, int]:
    """
    حذف شامل وآمن لبحار واحد:
        - وثائقه وشهاداته (``crew_documents``)
        - لقطات عهدته النقدية (``cash_reset_snapshot``)
        - سجل رواتبه ومعاملاته (``payroll_history``)
        - إغلاق تنبيهاته القائمة (``alerts_history``)
        - سجل بياناته الأساسي (``CrewWages``)

    Returns:
        dict: ملخص عدد الصفوف المتأثرة لكل جدول.
    """
    summary: Dict[str, int] = {}
    with closing(_connect(db_path)) as conn, conn:
        cur = conn.cursor()

        cur.execute("DELETE FROM crew_documents WHERE crew_id = ?", (crew_id,))
        summary['documents'] = cur.rowcount

        cur.execute("DELETE FROM cash_reset_snapshot WHERE crew_id = ?", (crew_id,))
        summary['snapshots'] = cur.rowcount

        cur.execute("DELETE FROM payroll_history WHERE crew_id = ?", (crew_id,))
        summary['payroll_rows'] = cur.rowcount

        cur.execute(
            "UPDATE alerts_history SET is_resolved = 1, "
            "resolved_at = datetime('now', 'localtime') "
            "WHERE target_type = 'CREW' AND target_id = ? AND is_resolved = 0",
            (crew_id,),
        )
        summary['alerts_closed'] = cur.rowcount

        cur.execute("DELETE FROM CrewWages WHERE No = ?", (crew_id,))
        summary['crew_rows'] = cur.rowcount

    return summary


def reset_all_data(db_path: str) -> Dict[str, int]:
    """
    تهيئة النظام بالكامل لاستخدام قبطان/مستخدم جديد:
    تفريغ كافة جداول التشغيل + تصفير عدّادات المعرّفات التلقائية،
    مع الإبقاء على المستخدمين وإعدادات السفينة وقواعد التنبيهات.

    Returns:
        dict: ملخص عدد الصفوف المحذوفة من كل جدول.
    """
    summary: Dict[str, int] = {}
    with closing(_connect(db_path)) as conn, conn:
        cur = conn.cursor()

        for table in RESET_TABLES:
            # اسم الجدول مأخوذ من قائمة ثابتة داخل الكود (لا يوجد أي مدخل مستخدم)
            cur.execute(f"DELETE FROM {table}")
            summary[table] = cur.rowcount

        placeholders = ", ".join("?" for _ in RESET_TABLES)
        cur.execute(
            f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})",
            tuple(RESET_TABLES),
        )

    return summary
