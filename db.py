# db.py
"""
طبقة الاتصال الموحّدة بقاعدة البيانات (العيب F7 — مراجعة 2026-10-06، القسم 10).

المشكلة التي تحلّها هذه الوحدة:
    كان المشروع يفتح ``sqlite3.connect`` في **60 موضعاً** مقابل 19 إغلاقاً فقط،
    وكل موضع يعيد ضبط إعداداته بنفسه — والأهم أن ``PRAGMA foreign_keys = ON``
    كان مطبَّقاً في مسار الحذف المتتالي وحده، أي أن ضمانة «لا سجلات يتيمة»
    تتبدّل حسب المسار الذي نُفِّذ منه الحذف. كذلك غياب ``journal_mode=WAL``
    و``busy_timeout`` يجعل احتمال ``database is locked`` قائماً عند تشغيل
    فحص التنبيهات في خيط منفصل أثناء فتح نافذة أخرى.

الحل: مُنشئ واحد ``connect()`` يضمن:
    • ``foreign_keys = ON`` في كل مسار (لا استثناء)
    • ``journal_mode = WAL`` (قراءة أثناء الكتابة بلا تعارض)
    • ``busy_timeout`` لمنع أخطاء القفل عند التزامن
    • إغلاقاً مضموناً للاتصال + تراجعاً (rollback) عند أي استثناء

ARN Technology (c) 2026 — تطوير وبرمجة: عبده رجب نصار
"""
import contextlib
import logging
import os
import sqlite3
from typing import Iterator, Optional

import paths

_log = logging.getLogger(__name__)

BUSY_TIMEOUT_MS = 10_000


def connect(db_path: Optional[str] = None, *, read_only: bool = False,
            timeout: float = 10.0) -> sqlite3.Connection:
    """
    اتصال قاعدة بيانات مُهيَّأ بالإعدادات الموحّدة (يحتاج إغلاقاً من المستدعي).

    استخدم ``with db.connect(...) as conn:`` للحصول على إغلاق وتراجع مضمونين.
    """
    resolved = str(db_path) if db_path else paths.db_path_str()
    if os.path.dirname(resolved) and not read_only:
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
    conn = sqlite3.connect(resolved, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.Error as exc:  # وسائط للقراءة فقط / نظام ملفات لا يدعم WAL
        _log.debug("تعذّر تفعيل WAL (%s) — سيُتابع بالوضع الافتراضي", exc)
    return conn


@contextlib.contextmanager
def session(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    """
    جلسة عمل كاملة على قاعدة البيانات:

        with db.session() as conn:
            conn.execute(...)

    تُنفّذ commit عند النجاح، وrollback عند أي استثناء، ثم تُغلق الاتصال
    وأي ملف ``-wal`` مرافق تلقائياً.
    """
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
