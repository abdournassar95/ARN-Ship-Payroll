# tests/test_auth_service.py
import pytest
import time

@pytest.mark.auth
class TestAuthService:
    def test_default_admin_login(self, auth_service):
        result = auth_service.authenticate("admin", "admin123")
        assert result["success"] is True
        assert result["user"]["role"] == "Admin"
        assert "عبده رجب نصار" in result["user"]["full_name"]

    def test_default_captain_login(self, auth_service):
        result = auth_service.authenticate("captain", "captain123")
        assert result["success"] is True
        assert result["user"]["role"] == "Captain"

    def test_login_invalid_password(self, auth_service):
        result = auth_service.authenticate("admin", "wrong_password")
        assert result["success"] is False
        assert "غير صحيحة" in result["message"]

    def test_login_nonexistent_user(self, auth_service):
        result = auth_service.authenticate("ghost_user", "password123")
        assert result["success"] is False
        assert "غير صحيحة" in result["message"]

    def test_login_empty_fields(self, auth_service):
        res1 = auth_service.authenticate("", "admin123")
        assert res1["success"] is False
        assert "الرجاء إدخال جميع البيانات" in res1["message"]

        res2 = auth_service.authenticate("admin", "")
        assert res2["success"] is False

    def test_account_lockout_after_three_failed_attempts(self, auth_service):
        # 3 محاولات خاطئة متتالية
        for _ in range(3):
            auth_service.authenticate("admin", "wrong_pass")

        # المحاولة الرابعة يجب أن تعود بالحساب مقفل
        result = auth_service.authenticate("admin", "admin123")
        assert result["success"] is False
        assert "مقفل مؤقتاً" in result["message"]

    def test_create_and_authenticate_new_user(self, auth_service):
        auth_service.create_test_user("officer1", "secret456", full_name="محمد علي", role="Officer")
        result = auth_service.authenticate("officer1", "secret456")
        assert result["success"] is True
        assert result["user"]["full_name"] == "محمد علي"
        assert result["user"]["role"] == "Officer"

    def test_password_hashing_is_salted(self, auth_service):
        h1 = auth_service._hash_password("mypassword")
        h2 = auth_service._hash_password("mypassword")
        # التمليح العشوائي يضمن اختلاف الـ hash لنفس كلمة المرور
        assert h1["salt"] != h2["salt"]
        assert h1["hash"] != h2["hash"]
        # كلاهما يتحقق بنجاح من الكلمة
        assert auth_service._verify_password("mypassword", h1["salt"], h1["hash"])
        assert auth_service._verify_password("mypassword", h2["salt"], h2["hash"])
