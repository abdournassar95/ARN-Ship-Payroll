# tests/test_pass2_p0.py
"""
اختبارات حراسة (Regression Guards) لعيوب «حزمة P0 الثانية» — مراجعة 2026-10-06 (القسم 10):

  F12) مسار قاعدة البيانات ثابت لا يعتمد على مجلد التشغيل، ولا يوجد أي اتصال بمسار نسبي.
  F5)  الصلاحية غير المعروفة تُحفظ كما هي ولا تُرقّى صامتاً إلى Admin.
  F1)  إعدادات الشركة/السفينة تُقرأ وتُكتب من مصدر واحد (مهما كان معرّف الصف)،
       والحفظ يُبلّغ بالفشل بصدق.
"""
import io
import os
import sqlite3

import pytest

import paths
import settings_service
from database import init_db
from utils import normalize_role, is_known_role

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ══════════════════════════════════════════════════════════════
# F12 — مسار قاعدة البيانات
# ══════════════════════════════════════════════════════════════
class TestDatabasePath:
    def test_path_does_not_depend_on_cwd(self, tmp_path, monkeypatch):
        """تغيير مجلد التشغيل لا يغيّر مسار قاعدة البيانات (كان يُنشئ قاعدة جديدة فارغة)."""
        monkeypatch.delenv(paths.ENV_DB_PATH, raising=False)
        monkeypatch.setattr(paths, "app_dir", lambda: tmp_path / "app")
        (tmp_path / "app").mkdir()

        before = paths.db_path()
        elsewhere = tmp_path / "run_from_here"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        after = paths.db_path()

        assert before == after, "المسار تغيّر بتغيّر مجلد التشغيل!"
        assert after.parent == tmp_path / "app"

    def test_legacy_database_is_adopted_not_lost(self, tmp_path, monkeypatch):
        """قاعدة قديمة في مجلد التشغيل القديم تُنسخ للمكان الثابت (بلا حذف الأصل)."""
        monkeypatch.delenv(paths.ENV_DB_PATH, raising=False)
        app = tmp_path / "app"
        app.mkdir()
        legacy_dir = tmp_path / "old_folder"
        legacy_dir.mkdir()
        legacy_db = legacy_dir / paths.DB_FILENAME
        init_db(str(legacy_db))
        conn = sqlite3.connect(str(legacy_db))
        conn.execute("INSERT INTO CrewWages (No, Name) VALUES (99, 'بحّار قديم')")
        conn.commit()
        conn.close()

        monkeypatch.setattr(paths, "app_dir", lambda: app)
        monkeypatch.chdir(legacy_dir)
        resolved = paths.db_path()

        assert resolved == app / paths.DB_FILENAME
        assert resolved.exists(), "لم تُنقل القاعدة القديمة إلى المكان الثابت"
        assert legacy_db.exists(), "حُذفت النسخة الأصلية — يجب ألا تُحذف أبداً"
        conn = sqlite3.connect(str(resolved))
        assert conn.execute("SELECT COUNT(*) FROM CrewWages").fetchone()[0] == 1
        conn.close()

    def test_env_variable_has_priority(self, tmp_path, monkeypatch):
        custom = tmp_path / "custom.db"
        monkeypatch.setenv(paths.ENV_DB_PATH, str(custom))
        assert paths.db_path() == custom

    def test_no_relative_db_path_in_app_code(self):
        """حاجز: لا `sqlite3.connect('arn_ship_payroll.db')` في أي وحدة من وحدات التطبيق."""
        offenders = []
        for name in sorted(os.listdir(PROJECT_ROOT)):
            if not name.endswith(".py") or name == "paths.py":
                continue
            content = io.open(os.path.join(PROJECT_ROOT, name), encoding="utf-8").read()
            if "sqlite3.connect('arn_ship_payroll.db')" in content or \
               'sqlite3.connect("arn_ship_payroll.db")' in content:
                offenders.append(name)
        assert offenders == [], f"وحدات ما زالت تستخدم المسار النسبي: {offenders}"

    def test_service_defaults_use_paths(self, tmp_path, monkeypatch):
        """خدمة بلا مسار تستخدم المسار المركزي وتُنشئ الملف في مجلد الإعدادات لا في CWD."""
        target = tmp_path / "svc.db"
        monkeypatch.setenv(paths.ENV_DB_PATH, str(target))
        elsewhere = tmp_path / "cwd"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)

        from auth_service import AuthService
        with sqlite3.connect(str(target)) as conn:
            pass  # ملف فارغ يكفي لفحص الموقع
        AuthService().user_exists("ghost")

        assert target.exists()
        assert not (elsewhere / paths.DB_FILENAME).exists()


