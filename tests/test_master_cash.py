# tests/test_master_cash.py
import pytest
import sqlite3
from database import init_db

class TestMasterCash:
    """اختبارات العمليات المحاسبية لصندوق القبطان"""

    def test_add_income_and_expense(self, temp_db_path):
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO general_cash (amount, type, description, date)
                VALUES (?, ?, ?, ?)
            """, (5000.0, "وارد", "تمويل الصندوق", "2026-09-01"))
            cursor.execute("""
                INSERT INTO general_cash (amount, type, description, date)
                VALUES (?, ?, ?, ?)
            """, (1200.0, "صادر", "مشتريات خضار ومؤن", "2026-09-05"))
            conn.commit()

            cursor.execute("SELECT type, SUM(amount) FROM general_cash GROUP BY type")
            totals = dict(cursor.fetchall())

            assert totals.get("وارد") == 5000.0
            assert totals.get("صادر") == 1200.0

    def test_net_cash_with_crew_advances(self, temp_db_path):
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            # 1. إيداع
            cursor.execute("INSERT INTO general_cash (amount, type, description, date) VALUES (10000, 'وارد', 'عهدة', '2026-09-01')")
            # 2. مصروف
            cursor.execute("INSERT INTO general_cash (amount, type, description, date) VALUES (3000, 'صادر', 'وقود', '2026-09-02')")
            # 3. سلف بحارة في payroll_history
            cursor.execute("""
                INSERT INTO payroll_history (crew_id, payroll_month, payroll_year, payment_cash)
                VALUES (1, 9, 2026, 1500.0)
            """)
            conn.commit()

            cursor.execute("SELECT SUM(amount) FROM general_cash WHERE type='وارد'")
            total_in = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT SUM(amount) FROM general_cash WHERE type='صادر'")
            total_out = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT SUM(payment_cash) FROM payroll_history WHERE payroll_month=9 AND payroll_year=2026")
            crew_adv = cursor.fetchone()[0] or 0.0

            net = total_in - total_out - crew_adv
            assert net == 10000 - 3000 - 1500
            assert net == 5500.0

    def test_month_closure(self, temp_db_path):
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("INSERT INTO cash_closed_months (month, year) VALUES (9, 2026)")
            conn.commit()

            res = conn.execute("SELECT COUNT(*) FROM cash_closed_months WHERE month=9 AND year=2026").fetchone()
            assert res[0] == 1

            conn.execute("DELETE FROM cash_closed_months WHERE month=9 AND year=2026")
            conn.commit()

            res2 = conn.execute("SELECT COUNT(*) FROM cash_closed_months WHERE month=9 AND year=2026").fetchone()
            assert res2[0] == 0

    def test_handover_reset_snapshot(self, temp_db_path):
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cash_reset_snapshot (crew_id, payroll_month, payroll_year, cleared_cash)
                VALUES (1, 9, 2026, 1500.0)
            """)
            conn.commit()

            row = cursor.execute("""
                SELECT cleared_cash FROM cash_reset_snapshot WHERE crew_id=1 AND payroll_month=9 AND payroll_year=2026
            """).fetchone()

            assert row is not None
            assert row[0] == 1500.0
