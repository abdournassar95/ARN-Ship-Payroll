# paths.py
"""
مصدر وحيد لمسارات النظام (قاعدة البيانات ومجلداتها المرافقة).

المشكلة التي تحلّها هذه الوحدة (العيب F12 في مراجعة 2026-10-06 — القسم 10):
    كانت كل الوحدات تفتح ``sqlite3.connect('arn_ship_payroll.db')`` بمسار نسبي،
    أي أنه يُحلّ مقابل **مجلد التشغيل الحالي (CWD)** لا مقابل مكان البرنامج.
    ونتيجةً لذلك كان تشغيل البرنامج من مجلد آخر يُنشئ قاعدة بيانات جديدة فارغة،
    فيرى المستخدم أن بياناته «اختفت».

قواعد الحل:
    1) ``ARN_DB_PATH`` (متغيّر بيئة) له الأولوية المطلقة — يُستخدم في الاختبارات والدعم الفني.
    2) المكان الثابت هو مجلد التطبيق: مجلد الملف التنفيذي عند التغليف (PyInstaller)،
       ومجلد المشروع عند التشغيل من المصدر.
    3) عند التغليف داخل مجلد غير قابل للكتابة (مثل Program Files) تُستخدم
       ``%LOCALAPPDATA%/ARN Ship Payroll`` تلقائياً.
    4) إن لم توجد قاعدة بيانات في المكان الثابت ووُجدت نسخة قديمة في مجلد التشغيل
       ⇒ تُنسخ للمكان الثابت مرة واحدة (بلا حذف الأصل) وتُسجَّل الملاحظة للمستخدم.

ARN Technology (c) 2026 — تطوير وبرمجة: عبده رجب نصار
"""
import logging
import os
import shutil
import sys
from pathlib import Path

ENV_DB_PATH = "ARN_DB_PATH"
DB_FILENAME = "arn_ship_payroll.db"

_log = logging.getLogger(__name__)

# ملاحظات الترحيل/النقل التي تُعرض للمستخدم في نافذة «حول» أو الإعدادات
MIGRATION_NOTES: list[str] = []


def app_dir() -> Path:
    """مجلد التطبيق الثابت (مجلد التنفيذي عند التغليف، ومجلد المشروع عند التشغيل من المصدر)."""
    if getattr(sys, "frozen", False):  # PyInstaller / exe
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _writable_dir() -> Path:
    """يُعيد مجلداً قابلاً للكتابة لتخزين قاعدة البيانات (يعالج البرامج المثبّتة في Program Files)."""
    base = app_dir()
    if os.access(base, os.W_OK):
        return base
    fallback = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".local" / "share")) / "ARN Ship Payroll"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except OSError:  # pragma: no cover - حالة بيئات نادرة
        return base
    _log.warning("مجلد التطبيق غير قابل للكتابة — سيُستخدم %s لتخزين قاعدة البيانات", fallback)
    return fallback


def db_path() -> Path:
    """
    المسار النهائي لقاعدة البيانات.

    لا يعتمد إطلاقاً على مجلد التشغيل الحالي، ويُنفّذ «تبنّي» النسخة القديمة إن وُجدت.
    """
    env = (os.environ.get(ENV_DB_PATH) or "").strip()
    if env:
        return Path(env).expanduser()

    fixed = _writable_dir() / DB_FILENAME
    if fixed.exists():
        return fixed

    legacy = Path.cwd() / DB_FILENAME
    try:
        if legacy.exists() and legacy.resolve() != fixed.resolve():
            shutil.copy2(legacy, fixed)
            note = f"تم نقل قاعدة البيانات من {legacy} إلى {fixed} (النسخة الأصلية لم تُحذف)."
            MIGRATION_NOTES.append(note)
            _log.info(note)
    except OSError as exc:  # pragma: no cover - صلاحيات/قرص ممتلئ
        _log.warning("تعذّر نقل قاعدة البيانات القديمة (%s): %s", legacy, exc)

    return fixed


def db_path_str() -> str:
    """نفس ``db_path`` لكن كنص جاهز لـ ``sqlite3.connect``."""
    return str(db_path())
