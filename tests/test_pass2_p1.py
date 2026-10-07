# tests/test_pass2_p1.py
"""
اختبارات حراسة لعيوب «حزمة P1» — مراجعة 2026-10-06 (القسم 10):

  F3) حرس الإقفال الشهري: لا كتابة على شهر مقفل من أي مسار + صفر استعلام محلي مكرّر.
  F2) رفض القيم السالبة في مسارات الإدخال المالي (مع بقاء «رصيد سابق» ذا إشارة).
  F4) تعريف واحد لرصيد الصندوق يستخدمه التنبيه والشاشة والتقرير.
  F7) طبقة اتصال موحّدة تُفعّل PRAGMA foreign_keys/WAL في كل مسار.
"""
import io
import os
import sqlite3

import pytest

import cash_service
import db
import month_guard
from database import init_db
from utils import parse_non_negative

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def finance_db(tmp_path):
    """قاعدة مالية ببيانات سبتمبر/أكتوبر لإعادة إنتاج سيناريو العيب F4."""
    db_path = str(tmp_path / "finance.db")
    init_db(db_path)
    with db.session(db_path) as conn:
        # سبتمبر: وارد 10,000 وصادر 2,000 ⇒ الرصيد المرحّل 8,000
        conn.execute("INSERT INTO general_cash (amount, type, description, date) VALUES (10000, 'وارد', 'دفعة سبتمبر', '2026-09-05')")
        conn.execute("INSERT INTO general_cash (amount, type, description, date) VALUES (2000, 'صادر', 'مصروف سبتمبر', '2026-09-20')")
        # أكتوبر: لا حركة إطلاقاً
        conn.execute("INSERT INTO CrewWages (No, Name, Rank, MonthlyWage) VALUES (1, 'أحمد محمود', 'MASTER', 3000)")
    return db_path