# ══════════════════════════════════════════════════════════════
# F5 — الصلاحيات
# ══════════════════════════════════════════════════════════════
class TestRoleHandling:
    def test_unknown_role_is_preserved(self):
        """'Officer' تبقى 'Officer' — كان النموذج يرقّيها صامتاً إلى 'Admin'."""
        assert normalize_role("Officer") == "Officer"
        assert normalize_role("  ضابط أول  ") == "ضابط أول"

    def test_known_role_case_is_normalized(self):
        assert normalize_role("admin") == "Admin"
        assert normalize_role("ADMIN") == "Admin"
        assert normalize_role("captain") == "Captain"
        assert normalize_role("accountant") == "Accountant"

    def test_empty_role_returns_none(self):
        assert normalize_role("") is None
        assert normalize_role("   ") is None
        assert normalize_role(None) is None

    def test_known_roles_source_of_truth(self):
        assert is_known_role("Admin") and is_known_role("officer".title())
        assert not is_known_role("SuperUser")

    def test_admin_window_has_no_silent_admin_fallback(self):
        """حاجز على الكود: لا addItems بثلاث قيم فقط ولا تجاهل لفشل findText."""
        source = io.open(os.path.join(PROJECT_ROOT, "ui_admin.py"), encoding="utf-8").read()
        assert 'addItems(["Admin", "Captain", "Accountant"])' not in source
        assert "c_role.addItem(normalized_role)" in source
        assert "normalize_role(role)" in source


# ══════════════════════════════════════════════════════════════
# F1 — إعدادات الشركة/السفينة
# ══════════════════════════════════════════════════════════════
class TestSystemSettings:
    @pytest.fixture
    def db_with_odd_id(self, tmp_path):
        db_path = str(tmp_path / "settings.db")
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM system_settings")
        conn.execute(
            "INSERT INTO system_settings (id, company_name, vessel_name) VALUES (7, 'ARN MARINE LTD', 'MV ALPHA')"
        )
        conn.commit()
        conn.close()
        return db_path

    def test_reads_row_regardless_of_id(self, db_with_odd_id):
        data = settings_service.get_system_settings(db_with_odd_id)
        assert data["found"] is True
        assert data["id"] == 7
        assert data["company_name"] == "ARN MARINE LTD"
        assert data["vessel_name"] == "MV ALPHA"
        assert settings_service.system_info_text(db_with_odd_id) == "MV ALPHA - ARN MARINE LTD"

    def test_dashboard_header_matches_settings_row(self, db_with_odd_id):
        """شريط عنوان لوحة القيادة يعرض بيانات الصف الفعلي (كان يعرض الافتراضي)."""
        from ui_dashboard import PayrollEngine
        assert PayrollEngine(db_path=db_with_odd_id).get_system_info() == "MV ALPHA - ARN MARINE LTD"

    def test_save_updates_existing_row_with_nonstandard_id(self, db_with_odd_id):
        assert settings_service.save_system_settings("شركة جديدة", "سفينة جديدة", db_with_odd_id) is True

        conn = sqlite3.connect(db_with_odd_id)
        rows = conn.execute("SELECT id, company_name, vessel_name FROM system_settings").fetchall()
        conn.close()
        assert len(rows) == 1, "أُضيف صف ثانٍ بدل تحديث الصف القائم"
        assert rows[0] == (7, "شركة جديدة", "سفينة جديدة")

    def test_save_inserts_when_table_empty(self, tmp_path):
        db_path = str(tmp_path / "empty.db")
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM system_settings")
        conn.commit()
        conn.close()

        assert settings_service.save_system_settings("شركة", "سفينة", db_path) is True
        data = settings_service.get_system_settings(db_path)
        assert data["found"] is True and data["company_name"] == "شركة"

    def test_report_service_no_scattered_settings_sql(self):
        """حاجز: تقارير الخدمة لم تعد تحمل استعلام إعدادات خاصاً بها (مصدر واحد)."""
        source = io.open(os.path.join(PROJECT_ROOT, "report_service.py"), encoding="utf-8").read()
        assert "FROM system_settings" not in source
        assert "settings_service.get_system_settings" in source

    def test_no_hardcoded_id_one_queries(self):
        """حاجز: لا استعلام `system_settings ... WHERE id=1` فعلي في أي وحدة تطبيق."""
        import re
        pattern = re.compile(r"FROM\s+system_settings[\s\S]{0,60}?WHERE\s+id\s*=\s*1", re.IGNORECASE)
        offenders = []
        for name in sorted(os.listdir(PROJECT_ROOT)):
            if not name.endswith(".py"):
                continue
            content = io.open(os.path.join(PROJECT_ROOT, name), encoding="utf-8").read()
            if pattern.search(content):
                offenders.append(name)
        assert offenders == [], f"استعلامات إعدادات قديمة في: {offenders}"


# ══════════════════════════════════════════════════════════════
# البنية العامة للجولة الثانية
# ══════════════════════════════════════════════════════════════
class TestPathModuleHygiene:
    def test_paths_module_has_no_side_effect_at_import(self, tmp_path, monkeypatch):
        """استيراد الوحدة لا ينشئ أي ملف بحدّ ذاته."""
        monkeypatch.setenv(paths.ENV_DB_PATH, str(tmp_path / "not_created.db"))
        import importlib
        importlib.reload(paths)
        assert not (tmp_path / "not_created.db").exists()
