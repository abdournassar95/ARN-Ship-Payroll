# ui_admin.py
import sqlite3
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QLineEdit, QFrame, 
    QGraphicsDropShadowEffect, QMessageBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView, QWidget, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QCursor
from auth_service import AuthService
from utils import normalize_role
import config
import paths
import settings_service

class AdminWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # المسار يأتي من النافذة الأم إن توفّر، وإلا من paths (ثابت) — العيب F12
        engine = getattr(parent, 'engine', None)
        self.db_path = str(getattr(engine, 'db_path', '') or paths.db_path_str())
        self.setWindowTitle("لوحة تحكم المدير ⚙️")
        self.resize(880, 760)
        self.setMinimumSize(820, 680)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.build_ui()
        self.load_settings()
        self.load_users()

    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 10))
        widget.setGraphicsEffect(shadow)

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(20)

        # 1. إعدادات النظام (الشركة والسفينة)
        card1 = QFrame()
        card1.setObjectName("Card")
        self.add_shadow(card1)
        card1_layout = QVBoxLayout(card1)
        
        lbl1 = QLabel("إعدادات النظام 🚢")
        font_lbl1 = QFont("Cairo", 14)
        font_lbl1.setBold(True)
        lbl1.setFont(font_lbl1)
        lbl1.setAlignment(Qt.AlignmentFlag.AlignRight)
        card1_layout.addWidget(lbl1)
        
        sys_layout = QHBoxLayout()
        sys_layout.setSpacing(12)

        lbl_company = QLabel("اسم الشركة:")
        lbl_company.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        lbl_company.setStyleSheet("color: #cbd5e1;")

        self.e_company = QLineEdit()
        self.e_company.setPlaceholderText("أدخل اسم الشركة...")
        self.e_company.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.e_company.setFont(QFont("Cairo", 11))

        lbl_vessel = QLabel("اسم السفينة:")
        lbl_vessel.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        lbl_vessel.setStyleSheet("color: #cbd5e1;")

        self.e_vessel = QLineEdit()
        self.e_vessel.setPlaceholderText("أدخل اسم السفينة...")
        self.e_vessel.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.e_vessel.setFont(QFont("Cairo", 11))

        btn_save_sys = QPushButton("حفظ الإعدادات 💾")
        btn_save_sys.setObjectName("Primary")
        btn_save_sys.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        btn_save_sys.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_save_sys.clicked.connect(self.save_settings)

        sys_layout.addWidget(lbl_company)
        sys_layout.addWidget(self.e_company, 2)
        sys_layout.addWidget(lbl_vessel)
        sys_layout.addWidget(self.e_vessel, 2)
        sys_layout.addWidget(btn_save_sys)
        card1_layout.addLayout(sys_layout)
        main_layout.addWidget(card1)

        # 2. الرقابة والتنبيهات الذكية
        card_audit = QFrame()
        card_audit.setObjectName("Card")
        self.add_shadow(card_audit)
        audit_layout = QVBoxLayout(card_audit)

        lbl_audit = QLabel("الرقابة الذكية وسجل التدقيق 🛡️")
        lbl_audit.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        lbl_audit.setStyleSheet("color: #38bdf8;")
        audit_layout.addWidget(lbl_audit)

        btn_row = QHBoxLayout()
        btn_audit_log = QPushButton("📋 فتح سجل التدقيق")
        btn_audit_log.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        btn_audit_log.setStyleSheet("background-color: #1e293b; color: #10b981; border: 1px solid #10b981; border-radius: 6px; padding: 7px 14px;")
        btn_audit_log.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_audit_log.clicked.connect(self.open_audit_log_win)

        btn_rules = QPushButton("⚙️ ضبط قواعد التنبيهات")
        btn_rules.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        btn_rules.setStyleSheet("background-color: #1e293b; color: #f59e0b; border: 1px solid #f59e0b; border-radius: 6px; padding: 7px 14px;")
        btn_rules.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_rules.clicked.connect(self.open_rules_win)

        btn_center = QPushButton("🔔 مركز التنبيهات")
        btn_center.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        btn_center.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; border-radius: 6px; padding: 7px 14px;")
        btn_center.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_center.clicked.connect(self.open_center_win)

        btn_row.addWidget(btn_audit_log)
        btn_row.addWidget(btn_rules)
        btn_row.addWidget(btn_center)
        audit_layout.addLayout(btn_row)
        main_layout.addWidget(card_audit)

        # 3. النسخ الاحتياطي واستعادة البيانات
        card_backup = QFrame()
        card_backup.setObjectName("Card")
        self.add_shadow(card_backup)
        backup_layout = QVBoxLayout(card_backup)

        lbl_bk = QLabel("النسخ الاحتياطي واستعادة البيانات 💾")
        lbl_bk.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        lbl_bk.setStyleSheet("color: #a78bfa;")
        backup_layout.addWidget(lbl_bk)

        bk_desc = QLabel("حفظ نسخة احتياطية آمنة من قاعدة البيانات، أو استعادة نسخة سابقة مع الفحص الأوتوماتيكي لسلامة الملف.")
        bk_desc.setFont(QFont("Cairo", 9))
        bk_desc.setStyleSheet("color: #94a3b8;")
        backup_layout.addWidget(bk_desc)

        bk_btns_row = QHBoxLayout()
        btn_create_backup = QPushButton("📦  إنشاء نسخة احتياطية الآن (Backup Now)")
        btn_create_backup.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        btn_create_backup.setStyleSheet("background-color: #1e293b; color: #a78bfa; border: 1px solid #a78bfa; border-radius: 6px; padding: 7px 16px;")
        btn_create_backup.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_create_backup.clicked.connect(self.create_backup)

        btn_restore_backup = QPushButton("🔄  استعادة نسخة احتياطية (Restore)")
        btn_restore_backup.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        btn_restore_backup.setStyleSheet("background-color: #1e293b; color: #f43f5e; border: 1px solid #f43f5e; border-radius: 6px; padding: 7px 16px;")
        btn_restore_backup.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_restore_backup.clicked.connect(self.restore_backup)

        bk_btns_row.addWidget(btn_create_backup)
        bk_btns_row.addWidget(btn_restore_backup)
        bk_btns_row.addStretch()
        backup_layout.addLayout(bk_btns_row)
        main_layout.addWidget(card_backup)

        # 4. إدارة المستخدمين

        card2 = QFrame()
        card2.setObjectName("Card")
        self.add_shadow(card2)
        card2_layout = QVBoxLayout(card2)
        
        header2_layout = QHBoxLayout()
        lbl2 = QLabel("إدارة المستخدمين 👥")
        font_lbl2 = QFont("Cairo", 14)
        font_lbl2.setBold(True)
        lbl2.setFont(font_lbl2)
        lbl2.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        btn_add = QPushButton("إضافة مستخدم جديد ➕")
        btn_add.setObjectName("Success")
        btn_add.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        btn_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_add.clicked.connect(lambda: self.open_user_form())
        
        header2_layout.addWidget(lbl2)
        header2_layout.addStretch()
        header2_layout.addWidget(btn_add)
        card2_layout.addLayout(header2_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["الاسم الكامل", "اسم المستخدم", "الصلاحية", "الإجراءات"])
        self.table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        header = self.table.horizontalHeader()
        header.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        card2_layout.addWidget(self.table)
        main_layout.addWidget(card2)

    def load_settings(self):
        # مصدر واحد للإعدادات (العيب F1) — الصف الوحيد مهما كان معرّفه
        data = settings_service.get_system_settings(self.db_path)
        self.e_company.setText(str(data["company_name"] or ""))
        self.e_vessel.setText(str(data["vessel_name"] or ""))

    def save_settings(self):
        comp = self.e_company.text().strip()
        vess = self.e_vessel.text().strip()
        # حفظ صادق: رسالة خطأ صريحة بدل «نجاح» كاذب (العيب F1)
        if not settings_service.save_system_settings(comp, vess, self.db_path):
            QMessageBox.critical(
                self, "فشل الحفظ ❌",
                "لم يتم حفظ بيانات الشركة والسفينة.\nتحقّق من وجود جدول الإعدادات وصلاحية الكتابة على قاعدة البيانات."
            )
            return
        QMessageBox.information(self, "نجاح", "تم حفظ بيانات الشركة والسفينة بنجاح!")
        # تحديث شريط الرأس في النافذة الرئيسية فوراً
        if self.parent():
            p = self.parent()
            if hasattr(p, 'engine') and hasattr(p, 'title_info'):
                p.system_info = p.engine.get_system_info()
                p.title_info.setText(f"🚢  {p.system_info}")

    def load_users(self):
        self.table.setRowCount(0)
        conn = sqlite3.connect(self.db_path)
        users = conn.execute("SELECT id, username, full_name, role FROM users").fetchall()
        conn.close()
        
        for i, u in enumerate(users):
            u_id, username, full_name, role = u
            self.table.insertRow(i)
            self.table.setRowHeight(i, 52)
            
            item_fullname = QTableWidgetItem(full_name if full_name else username)
            item_fullname.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_fullname.setFont(QFont("Cairo", 11))
            
            item_user = QTableWidgetItem(username)
            item_user.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_user.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
            
            item_role = QTableWidgetItem(role)
            item_role.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_role.setFont(QFont("Cairo", 11))
            
            self.table.setItem(i, 0, item_fullname)
            self.table.setItem(i, 1, item_user)
            self.table.setItem(i, 2, item_role)
            
            # أزرار الإجراءات (تعديل - كلمة السر - حذف)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(6, 4, 6, 4)
            actions_layout.setSpacing(6)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            btn_edit = QPushButton("✏️ تعديل")
            btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_edit.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-weight: bold;
                    font-family: 'Cairo';
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            btn_edit.clicked.connect(lambda _, user_data=u: self.open_user_form(user_data))
            
            btn_pwd = QPushButton("🔑 كلمة السر")
            btn_pwd.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_pwd.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-weight: bold;
                    font-family: 'Cairo';
                }
                QPushButton:hover {
                    background-color: #d97706;
                }
            """)
            btn_pwd.clicked.connect(lambda _, uid=u_id, uname=username, fname=full_name: self.open_password_dialog(uid, uname, fname))
            
            btn_del = QPushButton("🗑️ حذف")
            btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_del.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-weight: bold;
                    font-family: 'Cairo';
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """)
            btn_del.clicked.connect(lambda _, uid=u_id, uname=username, fname=full_name: self.delete_user(uid, uname, fname))
            
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_pwd)
            actions_layout.addWidget(btn_del)
            
            self.table.setCellWidget(i, 3, actions_widget)

    def open_user_form(self, user_data=None):
        form = QDialog(self)
        is_edit = user_data is not None
        title = "تعديل بيانات المستخدم ✏️" if is_edit else "إضافة مستخدم جديد 👤"
        form.setWindowTitle(title)
        form.setFixedSize(400, 420)
        form.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        layout = QVBoxLayout(form)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(10)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        lbl_fullname = QLabel("الاسم الكامل:")
        lbl_fullname.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        e_fullname = QLineEdit()
        e_fullname.setPlaceholderText("مثلاً: عبده رجب نصار")
        e_fullname.setFont(QFont("Cairo", 11))
        
        lbl_username = QLabel("اسم المستخدم:")
        lbl_username.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        e_username = QLineEdit()
        e_username.setPlaceholderText("اسم المستخدم للدخول")
        e_username.setFont(QFont("Cairo", 11))
        
        lbl_password = QLabel("كلمة المرور:")
        lbl_password.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        e_password = QLineEdit()
        e_password.setEchoMode(QLineEdit.EchoMode.Password)
        e_password.setFont(QFont("Cairo", 11))
        if is_edit:
            e_password.setPlaceholderText("اتركها فارغة إذا لم تُرِد التغيير")
        else:
            e_password.setPlaceholderText("كلمة المرور")
            
        lbl_role = QLabel("الصلاحية:")
        lbl_role.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        c_role = QComboBox()
        c_role.setFont(QFont("Cairo", 11))
        c_role.addItems(config.KNOWN_ROLES)
        
        if is_edit:
            u_id, username, full_name, role = user_data
            e_fullname.setText(full_name if full_name else "")
            e_username.setText(username if username else "")
            # لا ترقية صامتة: القيمة غير المعروفة تُضاف كما هي بدل السقوط على Admin (العيب F5)
            normalized_role = normalize_role(role)
            if normalized_role:
                index = c_role.findText(normalized_role, Qt.MatchFlag.MatchFixedString)
                if index < 0:
                    c_role.addItem(normalized_role)
                    index = c_role.findText(normalized_role, Qt.MatchFlag.MatchFixedString)
                c_role.setCurrentIndex(max(index, 0))
                
        layout.addWidget(lbl_fullname)
        layout.addWidget(e_fullname)
        layout.addWidget(lbl_username)
        layout.addWidget(e_username)
        layout.addWidget(lbl_password)
        layout.addWidget(e_password)
        layout.addWidget(lbl_role)
        layout.addWidget(c_role)
        layout.addSpacing(10)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("حفظ البيانات 💾")
        btn_save.setObjectName("Primary")
        btn_save.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_save.clicked.connect(lambda: self.save_user(
            form, 
            e_fullname.text().strip(), 
            e_username.text().strip(), 
            e_password.text().strip(), 
            c_role.currentText(), 
            user_data
        ))
        
        btn_cancel = QPushButton("إلغاء ❌")
        btn_cancel.setObjectName("Outline")
        btn_cancel.setFont(QFont("Cairo", 11))
        btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_cancel.clicked.connect(form.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        form.exec()

    def save_user(self, form, full_name, username, password, role, user_data=None):
        if not full_name:
            QMessageBox.warning(form, "تنبيه", "يرجى إدخال الاسم الكامل!")
            return
        if not username:
            QMessageBox.warning(form, "تنبيه", "يرجى إدخال اسم المستخدم!")
            return

        # تطبيع الصلاحية ورفض القيم الفارغة (العيب F5)
        role = normalize_role(role)
        if role is None:
            QMessageBox.warning(form, "تنبيه", "يرجى اختيار صلاحية صحيحة للمستخدم!")
            return
            
        is_edit = user_data is not None
        auth = AuthService(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if is_edit:
                u_id = user_data[0]
                if password:
                    hashed = auth._hash_password(password)
                    cursor.execute(
                        "UPDATE users SET full_name=?, username=?, role=?, password_hash=?, password_salt=? WHERE id=?",
                        (full_name, username, role, hashed['hash'], hashed['salt'], u_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET full_name=?, username=?, role=? WHERE id=?",
                        (full_name, username, role, u_id)
                    )
                # تسجيل تغيير الصلاحية في سجل التدقيق (العيب F5)
                old_role = normalize_role(user_data[3]) if len(user_data) > 3 else None
                if old_role != role:
                    try:
                        from audit_service import AuditService
                        AuditService(self.db_path).log(
                            1, "ADMIN", "ROLE_CHANGED", "users", u_id,
                            f"تغيير صلاحية المستخدم {username} من «{old_role}» إلى «{role}»"
                        )
                    except Exception:
                        pass
                QMessageBox.information(self, "نجاح", f"تم تحديث بيانات المستخدم '{username}' بنجاح.")
            else:
                if not password:
                    QMessageBox.warning(form, "تنبيه", "كلمة المرور مطلوبة لإضافة مستخدم جديد!")
                    conn.close()
                    return
                hashed = auth._hash_password(password)
                cursor.execute(
                    "INSERT INTO users (full_name, username, role, password_hash, password_salt) VALUES (?, ?, ?, ?, ?)",
                    (full_name, username, role, hashed['hash'], hashed['salt'])
                )
                QMessageBox.information(self, "نجاح", f"تم إضافة المستخدم الجديد '{username}' بنجاح.")
                
            conn.commit()
            form.accept()
            self.load_users()
        except sqlite3.IntegrityError:
            QMessageBox.critical(form, "خطأ", "اسم المستخدم موجود بالفعل! يرجى اختيار اسم مستخدم آخر.")
        except Exception as e:
            QMessageBox.critical(form, "خطأ", f"حدث خطأ أثناء الحفظ:\n{str(e)}")
        finally:
            conn.close()

    def open_password_dialog(self, u_id, username, full_name):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"تعيين كلمة السر - {username}")
        dialog.setFixedSize(380, 260)
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(10)
        
        lbl_title = QLabel(f"تعيين كلمة مرور جديدة لـ: {full_name or username}")
        lbl_title.setFont(QFont("Cairo", 12, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        lbl_p1 = QLabel("كلمة المرور الجديدة:")
        lbl_p1.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        e_p1 = QLineEdit()
        e_p1.setEchoMode(QLineEdit.EchoMode.Password)
        e_p1.setPlaceholderText("أدخل كلمة المرور الجديدة")
        e_p1.setFont(QFont("Cairo", 11))
        
        lbl_p2 = QLabel("تأكيد كلمة المرور:")
        lbl_p2.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        e_p2 = QLineEdit()
        e_p2.setEchoMode(QLineEdit.EchoMode.Password)
        e_p2.setPlaceholderText("أعد إدخال كلمة المرور لتأكيدها")
        e_p2.setFont(QFont("Cairo", 11))
        
        layout.addWidget(lbl_p1)
        layout.addWidget(e_p1)
        layout.addWidget(lbl_p2)
        layout.addWidget(e_p2)
        layout.addSpacing(10)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("تحديث كلمة السر 🔑")
        btn_save.setObjectName("Primary")
        btn_save.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        def save_new_password():
            p1 = e_p1.text().strip()
            p2 = e_p2.text().strip()
            if not p1:
                QMessageBox.warning(dialog, "تنبيه", "يرجى إدخال كلمة المرور الجديدة!")
                return
            if p1 != p2:
                QMessageBox.warning(dialog, "تنبيه", "كلمتا المرور غير متطابقتين!")
                return
                
            try:
                auth = AuthService(self.db_path)
                hashed = auth._hash_password(p1)
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    "UPDATE users SET password_hash=?, password_salt=? WHERE id=?",
                    (hashed['hash'], hashed['salt'], u_id)
                )
                conn.commit()
                conn.close()
                QMessageBox.information(self, "نجاح", f"تم تغيير كلمة المرور للمستخدم '{username}' بنجاح.")
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(dialog, "خطأ", f"فشل تغيير كلمة المرور:\n{str(e)}")
                
        btn_save.clicked.connect(save_new_password)
        
        btn_cancel = QPushButton("إلغاء ❌")
        btn_cancel.setObjectName("Outline")
        btn_cancel.setFont(QFont("Cairo", 11))
        btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_cancel.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def delete_user(self, u_id, username, full_name):
        if username.lower() == 'admin':
            QMessageBox.warning(self, "حظر إجراء", "لا يمكن حذف حساب مدير النظام الرئيسي (admin)!")
            return
            
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف ⚠️",
            f"هل أنت متأكد من رغبتك في حذف المستخدم '{full_name or username}' ({username})؟\n\nلن يتمكن هذا المستخدم من تسجيل الدخول للنظام بعد الحذف.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("DELETE FROM users WHERE id=?", (u_id,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "نجاح", f"تم حذف المستخدم '{username}' بنجاح.")
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء حذف المستخدم:\n{str(e)}")

    def open_audit_log_win(self):
        try:
            from ui_audit_log import AuditLogWindow
            dlg = AuditLogWindow(parent=self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح سجل التدقيق: {e}")

    def open_rules_win(self):
        try:
            from ui_alerts_rules import AlertRulesDialog
            dlg = AlertRulesDialog(parent=self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح إعدادات القواعد: {e}")

    def open_center_win(self):
        try:
            from ui_alerts_center import AlertsCenterWindow
            dlg = AlertsCenterWindow(parent=self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح مركز التنبيهات: {e}")

    def create_backup(self):
        """إنشاء نسخة احتياطية آمنة من قاعدة البيانات"""
        import shutil
        import os
        from datetime import datetime

        db_path = self.db_path
        if not os.path.exists(db_path):
            QMessageBox.critical(self, "خطأ", f"لم يتم العثور على ملف قاعدة البيانات: {db_path}")
            return

        backups_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        os.makedirs(backups_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"arn_ship_payroll_backup_{timestamp}.db"
        default_path = os.path.join(backups_dir, default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ النسخة الاحتياطية", default_path, "SQLite Database (*.db)"
        )
        if not file_path:
            return

        try:
            shutil.copy2(db_path, file_path)
            if os.path.getsize(file_path) == 0:
                raise RuntimeError("فشل النسخ، حجم الملف الناتج 0 بايت.")

            try:
                from audit_service import AuditService
                AuditService(self.db_path).log(
                    1, "ADMIN", "BACKUP", "database", 0,
                    f"إنشاء نسخة احتياطية من قاعدة البيانات إلى: {os.path.basename(file_path)}"
                )
            except Exception:
                pass

            QMessageBox.information(
                self, "نجاح النسخ الاحتياطي 📦",
                f"تم حفظ النسخة الاحتياطية بنجاح في:\n\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل إنشاء النسخة الاحتياطية:\n{e}")

    def restore_backup(self):
        """استعادة نسخة احتياطية مع فحص السلامة (Integrity Check)"""
        import shutil
        import os

        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف النسخة الاحتياطية للاستعادة", "", "SQLite Database (*.db)"
        )
        if not file_path:
            return

        # 1. فحص سلامة الملف المختار
        try:
            with sqlite3.connect(file_path) as conn:
                check_result = conn.execute("PRAGMA integrity_check").fetchone()
                if not check_result or check_result[0].lower() != "ok":
                    raise ValueError(f"فشل فحص سلامة قاعدة البيانات: {check_result}")

                tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                required_tables = ['users', 'CrewWages', 'payroll_history']
                for req in required_tables:
                    if req not in tables:
                        raise ValueError(f"الملف المحدد لا يحتوي على جدول أساسي: {req}")

        except Exception as e:
            QMessageBox.critical(
                self, "ملف غير صالح ❌",
                f"الملف المحدد غير صالح كنسخة احتياطية لنظام ARN Payroll:\n\n{e}"
            )
            return

        # 2. تأكيد الاستعادة من المستخدم
        reply = QMessageBox.warning(
            self, "تحذير استعادة البيانات ⚠️",
            "أنت على وشك استعادة نسخة احتياطية.\n"
            "سيتم استبدال البيانات الحالية بالكامل بمحتويات النسخة المحددة!\n\n"
            f"الملف المختار: {os.path.basename(file_path)}\n\n"
            "هل ترغب في الاستمرار؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            db_path = self.db_path
            safety_copy = db_path + ".before_restore"
            if os.path.exists(db_path):
                shutil.copy2(db_path, safety_copy)

            shutil.copy2(file_path, db_path)

            try:
                from audit_service import AuditService
                AuditService(self.db_path).log(
                    1, "ADMIN", "RESTORE", "database", 0,
                    f"استعادة نسخة احتياطية من الملف: {os.path.basename(file_path)}"
                )
            except Exception:
                pass

            self.load_settings()
            self.load_users()

            QMessageBox.information(
                self, "نجاح الاستعادة 🔄",
                "تمت استعادة قاعدة البيانات بنجاح وتم تحديث بيانات النظام!"
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الاستعادة", f"فشلت عملية الاستعادة:\n{e}")