# ══════════════════════════════════════════════════════════════
# F7 — طبقة الاتصال الموحّدة
# ══════════════════════════════════════════════════════════════
class TestUnifiedConnectionLayer:
    def test_connect_applies_pragmas(self, tmp_path):
        db_path = str(tmp_path / "pragmas.db")
        init_db(db_path)
        with db.connect(db_path) as conn:
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == db.BUSY_TIMEOUT_MS
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.lower() in ("wal", "delete")   # delete فقط لو نظام ملفات لا يدعم WAL

    def test_session_rolls_back_on_error(self, tmp_path):
        db_path = str(tmp_path / "rollback.db")
        init_db(db_path)
        with pytest.raises(RuntimeError):
            with db.session(db_path) as conn:
                conn.execute("INSERT INTO CrewWages (No, Name) VALUES (77, 'مؤقت')")
                raise RuntimeError("فشل مقصود")

        with db.session(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM CrewWages WHERE No=77").fetchone()[0] == 0

    def test_session_commits_and_closes(self, tmp_path):
        db_path = str(tmp_path / "commit.db")
        init_db(db_path)
        with db.session(db_path) as conn:
            conn.execute("INSERT INTO CrewWages (No, Name) VALUES (5, 'بحار')")
        with db.session(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM CrewWages WHERE No=5").fetchone()[0] == 1

    def test_no_raw_sqlite_connect_in_app_modules(self):
        """حاجز: كل الاتصالات تمرّ عبر db.py (عدا الاختبارات والمكتبات الجديدة نفسها)."""
        allowed = {"db.py"}
        offenders = []
        for name in sorted(os.listdir(PROJECT_ROOT)):
            if not name.endswith(".py") or name in allowed:
                continue
            content = io.open(os.path.join(PROJECT_ROOT, name), encoding="utf-8").read()
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""'):
                    continue
                if "sqlite3.connect(" in stripped:
                    offenders.append(f"{name}: {stripped[:70]}")
        # paths.py يذكره داخل توثيق فقط، وdb.py هو الطبقة نفسها
        offenders = [o for o in offenders if not o.startswith("paths.py")]
        assert offenders == [], f"اتصالات مباشرة خارج db.py: {offenders}"


# ══════════════════════════════════════════════════════════════
# F3 — حرس الإقفال الشهري
# ══════════════════════════════════════════════════════════════
class TestMonthGuard:
    def test_close_and_detect(self, finance_db):
        assert month_guard.is_month_closed(2026, 10, finance_db) is False
        assert month_guard.close_month(2026, 10, finance_db) is True
        assert month_guard.is_month_closed(2026, 10, finance_db) is True
        assert (2026, 10) in month_guard.closed_months(finance_db)
        assert month_guard.open_month(2026, 10, finance_db) is True
        assert month_guard.is_month_closed(2026, 10, finance_db) is False

    def test_assert_month_open_raises_with_arabic_message(self, finance_db):
        month_guard.close_month(2026, 10, finance_db)
        with pytest.raises(month_guard.MonthClosedError) as exc:
            month_guard.assert_month_open(2026, 10, finance_db)
        assert "أكتوبر" in str(exc.value)
        assert "مقفل" in str(exc.value)

    def test_assert_months_open_reports_all_blocked(self, finance_db):
        month_guard.close_month(2026, 9, finance_db)
        month_guard.close_month(2026, 10, finance_db)
        with pytest.raises(month_guard.MonthClosedError) as exc:
            month_guard.assert_months_open([(2026, 9), (2026, 10), (2026, 11)], finance_db)
        assert len(exc.value.months) == 2          # نوفمبر مفتوح فلم يُذكر
        assert month_guard.assert_months_open([(2026, 11)], finance_db) is None

    def test_settlement_change_writes_marker_in_db(self, finance_db):
        """«تسوية 🔒» تُحفظ في PaidMonthsData — والمقفل يُرفض من التطبيق لا من القاعدة."""
        with db.session(finance_db) as conn:
            conn.execute("UPDATE CrewWages SET PaidMonthsData=? WHERE No=1", ('{"2026-09": true}',))
        with db.session(finance_db) as conn:
            assert conn.execute("SELECT PaidMonthsData FROM CrewWages WHERE No=1").fetchone()[0] == '{"2026-09": true}'


# ══════════════════════════════════════════════════════════════
# F4 — تعريف رصيد الصندوق الواحد
# ══════════════════════════════════════════════════════════════
class TestUnifiedCashBalance:
    def test_carried_balance_from_previous_months(self, finance_db):
        # قبل أكتوبر: وارد 10,000 − صادر 2,000 = 8,000
        assert cash_service.carried_balance(2026, 10, finance_db) == 8000.0
        # داخل سبتمبر لا يوجد عهدة سابقة
        assert cash_service.carried_balance(2026, 9, finance_db) == 0.0

    def test_month_flow_is_month_scoped(self, finance_db):
        flow = cash_service.month_flow(2026, 9, finance_db)
        assert flow["in"] == 10000.0 and flow["out"] == 2000.0
        assert cash_service.month_flow(2026, 10, finance_db)["month_net"] == 0.0

    def test_balance_includes_carried_even_in_empty_month(self, finance_db):
        """شهر بلا حركة لا يُظهر صفراً — الرصيد 8,000 كما في الخزنة فعلاً."""
        assert cash_service.cash_balance(2026, 10, finance_db) == 8000.0
        summary = cash_service.month_summary(2026, 10, finance_db)
        assert summary["old_adv"] == 8000.0
        assert summary["net"] == 8000.0

    def test_alert_matches_screen_balance(self, finance_db):
        """تنبيه «رصيد منخفض» يستخدم نفس رقم الشاشة/التقرير (العيب F4)."""
        from alert_service import AlertService
        service = AlertService(finance_db)

        # الحد 500 ⇒ لا تنبيه (الرصيد 8,000)
        with db.session(finance_db) as conn:
            conn.execute("UPDATE alerts_rules SET threshold_value=500 WHERE rule_code='LOW_CASH'")
        assert service.check_low_cash() is False

        # الحد 9,000 ⇒ يجب أن يُطلق التنبيه اعتماداً على الرصيد التراكمي نفسه
        with db.session(finance_db) as conn:
            conn.execute("UPDATE alerts_rules SET threshold_value=9000 WHERE rule_code='LOW_CASH'")
        assert service.check_low_cash() is True
        assert abs(cash_service.cash_balance(db_path=finance_db) - 8000.0) < 0.01

    def test_master_cash_report_shows_carried_balance(self, finance_db, tmp_path):
        """تقرير صندوق القبطان: «عهدة سابقة» = الرصيد الحقيقي لا صفراً، والاسم من الإعدادات."""
        from report_service import ReportService
        from PyQt6.QtPdf import QPdfDocument

        summary = cash_service.month_summary(2026, 10, finance_db)
        out_pdf = str(tmp_path / "cash_report.pdf")
        ReportService.generate_master_cash_report(10, 2026, [], summary, output_path=out_pdf)

        doc = QPdfDocument(None)
        doc.load(out_pdf)
        text = doc.getAllText(0).text()
        assert "8,000.00" in text, "«عهدة سابقة» لم تُطبع بالقيمة الحقيقية"
        assert "ARN FLEET MANAGEMENT" in text     # الافتراضي من الإعدادات

    def test_crew_advances_and_clearance_affect_balance(self, finance_db):
        with db.session(finance_db) as conn:
            conn.execute(
                "INSERT INTO payroll_history (crew_id, payroll_month, payroll_year, payment_cash) VALUES (1, 10, 2026, 1500)"
            )
        # سلفة أكتوبر 1,500 تُخصم من الرصيد المرحّل
        assert cash_service.cash_balance(2026, 10, finance_db) == 6500.0
        with db.session(finance_db) as conn:
            conn.execute(
                "INSERT INTO cash_reset_snapshot (crew_id, payroll_month, payroll_year, cleared_cash) VALUES (1, 10, 2026, 500)"
            )
        assert cash_service.cash_balance(2026, 10, finance_db) == 7000.0


# ══════════════════════════════════════════════════════════════
# F2 — رفض القيم السالبة
# ══════════════════════════════════════════════════════════════
class TestNonNegativeValues:
    @pytest.mark.parametrize("raw,expected", [
        ("1500", 1500.0), ("1,500.50", 1500.5), ("0", 0.0), (" 300 ", 300.0),
    ])
    def test_accepts_valid_values(self, raw, expected):
        assert parse_non_negative(raw, "الإضافي") == expected

    @pytest.mark.parametrize("raw", ["-100", "-0.01", "سالب", "", "   ", None])
    def test_rejects_negative_and_invalid(self, raw):
        with pytest.raises(ValueError):
            parse_non_negative(raw, "الإضافي")

    def test_error_message_names_the_field(self):
        with pytest.raises(ValueError) as exc:
            parse_non_negative("-50", "سلفة الكاش")
        assert "سلفة الكاش" in str(exc.value)

    def test_accounting_reads_form_with_validators(self):
        """حاجز كودي: نموذج المحاسبة ومحاسبة القبطان يستخدمان المُحقِّق المشترك."""
        accounting = io.open(os.path.join(PROJECT_ROOT, "ui_accounting.py"), encoding="utf-8").read()
        assert "parse_non_negative(self.extra_e.text()" in accounting
        assert "parse_non_negative(self.wage_e.text()" in accounting
        # «رصيد سابق» يبقى ذا إشارة عن قصد (سالب = البحار مدين للشركة)
        assert "رصيد سابق» يبقى ذا إشارة" in accounting

        cash = io.open(os.path.join(PROJECT_ROOT, "ui_master_cash.py"), encoding="utf-8").read()
        assert "parse_non_negative(amt_str" in cash

    def test_engine_still_supports_signed_previous_balance(self):
        """تأكيد مقصود: الرصيد السابق السالب (دين البحار) مدعوم في المحرك والكشف."""
        from report_service import ReportService
        crew = [dict(id=9, name="مدين", rank="BOSUN", basic_wage=1000.0, worked_days=300.0,
                     total_due=1000.0, curr_extra=0.0, curr_ded=0.0, prev_balance=-500.0,
                     payment_cash=0.0, cigarette=0.0, transfer=0.0,
                     total_received=0.0, final_balance=1500.0, month=10, year=2026)]
        # _normalize_crew_data تستقبل سجلاً واحداً وتُعيد قاموساً مُطبَّعاً
        row = ReportService._normalize_crew_data(crew[0])
        assert float(row["prev_balance"]) == -500.0
        # ثبات هوية الكشف مع المحرك: total_earnings == إجمالي المستحق القادم من المحرك
        assert float(row["total_earnings"]) == 1000.0
        assert float(row["total_due"]) == 1500.0          # أجر الفترة بعد استبعاد الرصيد السابق


# ══════════════════════════════════════════════════════════════
# RTL/التكامل — النافذة المالية تستخدم الوحدات الموحّدة
# ══════════════════════════════════════════════════════════════
class TestFinancialViewsUseUnifiedModules:
    def test_master_cash_uses_cash_service_and_month_guard(self):
        src = io.open(os.path.join(PROJECT_ROOT, "ui_master_cash.py"), encoding="utf-8").read()
        assert "cash_service.carried_balance(" in src
        assert "month_guard.is_month_closed(" in src
        assert "month_guard.close_month(" in src
        assert "'old_adv': carried" in src
        # لم يبق استعلام إقفال محلي مكرّر
        assert "SELECT COUNT(*) FROM cash_closed_months" not in src

    def test_accounting_guards_closed_months_before_write(self):
        src = io.open(os.path.join(PROJECT_ROOT, "ui_accounting.py"), encoding="utf-8").read()
        assert "month_guard.assert_months_open(" in src
        assert "can_manage_settlement" in src
        assert "paid_status_changes" in src

    def test_alert_service_uses_cash_service(self):
        src = io.open(os.path.join(PROJECT_ROOT, "alert_service.py"), encoding="utf-8").read()
        assert "cash_service.cash_balance(" in src
        assert "SELECT SUM(amount) FROM general_cash" not in src
