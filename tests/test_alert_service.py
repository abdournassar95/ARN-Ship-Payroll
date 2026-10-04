# tests/test_alert_service.py
import pytest
import sqlite3
from datetime import datetime, timedelta
from alert_service import AlertService

@pytest.mark.unit
class TestAlertService:
    @pytest.fixture
    def alert_svc(self, temp_db_path):
        return AlertService(temp_db_path)

    def test_low_cash_rule(self, alert_svc, temp_db_path):
        # لم يتم إضافة واردات، الرصيد 0 < 500
        fired = alert_svc.check_low_cash()
        assert fired is True

        alerts = alert_svc.get_alerts(severity="CRITICAL")
        assert len(alerts) >= 1
        assert "صندوق القبطان" in alerts[0]["message"]

    def test_high_advance_rule(self, alert_svc, temp_db_path):
        now = datetime.now()
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("INSERT INTO CrewWages (No, Name, MonthlyWage) VALUES (1, 'كابتن رامي', 2000.0)")
            # سلفة 1200 > 50% من 2000 (الحد 1000)
            conn.execute("""
                INSERT INTO payroll_history (crew_id, payroll_month, payroll_year, payment_cash)
                VALUES (1, ?, ?, 1200.0)
            """, (now.month, now.year))
            conn.commit()

        fired = alert_svc.check_high_advance(crew_id=1, month=now.month, year=now.year)
        assert fired is True

        alerts = alert_svc.get_alerts(severity="WARNING")
        assert any("كابتن رامي" in a["message"] for a in alerts)

    def test_contract_expiry_rule(self, alert_svc, temp_db_path):
        # عقد ينتهي بعد 15 يوماً (ضمن حد الـ 30 يوماً)
        exp_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("INSERT INTO CrewWages (No, Name, MonthlyWage, contract_end) VALUES (2, 'محمد علي', 1500.0, ?)", (exp_date,))
            conn.commit()

        fired = alert_svc.check_contract_expiry()
        assert fired is True
        alerts = alert_svc.get_alerts()
        assert any("محمد علي" in a["message"] for a in alerts)

    def test_unpaid_months_rule(self, alert_svc, temp_db_path):
        # بحار موجود منذ 4 أشهر ولم تسجل له أي مدفوعات
        start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("INSERT INTO CrewWages (No, Name, MonthlyWage, PeriodFrom) VALUES (3, 'سعيد محمود', 1800.0, ?)", (start_date,))
            conn.commit()

        fired = alert_svc.check_unpaid_months()
        assert fired is True
        alerts = alert_svc.get_alerts()
        assert any("سعيد محمود" in a["message"] for a in alerts)

    def test_cert_expiry_rule(self, alert_svc, temp_db_path):
        # شهادة تنتهي بعد 20 يوماً (ضمن حد الـ 60 يوماً)
        exp_date = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("INSERT INTO CrewWages (No, Name, MonthlyWage) VALUES (4, 'عمر خالد', 2500.0)")
            conn.execute("""
                INSERT INTO crew_documents (crew_id, doc_type, expiry_date)
                VALUES (4, 'جواز بحري', ?)
            """, (exp_date,))
            conn.commit()

        fired = alert_svc.check_cert_expiry()
        assert fired is True
        alerts = alert_svc.get_alerts(severity="CRITICAL")
        assert any("جواز بحري" in a["message"] for a in alerts)

    def test_login_failed_rule(self, alert_svc, temp_db_path):
        # تسجيل محاولتي دخول فاشلتين في audit_log
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("INSERT INTO audit_log (user_id, username, action, description, timestamp) VALUES (0, 'hacker', 'LOGIN_FAILED', 'فشل', ?)", (now_str,))
            conn.execute("INSERT INTO audit_log (user_id, username, action, description, timestamp) VALUES (0, 'hacker', 'LOGIN_FAILED', 'فشل', ?)", (now_str,))
            conn.commit()

        fired = alert_svc.check_login_failed()
        assert fired is True
        alerts = alert_svc.get_alerts()
        assert any("محاولات تسجيل دخول فاشلة" in a["message"] for a in alerts)

    def test_unusual_deduction_rule(self, alert_svc, temp_db_path):
        now = datetime.now()
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("INSERT INTO CrewWages (No, Name, MonthlyWage) VALUES (5, 'حسن إبراهيم', 3000.0)")
            # خصومات الشهور الثلاثة السابقة بمتوسط 50 دولار
            conn.execute("INSERT INTO payroll_history (crew_id, payroll_month, payroll_year, deduction) VALUES (5, 6, 2026, 50.0)")
            conn.execute("INSERT INTO payroll_history (crew_id, payroll_month, payroll_year, deduction) VALUES (5, 7, 2026, 50.0)")
            conn.execute("INSERT INTO payroll_history (crew_id, payroll_month, payroll_year, deduction) VALUES (5, 8, 2026, 50.0)")
            # خصم الشهر الحالي 300 دولار (> 200% من 50)
            conn.execute("INSERT INTO payroll_history (crew_id, payroll_month, payroll_year, deduction) VALUES (5, 9, 2026, 300.0)")
            conn.commit()

        fired = alert_svc.check_unusual_deduction(crew_id=5, month=9, year=2026)
        assert fired is True
        alerts = alert_svc.get_alerts()
        assert any("خصم مالي استثنائي" in a["message"] for a in alerts)

    def test_cooldown_prevents_duplicate_alerts(self, alert_svc, temp_db_path):
        # تشغيل LOW_CASH للمرة الأولى
        fired_first = alert_svc.check_low_cash()
        assert fired_first is True

        # تشغيلها للمرة الثانية فوراً يجب أن تمنع بسبب الـ Cooldown (24 ساعة)
        fired_second = alert_svc.check_low_cash()
        assert fired_second is False

    def test_mark_as_read_and_resolve(self, alert_svc, temp_db_path):
        alert_svc.check_low_cash()
        alerts = alert_svc.get_alerts(only_unresolved=True)
        assert len(alerts) >= 1
        aid = alerts[0]["id"]

        assert alert_svc.mark_as_read(aid) is True
        assert alert_svc.resolve_alert(aid, resolved_by_user_id=1) is True

        unresolved = alert_svc.get_alerts(only_unresolved=True)
        assert not any(a["id"] == aid for a in unresolved)

    def test_update_rule_configuration(self, alert_svc):
        ok = alert_svc.update_rule("LOW_CASH", threshold_value=750.0, cooldown_hours=12, severity="WARNING", is_enabled=True, sound_enabled=False)
        assert ok is True

        rule = alert_svc._get_rule("LOW_CASH")
        assert rule["threshold_value"] == 750.0
        assert rule["cooldown_hours"] == 12
        assert rule["severity"] == "WARNING"
        assert rule["sound_enabled"] == 0
