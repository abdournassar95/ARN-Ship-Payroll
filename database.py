# database.py
import sqlite3
import hashlib
import base64
from db_safety import connect

def init_db(db_path='arn_ship_payroll.db'):
    conn = connect(db_path)
    cursor = conn.cursor()
    
    # 1. جدول المستخدمين
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        password_salt TEXT,
        must_change_password INTEGER NOT NULL DEFAULT 0,
        full_name TEXT,
        role TEXT
    )''')
    
    # 2. جدول الرواتب
    cursor.execute('''CREATE TABLE IF NOT EXISTS CrewWages (
        No INTEGER PRIMARY KEY AUTOINCREMENT, 
        Name TEXT, 
        Rank TEXT, 
        PeriodFrom TEXT, 
        MonthlyWage REAL DEFAULT 0, 
        PREVIOUS REAL DEFAULT 0,
        PaidMonthsData TEXT DEFAULT '{}', 
        WageHistory TEXT DEFAULT '{}'
    )''')
    
    # 3. جدول السجل المالي (للرواتب)
    cursor.execute('''CREATE TABLE IF NOT EXISTS payroll_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        crew_id INTEGER, 
        payroll_month INTEGER, 
        payroll_year INTEGER, 
        extra REAL DEFAULT 0, 
        deduction REAL DEFAULT 0, 
        payment_cash REAL DEFAULT 0, 
        cigarette REAL DEFAULT 0, 
        transfer REAL DEFAULT 0, 
        UNIQUE(crew_id, payroll_month, payroll_year)
    )''')

    # 4. جدول صندوق القبطان (المصروفات العامة)
    cursor.execute('''CREATE TABLE IF NOT EXISTS general_cash (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        type TEXT,
        description TEXT,
        date TEXT
    )''')

    # 5. جداول صندوق القبطان الإضافية (إقفال الشهور والعهد المسلمة)
    cursor.execute('''CREATE TABLE IF NOT EXISTS cash_closed_months (
        month INTEGER, 
        year INTEGER, 
        PRIMARY KEY(month, year)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS cash_reset_snapshot (
        crew_id INTEGER, 
        payroll_month INTEGER, 
        payroll_year INTEGER, 
        cleared_cash REAL, 
        PRIMARY KEY(crew_id, payroll_month, payroll_year)
    )''')

    # 6. جدول إعدادات النظام (الشركة والسفينة)
    cursor.execute('''CREATE TABLE IF NOT EXISTS system_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT,
        vessel_name TEXT
    )''')
    
    # التأكد من وجود سجل واحد للإعدادات
    cursor.execute("SELECT COUNT(*) FROM system_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO system_settings (company_name, vessel_name) VALUES (?, ?)", 
                       ("ARN Fleet", "Default Vessel"))

    # 7. جدول سجل التدقيق (Audit Trail)
    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        table_name TEXT,
        record_id INTEGER,
        description TEXT NOT NULL,
        timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)")

    # 8. جدول قواعد التنبيهات الذكية (Alert Rules)
    cursor.execute('''CREATE TABLE IF NOT EXISTS alerts_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_code TEXT UNIQUE NOT NULL,
        rule_name TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL,
        threshold_value REAL,
        severity TEXT NOT NULL,
        is_enabled INTEGER DEFAULT 1,
        cooldown_hours INTEGER NOT NULL,
        sound_enabled INTEGER DEFAULT 1
    )''')

    # البذر التلقائي للقواعد الـ 8 الافتراضية
    cursor.execute("SELECT COUNT(*) FROM alerts_rules")
    if cursor.fetchone()[0] == 0:
        default_rules = [
            ("LOW_CASH", "رصيد الصندوق منخفض", "تنبيه عند انخفاض رصيد صندوق القبطان عن الحد الأدنى", "CASH", 500.0, "CRITICAL", 1, 24, 1),
            ("HIGH_ADVANCE", "سلفة نقدية مرتفعة", "تنبيه عند تجاوز سلفة البحار الشهرية 50% من راتبه الأساسي", "CREW", 50.0, "WARNING", 1, 48, 1),
            ("CONTRACT_EXPIRY", "اقتراب انتهاء العقد", "تنبيه قبل انتهاء عقد البحار بـ 30 يوماً أو أقل", "CREW", 30.0, "WARNING", 1, 168, 1),
            ("UNPAID_MONTHS", "شهور متتالية بلا صرف", "تنبيه عند مرور 3 شهور متتالية لبحار دون صرف راتب أو معاملة", "PAYROLL", 3.0, "WARNING", 1, 168, 1),
            ("MONTH_NOT_CLOSED", "شهر مالي غير مقفل", "تنبيه عند بقاء الشهر مفتوحاً دون إقفال لأكثر من 45 يوماً", "SYSTEM", 45.0, "INFO", 1, 168, 0),
            ("CERT_EXPIRY", "اقتراب انتهاء شهادة ملاحية", "تنبيه قبل انتهاء صلاحية شهادة البحار بـ 60 يوماً أو أقل", "CREW", 60.0, "CRITICAL", 1, 168, 1),
            ("LOGIN_FAILED", "محاولات دخول فاشلة متكررة", "تنبيه عند تسجيل محاولتي دخول فاشلتين أو أكثر خلال 30 دقيقة", "SYSTEM", 2.0, "WARNING", 1, 1, 1),
            ("UNUSUAL_DEDUCTION", "خصم مالي غير طبيعي", "تنبيه عند تجاوز الخصم 200% من متوسط خصومات البحار لآخر 3 شهور", "PAYROLL", 200.0, "CRITICAL", 1, 24, 1)
        ]
        cursor.executemany("""
            INSERT INTO alerts_rules (rule_code, rule_name, description, category, threshold_value, severity, is_enabled, cooldown_hours, sound_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, default_rules)

    # 9. جدول التنبيهات المُطلقة (Alerts History)
    cursor.execute('''CREATE TABLE IF NOT EXISTS alerts_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id INTEGER,
        rule_code TEXT NOT NULL,
        triggered_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        target_type TEXT,
        target_id INTEGER,
        target_name TEXT,
        message TEXT NOT NULL,
        severity TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        is_resolved INTEGER DEFAULT 0,
        resolved_at TEXT,
        resolved_by INTEGER,
        FOREIGN KEY(rule_id) REFERENCES alerts_rules(id)
    )''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_unread ON alerts_history(is_read, is_resolved)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts_history(triggered_at)")

    # 10. جدول شهادات ووثائق البحارة (Crew Documents)
    cursor.execute('''CREATE TABLE IF NOT EXISTS crew_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crew_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        doc_number TEXT,
        issue_date TEXT,
        expiry_date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY(crew_id) REFERENCES CrewWages(No) ON DELETE CASCADE
    )''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_expiry ON crew_documents(expiry_date)")
    
    # ضمان وجود الأعمدة الأساسية (إصلاح وترحيل الأعمدة المفقودة)
    try:
        cursor.execute("ALTER TABLE payroll_history ADD COLUMN payment_cash REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password_salt TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE general_cash ADD COLUMN date TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE CrewWages ADD COLUMN contract_start TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE CrewWages ADD COLUMN contract_end TEXT")
    except sqlite3.OperationalError:
        pass

    
    # Existing installations keep their current password policy; new seed accounts must rotate.
    if 'must_change_password' not in {row[1] for row in cursor.execute("PRAGMA table_info(users)")}:
        cursor.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")

    # Require rotation on legacy installations still using the published seed password.
    for user_name, default_password in (("admin", "admin123"), ("captain", "captain123")):
        row = cursor.execute("SELECT id, password_hash, password_salt FROM users WHERE username=?", (user_name,)).fetchone()
        if row and row[1] and row[2]:
            try:
                salt = base64.b64decode(row[2])
                expected = base64.b64encode(hashlib.pbkdf2_hmac(
                    'sha256', default_password.encode(), salt, 100000)).decode()
                if expected == row[1]:
                    cursor.execute("UPDATE users SET must_change_password=1 WHERE id=?", (row[0],))
            except (ValueError, TypeError):
                pass

    # إنشاء حسابات افتراضية مشفرة بـ PBKDF2 إذا كان الجدول فارغاً
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        import os
        def _hash_pw(password: str):
            salt = os.urandom(32)
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return base64.b64encode(key).decode('utf-8'), base64.b64encode(salt).decode('utf-8')
        
        admin_hash, admin_salt = _hash_pw("admin123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, password_salt, full_name, role, must_change_password) VALUES (?, ?, ?, ?, ?, 1)",
            ("admin", admin_hash, admin_salt, "عبده رجب نصار", "Admin")
        )
        
        capt_hash, capt_salt = _hash_pw("captain123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, password_salt, full_name, role, must_change_password) VALUES (?, ?, ?, ?, ?, 1)",
            ("captain", capt_hash, capt_salt, "قبطان السفينة", "Captain")
        )
        
    conn.commit()
    conn.close()


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    # عند تشغيل هذا الملف مباشرة، سيقوم بإصلاح قاعدة البيانات
    init_db()
    print("تم فحص وتحديث قاعدة البيانات بنجاح.")
