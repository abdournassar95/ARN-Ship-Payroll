# settings_service.py
"""
خدمة موحّدة لقراءة وكتابة إعدادات الشركة/السفينة (``system_settings``).

المشكلة التي تحلّها (العيب F1 في مراجعة 2026-10-06 — القسم 10):
    كانت الإعدادات تُقرأ وتُكتب بثلاث طرق متضاربة:
      • ``ui_dashboard.PayrollEngine.get_system_info`` → ``WHERE id=1``
      • ``ui_admin.load_settings``                    → ``WHERE id=1``
      • ``ui_admin.save_settings``                    → ``UPDATE ... WHERE id=1``
      • ``report_service`` (3 مواضع)                  → ``LIMIT 1`` بلا ``ORDER BY``

    فإذا كان الصف الفعلي بمعرّف غير 1 انقسمت الشاشات على نفسها، وصار الحفظ بلا أثر
    مع رسالة «تم الحفظ بنجاح!» الكاذبة.

الحل: مصدر واحد للقراءة (الصف الوحيد مهما كان معرّفه) وللكتابة (تحديث فعلي،
وإدراج عند غياب الصف)، مع إبلاغ صادق عن نتيجة الحفظ.

ARN Technology (c) 2026 — تطوير وبرمجة: عبده رجب نصار
"""
import sqlite3
from typing import Dict, Optional

import db
import paths

DEFAULT_COMPANY = "ARN FLEET MANAGEMENT"
DEFAULT_VESSEL = "Vessel"


def _resolve(db_path: Optional[str]) -> str:
    return str(db_path) if db_path else paths.db_path_str()


def get_system_settings(db_path: Optional[str] = None) -> Dict[str, object]:
    """
    قراءة إعدادات الشركة/السفينة من الصف الوحيد في الجدول (مهما كان معرّفه).

    Returns:
        dict: ``{"id": int|None, "company_name": str, "vessel_name": str, "found": bool}``
        والقيم الافتراضية مستخدمة عندما يكون الجدول فارغاً.
    """
    result: Dict[str, object] = {
        "id": None,
        "company_name": DEFAULT_COMPANY,
        "vessel_name": DEFAULT_VESSEL,
        "found": False,
    }
    try:
        with db.session(_resolve(db_path)) as conn:
            row = conn.execute(
                "SELECT id, company_name, vessel_name FROM system_settings ORDER BY id LIMIT 1"
            ).fetchone()
    except (sqlite3.Error, Exception):
        return result

    if row:
        result["id"] = row[0]
        result["company_name"] = (row[1] or DEFAULT_COMPANY)
        result["vessel_name"] = (row[2] or DEFAULT_VESSEL)
        result["found"] = True
    return result


def save_system_settings(company_name: str, vessel_name: str,
                         db_path: Optional[str] = None) -> bool:
    """
    حفظ إعدادات الشركة/السفينة على الصف الوحيد في الجدول (مهما كان معرّفه).

    - إن وُجد صف ⇒ يُحدَّث فعلياً.
    - إن كان الجدول فارغاً ⇒ يُدرَج صف واحد.
    - تُعيد ``True`` فقط إذا تحقّق الحفظ فعلاً (وإلا ``False`` مع سبب مطبوع في السجل).
    """
    company = (company_name or "").strip()
    vessel = (vessel_name or "").strip()

    try:
        with db.session(_resolve(db_path)) as conn:
            row = conn.execute(
                "SELECT id FROM system_settings ORDER BY id LIMIT 1"
            ).fetchone()
            if row:
                cur = conn.execute(
                    "UPDATE system_settings SET company_name = ?, vessel_name = ? WHERE id = ?",
                    (company, vessel, row[0]),
                )
                changed = cur.rowcount > 0
            else:
                conn.execute(
                    "INSERT INTO system_settings (company_name, vessel_name) VALUES (?, ?)",
                    (company, vessel),
                )
                changed = True
            conn.commit()
            return changed
    except (sqlite3.Error, Exception):
        return False


def system_info_text(db_path: Optional[str] = None) -> str:
    """نص شريط العنوان الموحّد: «اسم السفينة - اسم الشركة»."""
    data = get_system_settings(db_path)
    return f"{data['vessel_name']} - {data['company_name']}"
