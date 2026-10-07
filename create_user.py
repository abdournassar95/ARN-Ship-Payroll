"""
إنشاء المستخدم الإداري الأولي (يُنفَّذ يدوياً فقط عند الحاجة).

ملاحظة أمنية (العيب F11): كان الملف يعيد ضبط كلمة مرور المدير إلى «2314» عند كل تشغيل،
والآن لا يعيد الضبط إن كان المستخدم موجوداً بالفعل.
"""
from auth_service import AuthService
from utils import normalize_role

DEFAULT_USERNAME = "admin"


def main():
    auth = AuthService()
    if not auth.user_exists(DEFAULT_USERNAME):
        auth.create_test_user(DEFAULT_USERNAME, "2314", "مدير النظام",
                              normalize_role("Admin"))
        print(f"✅ تم إنشاء المستخدم {DEFAULT_USERNAME} — يُنصح بتغيير كلمة المرور فوراً.")
    else:
        print(f"ℹ️ المستخدم {DEFAULT_USERNAME} موجود بالفعل — لم يُعدَّل شيء.")


if __name__ == "__main__":
    main()