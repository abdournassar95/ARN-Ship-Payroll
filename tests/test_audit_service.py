# tests/test_audit_service.py
import pytest
from audit_service import AuditService

@pytest.mark.unit
class TestAuditService:
    @pytest.fixture
    def audit_svc(self, temp_db_path):
        return AuditService(temp_db_path)

    def test_log_and_retrieve_basic_event(self, audit_svc):
        ok = audit_svc.log(1, "admin", "LOGIN", "users", 1, "تسجيل دخول تجريبي")
        assert ok is True

        logs = audit_svc.get_logs()
        assert len(logs) >= 1
        assert logs[0]["action"] == "LOGIN"
        assert logs[0]["username"] == "admin"
        assert "تسجيل دخول تجريبي" in logs[0]["description"]

    def test_log_convenience_methods(self, audit_svc):
        audit_svc.log_create(1, "admin", "CrewWages", 10, "إضافة بحار جديد")
        audit_svc.log_update(1, "admin", "CrewWages", 10, "تعديل راتب البحار")
        audit_svc.log_delete(1, "admin", "CrewWages", 10, "حذف بحار")
        audit_svc.log_auth(1, "admin", "LOGIN_FAILED", "فشل تسجيل الدخول")

        logs = audit_svc.get_logs()
        actions = [l["action"] for l in logs]
        assert "CREATE" in actions
        assert "UPDATE" in actions
        assert "DELETE" in actions
        assert "LOGIN_FAILED" in actions

    def test_filter_by_user_and_action(self, audit_svc):
        audit_svc.log(1, "admin", "CREATE", "CrewWages", 1, "إضافة بحار")
        audit_svc.log(2, "captain", "CLOSE_MONTH", "cash_closed_months", 1, "إقفال شهر")

        admin_logs = audit_svc.get_logs(user_filter="admin")
        assert all(l["username"] == "admin" for l in admin_logs)

        close_logs = audit_svc.get_logs(action_filter="CLOSE_MONTH")
        assert len(close_logs) == 1
        assert close_logs[0]["action"] == "CLOSE_MONTH"

    def test_search_text_filtering(self, audit_svc):
        audit_svc.log(1, "admin", "UPDATE", "CrewWages", 5, "تعديل بحار باسم أحمد محمود")
        audit_svc.log(1, "admin", "UPDATE", "general_cash", 1, "شراء مؤن غذائية للسفينة")

        results = audit_svc.get_logs(search_text="أحمد محمود")
        assert len(results) == 1
        assert "أحمد محمود" in results[0]["description"]

    def test_distinct_users_and_actions(self, audit_svc):
        audit_svc.log(1, "admin", "CREATE")
        audit_svc.log(2, "captain", "UPDATE")

        users = audit_svc.get_distinct_users()
        actions = audit_svc.get_distinct_actions()

        assert "admin" in users
        assert "captain" in users
        assert "CREATE" in actions
        assert "UPDATE" in actions

    def test_export_pdf(self, audit_svc, tmp_path):
        audit_svc.log(1, "admin", "CREATE", "CrewWages", 1, "سجل اختبار PDF")
        logs = audit_svc.get_logs()
        pdf_file = tmp_path / "test_audit.pdf"
        
        ok = audit_svc.export_pdf(str(pdf_file), logs, vessel_name="ARN Pioneer")
        assert ok is True
        assert pdf_file.exists()
        assert pdf_file.stat().st_size > 0
