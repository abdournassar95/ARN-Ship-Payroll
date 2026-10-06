# tests/test_p0_regressions.py
"""
اختبارات حراسة (Regression Guards) لعيوب حزمة P0 التي أُصلحت في مراجعة 2026-10-06:

  1) لا يوجد أي اعتماد على مكتبة ``reportlab`` في المشروع (كانت غير مذكورة في الاعتماديات).
  2) الحذف الشامل لبيانات البحار وتهيئة النظام لا يتركان سجلات يتيمة
     (وثائق / لقطات عهدة / تنبيهات).
  3) إجماليات كشف المسير (PDF و Excel) تطابق مخرجات محرك الرواتب حرفياً،
     مع ظهور عمودَي «رصيد سابق» و«خصم مباشر».
  4) تقارير PDF تُظهر النص العربي بشكل صحيح بدل الصناديق الفارغة.
"""
import glob
import os
import re
import sqlite3

import pytest

from crew_service import delete_crew_cascade, reset_all_data
from database import init_db
from report_service import ReportService

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# بيانات تشغيلية تحاكي مخرجات PayrollEngine (total_due يشمل الإضافي والرصيد السابق والخصم)
SAMPLE_ROWS = [
    dict(id=1, name="أحمد محمود", rank="MASTER", basic_wage=3000.0, worked_days=300.0,
         total_due=50200.00, curr_extra=200.0, curr_ded=0.0, prev_balance=0.0,
         payment_cash=1200.0, cigarette=60.0, transfer=2000.0,
         total_received=3260.0, final_balance=46940.00, month=10, year=2026, is_settled=False),
    dict(id=2, name="محمد عبد الله", rank="CH.ENG", basic_wage=3800.0, worked_days=226.0,
         total_due=28476.67, curr_extra=0.0, curr_ded=150.0, prev_balance=0.0,
         payment_cash=800.0, cigarette=0.0, transfer=1000.0,
         total_received=1800.0, final_balance=26676.67, month=10, year=2026, is_settled=False),
    dict(id=3, name="عمر خالد", rank="BOSUN", basic_wage=1800.0, worked_days=281.0,
         total_due=16860.00, curr_extra=0.0, curr_ded=0.0, prev_balance=-500.0,
         payment_cash=300.0, cigarette=90.0, transfer=400.0,
         total_received=790.0, final_balance=16070.00, month=10, year=2026, is_settled=False),
]


def _no_whitespace(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _pdf_text(path: str) -> str:
    """استخراج نص أول صفحة من ملف PDF عبر محرك Qt (بدون مكتبات خارجية)."""
    from PyQt6.QtPdf import QPdfDocument

    doc = QPdfDocument(None)
    doc.load(path)
    if doc.pageCount() < 1:
        raise AssertionError(f"ملف PDF بلا صفحات: {path}")
    selection = doc.getAllText(0)
    raw = selection.text() if hasattr(selection, "text") else str(selection)
    return _no_whitespace(raw)


def _seed_crew(db_path: str, crew_id: int) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO CrewWages (No, Name, Rank, MonthlyWage, PeriodFrom) "
            "VALUES (?, 'بحار قديم', 'OILER', 1500, '2026-01-01')", (crew_id,))
        conn.execute(
            "INSERT INTO payroll_history (crew_id, payroll_month, payroll_year, payment_cash) "
            "VALUES (?, 10, 2026, 400.0)", (crew_id,))
        conn.execute(
            "INSERT INTO crew_documents (crew_id, doc_type, doc_number, issue_date, expiry_date) "
            "VALUES (?, 'شهادة الأهلية', 'COC-7', '2020-01-01', '2027-01-01')", (crew_id,))
        conn.execute(
            "INSERT INTO cash_reset_snapshot (crew_id, payroll_month, payroll_year, cleared_cash) "
            "VALUES (?, 10, 2026, 400.0)", (crew_id,))
        conn.execute(
            "INSERT INTO alerts_history (rule_code, message, severity, target_type, target_id, target_name) "
            "VALUES ('CERT_EXPIRY', 'تنبيه تجريبي', 'WARNING', 'CREW', ?, 'بحار قديم')", (crew_id,))
        conn.commit()


