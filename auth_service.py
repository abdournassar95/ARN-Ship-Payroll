# auth_service.py
import os
import sqlite3
import hashlib
import base64
import time

class AuthService:
    def __init__(self, db_path='arn_ship_payroll.db'):
        self.db_path = db_path
        self.failed_attempts = {}  # {username: [count, lock_until]}

    def _hash_password(self, password: str) -> dict:
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return {
            'salt': base64.b64encode(salt).decode('utf-8'),
            'hash': base64.b64encode(key).decode('utf-8')
        }

    def _verify_password(self, password: str, stored_salt: str, stored_hash: str) -> bool:
        salt = base64.b64decode(stored_salt.encode('utf-8'))
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return base64.b64encode(key).decode('utf-8') == stored_hash

    def _is_account_locked(self, username: str) -> bool:
        if username not in self.failed_attempts:
            return False
        count, lock_until = self.failed_attempts[username]
        if lock_until and time.time() < lock_until:
            return True
        if lock_until and time.time() >= lock_until:
            self.failed_attempts[username] = [0, None]
        return False

    def _record_failed_attempt(self, username: str):
        if username not in self.failed_attempts:
            self.failed_attempts[username] = [0, None]
        count, _ = self.failed_attempts[username]
        count += 1
        if count >= 3:
            lock_until = time.time() + (5 * 60)
            self.failed_attempts[username] = [count, lock_until]
        else:
            self.failed_attempts[username] = [count, None]

    def _reset_failed_attempts(self, username: str):
        if username in self.failed_attempts:
            self.failed_attempts[username] = [0, None]

    def authenticate(self, username: str, password: str) -> dict:
        if not username or not password:
            return {"success": False, "message": "الرجاء إدخال جميع البيانات"}

        if self._is_account_locked(username):
            remaining = int(self.failed_attempts[username][1] - time.time())
            return {"success": False, "message": f"الحساب مقفل مؤقتاً. حاول بعد {remaining // 60} دقيقة و {remaining % 60} ثانية."}

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, full_name, role, password_hash, password_salt FROM users WHERE username = ?",
                    (username,)
                )
                user = cursor.fetchone()

            if not user:
                self._record_failed_attempt(username)
                try:
                    from audit_service import AuditService
                    AuditService(self.db_path).log(0, username or "UNKNOWN", "LOGIN_FAILED", "users", None, f"محاولة دخول فاشلة للمستخدم {username} (المستخدم غير موجود)")
                    from alert_service import AlertService
                    AlertService(self.db_path).check_login_failed()
                except Exception:
                    pass
                return {"success": False, "message": "اسم المستخدم أو كلمة المرور غير صحيحة."}

            is_valid = self._verify_password(password, user['password_salt'], user['password_hash'])
            if is_valid:
                self._reset_failed_attempts(username)
                try:
                    from audit_service import AuditService
                    AuditService(self.db_path).log(user['id'], username, "LOGIN", "users", user['id'], f"تسجيل دخول ناجح للمستخدم {user['full_name']} ({user['role']})")
                except Exception:
                    pass
                return {
                    "success": True,
                    "message": "تم تسجيل الدخول بنجاح",
                    "user": {"id": user['id'], "full_name": user['full_name'], "role": user['role']}
                }
            else:
                self._record_failed_attempt(username)
                try:
                    from audit_service import AuditService
                    AuditService(self.db_path).log(user['id'], username, "LOGIN_FAILED", "users", user['id'], f"محاولة دخول فاشلة للمستخدم {username} (كلمة مرور خاطئة)")
                    from alert_service import AlertService
                    AlertService(self.db_path).check_login_failed()
                except Exception:
                    pass
                return {"success": False, "message": "اسم المستخدم أو كلمة المرور غير صحيحة."}

        except sqlite3.Error as e:
            return {"success": False, "message": f"خطأ في قاعدة البيانات: {str(e)}"}


    def create_test_user(self, username, password, full_name="Admin", role="admin"):
        hashed = self._hash_password(password)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users (username, full_name, role, password_hash, password_salt)
                    VALUES (?, ?, ?, ?, ?)
                """, (username, full_name, role, hashed['hash'], hashed['salt']))
                conn.commit()
                print(f"✅ تم إنشاء المستخدم {username} بنجاح!")
        except sqlite3.OperationalError as e:
            print(f"⚠️ خطأ: تأكد من وجود عمودي password_salt في جدول users. التفاصيل: {e}")