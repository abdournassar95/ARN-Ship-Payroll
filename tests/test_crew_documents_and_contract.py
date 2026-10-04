# tests/test_crew_documents_and_contract.py
import pytest
import sqlite3

class TestCrewDocumentsAndContract:
    """اختبارات وثائق وشهادات البحارة وتحديث تواريخ العقود"""

    def test_crew_contract_dates_update(self, temp_db_path):
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO CrewWages (Name, Rank, MonthlyWage, PeriodFrom, contract_start, contract_end)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("محمود سالم", "2nd.OFF", 2500.0, "2026-01-01", "2026-01-01", "2026-07-01"))
            cid = cursor.lastrowid
            conn.commit()

            # تجديد وتمديد العقد
            cursor.execute("""
                UPDATE CrewWages 
                SET contract_start = ?, contract_end = ? 
                WHERE No = ?
            """, ("2026-07-01", "2027-01-01", cid))
            conn.commit()

            row = cursor.execute("SELECT contract_start, contract_end FROM CrewWages WHERE No = ?", (cid,)).fetchone()
            assert row[0] == "2026-07-01"
            assert row[1] == "2027-01-01"

    def test_add_and_delete_crew_document(self, temp_db_path):
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO CrewWages (Name, Rank, MonthlyWage, PeriodFrom)
                VALUES ('علي حسني', 'BOSUN', 1800.0, '2026-01-01')
            """)
            cid = cursor.lastrowid

            # إضافة شهادة
            cursor.execute("""
                INSERT INTO crew_documents (crew_id, doc_type, doc_number, issue_date, expiry_date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cid, "جواز سفر بحري", "SB123456", "2025-01-01", "2027-01-01", "ساري"))
            doc_id = cursor.lastrowid
            conn.commit()

            assert doc_id is not None
            doc_count = cursor.execute("SELECT COUNT(*) FROM crew_documents WHERE crew_id = ?", (cid,)).fetchone()[0]
            assert doc_count == 1

            # حذف الشهادة
            cursor.execute("DELETE FROM crew_documents WHERE id = ?", (doc_id,))
            conn.commit()
            doc_count2 = cursor.execute("SELECT COUNT(*) FROM crew_documents WHERE crew_id = ?", (cid,)).fetchone()[0]
            assert doc_count2 == 0

    def test_fleet_documents_alert_and_report(self, temp_db_path):
        from alert_service import AlertService
        from report_service import ReportService
        import os
        from datetime import datetime, timedelta

        with sqlite3.connect(temp_db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO CrewWages (Name, Rank, MonthlyWage, PeriodFrom) VALUES ('أحمد سعيد', 'MASTER', 5000.0, '2026-01-01')")
            cid = c.lastrowid
            
            # شهادة تنتهي بعد 15 يوماً (تنتهي قريباً)
            exp_soon = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
            c.execute("""
                INSERT INTO crew_documents (crew_id, doc_type, doc_number, issue_date, expiry_date, notes)
                VALUES (?, 'شهادة الأهلية والربانية', 'COC-9988', '2021-01-01', ?, 'تحتاج تجديد')
            """, (cid, exp_soon))
            
            # شهادة منتهية منذ 10 أيام
            exp_past = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            c.execute("""
                INSERT INTO crew_documents (crew_id, doc_type, doc_number, issue_date, expiry_date, notes)
                VALUES (?, 'كشف طبي بحري', 'MED-1122', '2024-01-01', ?, 'منتهي')
            """, (cid, exp_past))
            conn.commit()

        # فحص إطلاق التنبيهات للشهادات
        service = AlertService(temp_db_path)
        alert_fired = service.check_cert_expiry()
        assert alert_fired is True

        # فحص توليد تقرير PDF للشهادات
        docs = [
            {
                'crew_name': 'أحمد سعيد',
                'crew_rank': 'MASTER',
                'doc_type': 'شهادة الأهلية والربانية',
                'doc_number': 'COC-9988',
                'issue_date': '2021-01-01',
                'expiry_date': exp_soon,
                'notes': 'تحتاج تجديد'
            }
        ]
        pdf_path = ReportService.generate_documents_report(docs, filter_title="كافة أفراد الطاقم")
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0