@pytest.mark.unit
class TestNoReportlabDependency:
    def test_no_reportlab_imports_anywhere_in_project(self):
        offenders = []
        for path in glob.glob(os.path.join(PROJECT_ROOT, "*.py")) + \
                    glob.glob(os.path.join(PROJECT_ROOT, "tests", "*.py")):
            with open(path, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith(("import reportlab", "from reportlab")):
                        offenders.append(f"{os.path.basename(path)}:{lineno}")
        assert offenders == [], f"تم العثور على استيراد reportlab في: {offenders}"

    def test_exports_work_without_reportlab(self, tmp_path):
        from alert_service import AlertService
        from audit_service import AuditService

        db_path = str(tmp_path / "no_reportlab.db")
        init_db(db_path)

        audit = AuditService(db_path)
        audit.log(1, "admin", "LOGIN", "users", 1, "تسجيل دخول تجريبي")
        assert audit.export_pdf(str(tmp_path / "audit.pdf"), audit.get_logs()) is True

        alerts_export = AlertService(db_path).export_pdf(
            str(tmp_path / "alerts.pdf"),
            [{"triggered_at": "2026-10-06 10:00:00", "rule_code": "LOW_CASH",
              "severity": "CRITICAL", "target_name": "صندوق القبطان",
              "message": "رصيد الصندوق منخفض", "is_read": 0, "is_resolved": 0}],
        )
        assert alerts_export is True
        assert os.path.getsize(str(tmp_path / "audit.pdf")) > 0
        assert os.path.getsize(str(tmp_path / "alerts.pdf")) > 0


@pytest.mark.database
class TestCrewDeletionCleanup:
    def test_delete_crew_removes_all_related_records(self, temp_db_path):
        _seed_crew(temp_db_path, 7)

        summary = delete_crew_cascade(temp_db_path, 7)

        with sqlite3.connect(temp_db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM CrewWages WHERE No=7").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM payroll_history WHERE crew_id=7").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM crew_documents WHERE crew_id=7").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM cash_reset_snapshot WHERE crew_id=7").fetchone()[0] == 0
            unresolved = conn.execute(
                "SELECT COUNT(*) FROM alerts_history WHERE target_type='CREW' AND target_id=7 AND is_resolved=0"
            ).fetchone()[0]
            assert unresolved == 0

        assert summary["documents"] == 1
        assert summary["snapshots"] == 1
        assert summary["alerts_closed"] == 1

    def test_new_crew_does_not_inherit_old_documents(self, temp_db_path):
        _seed_crew(temp_db_path, 7)
        delete_crew_cascade(temp_db_path, 7)

        # بحار جديد بنفس رقم السجل (سيناريو واقعي عند إعادة ترقيم الطاقم)
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute(
                "INSERT INTO CrewWages (No, Name, Rank, MonthlyWage, PeriodFrom) "
                "VALUES (7, 'بحار جديد', 'OILER', 1600, '2026-10-01')")
            conn.commit()
            docs = conn.execute("SELECT COUNT(*) FROM crew_documents WHERE crew_id=7").fetchone()[0]
        assert docs == 0, "البحار الجديد وَرِث وثائق بحار قديم محذوف"

    def test_reset_all_data_clears_operational_tables(self, temp_db_path):
        _seed_crew(temp_db_path, 7)
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("INSERT INTO general_cash (amount, type, description, date) "
                         "VALUES (5000, 'وارد', 'تمويل', '2026-10-01')")
            conn.execute("INSERT INTO cash_closed_months (month, year) VALUES (9, 2026)")
            conn.commit()

        reset_all_data(temp_db_path)

        with sqlite3.connect(temp_db_path) as conn:
            for table in ("CrewWages", "payroll_history", "general_cash",
                          "cash_closed_months", "cash_reset_snapshot",
                          "crew_documents", "alerts_history"):
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                assert count == 0, f"الجدول {table} لم يُفرَّغ"
            # الإعدادات وقواعد التنبيهات والمستخدمون تبقى كما هي
            assert conn.execute("SELECT COUNT(*) FROM alerts_rules").fetchone()[0] == 8
            assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2


