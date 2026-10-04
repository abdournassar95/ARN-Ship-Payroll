# tests/test_database.py
import pytest
import sqlite3
from database import init_db

@pytest.mark.database
class TestDatabaseInitialization:
    def test_all_required_tables_created(self, temp_db_path):
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        expected_tables = [
            "users", "CrewWages", "payroll_history", "general_cash", 
            "system_settings", "cash_closed_months", "cash_reset_snapshot",
            "audit_log", "alerts_rules", "alerts_history", "crew_documents"
        ]
        for table in expected_tables:
            assert table in tables, f"الجدول {table} غير موجود في قاعدة البيانات"

    def test_crew_wages_has_contract_columns(self, temp_db_path):
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(CrewWages)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "contract_start" in columns
        assert "contract_end" in columns

    def test_default_eight_alert_rules_seeded(self, temp_db_path):
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM alerts_rules")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 8

    def test_general_cash_table_has_date_column(self, temp_db_path):

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(general_cash)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "date" in columns
        assert "amount" in columns
        assert "type" in columns

    def test_users_table_has_password_salt(self, temp_db_path):

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "password_salt" in columns
        assert "password_hash" in columns
        assert "username" in columns
        assert "role" in columns

    def test_payroll_history_has_payment_cash_column(self, temp_db_path):
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(payroll_history)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "payment_cash" in columns

    def test_default_system_settings_created(self, temp_db_path):
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT company_name, vessel_name FROM system_settings")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "ARN Fleet"
        assert row[1] == "Default Vessel"

    def test_init_db_is_idempotent(self, temp_db_path):
        # تشغيل init_db مرة ثانية لا يجب أن يرمي خطأ أو يكرر المستخدمين
        init_db(temp_db_path)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 2  # admin & captain فقط