@pytest.mark.unit
class TestPayrollSheetTotalsMatchEngine:
    def test_excel_row_totals_equal_engine_total_due(self, tmp_path):
        import openpyxl

        out_xlsx = str(tmp_path / "sheet.xlsx")
        ReportService.export_payroll_to_excel(SAMPLE_ROWS, 10, 2026, output_path=out_xlsx)

        wb = openpyxl.load_workbook(out_xlsx)
        ws = wb["Payroll_2026_10"]

        headers = [cell.value for cell in ws[3]]
        assert "خصم مباشر ($)" in headers
        assert "رصيد سابق ($)" in headers

        due_col = headers.index("إجمالي المستحق ($)") + 1
        ded_col = headers.index("خصم مباشر ($)") + 1
        prev_col = headers.index("رصيد سابق ($)") + 1
        exported_due = []
        for i, row in enumerate(SAMPLE_ROWS):
            excel_row = 4 + i
            exported_due.append(ws.cell(row=excel_row, column=due_col).value)
            assert ws.cell(row=excel_row, column=ded_col).value == row["curr_ded"]
            assert ws.cell(row=excel_row, column=prev_col).value == row["prev_balance"]

        expected = [row["total_due"] for row in SAMPLE_ROWS]
        assert exported_due == pytest.approx(expected, abs=0.01)

    def test_pdf_sheet_totals_row_equals_engine_total_due(self, tmp_path):
        out_pdf = str(tmp_path / "sheet.pdf")
        ReportService.generate_monthly_payroll_sheet(SAMPLE_ROWS, 10, 2026, output_path=out_pdf)

        expected_total = sum(row["total_due"] for row in SAMPLE_ROWS)
        expected_net = sum(row["final_balance"] for row in SAMPLE_ROWS)

        text = _pdf_text(out_pdf)
        assert f"{expected_total:,.2f}" in text, "إجمالي المستحق في الكشف لا يطابق المحرك"
        assert f"{expected_net:,.2f}" in text
        # الكشف يجب أن يُظهر العمودين الجديدين («رصيد سابق» و«خصم مباشر»)
        # ملاحظة: استخراج النص من PDF قد يعيد ترتيب مقاطع RTL، لذلك نفحص الكلمات فرادى
        for keyword in ("رصيد", "سابق", "خصم", "مباشر"):
            assert keyword in text, f"كلمة «{keyword}» غير موجودة في كشف المسير"


@pytest.mark.unit
class TestArabicPdfReports:
    def test_audit_report_renders_arabic_text(self, temp_db_path, tmp_path):
        from audit_service import AuditService

        svc = AuditService(temp_db_path)
        svc.log(1, "admin", "LOGIN", "users", 1, "تسجيل دخول ناجح للمدير عبده رجب نصار")

        out_pdf = str(tmp_path / "audit_ar.pdf")
        assert svc.export_pdf(out_pdf, svc.get_logs(), vessel_name="ARN Pioneer") is True

        text = _pdf_text(out_pdf)
        assert "تسجيلدخول" in text, "النص العربي غير موجود في تقرير PDF (مشكلة الخطوط)"
        assert "\u25af" not in text, "ظهرت صناديق فارغة بدل الحروف العربية"

    def test_alerts_report_renders_arabic_text(self, temp_db_path, tmp_path):
        from alert_service import AlertService

        out_pdf = str(tmp_path / "alerts_ar.pdf")
        ok = AlertService(temp_db_path).export_pdf(
            out_pdf,
            [{"triggered_at": "2026-10-06 10:00:00", "rule_code": "LOW_CASH",
              "severity": "CRITICAL", "target_name": "صندوق القبطان",
              "message": "رصيد صندوق القبطان منخفض", "is_read": 0, "is_resolved": 0}],
        )
        assert ok is True
        text = _pdf_text(out_pdf)
        assert "صندوقالقبطان" in text
        assert "\u25af" not in text
