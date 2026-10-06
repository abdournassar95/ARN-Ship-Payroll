# ui_login.py
import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QMessageBox, QFrame, QProgressBar,
    QToolButton, QGraphicsDropShadowEffect, QDialog, QDialogButtonBox, QFormLayout
)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QFont, QColor, QCursor

from auth_service import AuthService
import config

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        # إزالة إطار النظام لعنوان مخصص
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setObjectName("LoginWindow")
        self.setFixedSize(480, 650)
        
        self.prefs_file = "login_prefs.json"
        self.auth_service = AuthService()
        
        # متغيرات لسحب النافذة
        self.dragging = False
        self.drag_position = QPoint()
        
        self.init_ui()
        self.apply_stylesheet()
        self.load_saved_username()
        self.center_window()

    def center_window(self):
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    # ====== أحداث الفأرة لسحب النافذة ======
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    # ====== واجهة المستخدم ======
    def init_ui(self):
        # الحاوية الرئيسية
        main_container = QVBoxLayout(self)
        main_container.setContentsMargins(24, 24, 24, 24)

        # البطاقة الزجاجية
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        
        # ✅ إضافة الظل بالطريقة الصحيحة (بدلاً من box-shadow في QSS)
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 45))  # ظل أسود شفاف
        self.card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 24, 30, 28)
        card_layout.setSpacing(12)

        # ---- شريط العنوان المخصص ----
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        
        app_title = QLabel("⚓ ARN Fleet")
        app_title.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        app_title.setObjectName("LoginBrand")
        
        btn_minimize = QToolButton()
        btn_minimize.setText("─")
        btn_minimize.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_minimize.setAccessibleName("تصغير النافذة")
        btn_minimize.clicked.connect(self.showMinimized)
        
        btn_close = QToolButton()
        btn_close.setText("✕")
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.setAccessibleName("إغلاق النافذة")
        btn_close.clicked.connect(self.close)

        title_bar.addWidget(app_title)
        title_bar.addStretch()
        title_bar.addWidget(btn_minimize)
        title_bar.addWidget(btn_close)
        card_layout.addLayout(title_bar)
        
        # فاصل
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {config.COLOR_BORDER}; max-height: 1px;")
        card_layout.addWidget(line)

        card_layout.addSpacing(5)

        # الشعار
        logo = QLabel("⚓")
        logo.setObjectName("LoginMark")
        logo.setFont(QFont("Arial", 38))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(logo)

        # العناوين
        title = QLabel("تسجيل الدخول")
        title.setFont(QFont("Cairo", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("LoginTitle")
        card_layout.addWidget(title)

        subtitle = QLabel("أدخل بياناتك للوصول إلى لوحة القيادة")
        subtitle.setFont(QFont("Cairo", 9))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("LoginSubtitle")
        card_layout.addWidget(subtitle)

        # ---- حقل اسم المستخدم ----
        username_label = QLabel("اسم المستخدم")
        username_label.setObjectName("LoginFieldLabel")
        card_layout.addWidget(username_label)
        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("أدخل اسم المستخدم")
        self.username_entry.setAccessibleName("اسم المستخدم")
        self.username_entry.setMinimumHeight(42)
        card_layout.addWidget(self.username_entry)

        # ---- حقل كلمة المرور ----
        password_label = QLabel("كلمة المرور")
        password_label.setObjectName("LoginFieldLabel")
        card_layout.addWidget(password_label)
        pwd_layout = QHBoxLayout()
        self.password_entry = QLineEdit()
        self.password_entry.setPlaceholderText("أدخل كلمة المرور")
        self.password_entry.setAccessibleName("كلمة المرور")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setMinimumHeight(42)

        self.toggle_pwd_btn = QToolButton()
        self.toggle_pwd_btn.setText("👁")
        self.toggle_pwd_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.toggle_pwd_btn.setAccessibleName("إظهار أو إخفاء كلمة المرور")
        self.toggle_pwd_btn.clicked.connect(self.toggle_password_visibility)

        pwd_layout.addWidget(self.password_entry)
        pwd_layout.addWidget(self.toggle_pwd_btn)
        pwd_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addLayout(pwd_layout)

        # ---- خيار تذكرني ----
        options_layout = QHBoxLayout()
        self.remember_cb = QCheckBox("  تذكر اسم المستخدم")
        self.remember_cb.setFont(QFont("Cairo", 9))
        self.remember_cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        options_layout.addWidget(self.remember_cb)
        options_layout.addStretch()
        card_layout.addLayout(options_layout)

        card_layout.addSpacing(5)

        # ---- زر تسجيل الدخول + شريط التحميل ----
        self.login_btn = QPushButton("تسجيل الدخول")
        self.login_btn.setObjectName("PrimaryButton")
        self.login_btn.setMinimumHeight(44)
        self.login_btn.setFont(QFont("Cairo", 12, QFont.Weight.Bold))
        self.login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_btn.clicked.connect(self.authenticate)
        card_layout.addWidget(self.login_btn)

        # شريط تقدم مخفي
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.hide()
        card_layout.addWidget(self.progress_bar)

        # ربط ضغط Enter
        self.password_entry.returnPressed.connect(self.authenticate)
        self.username_entry.returnPressed.connect(self.password_entry.setFocus)

        main_container.addWidget(self.card)

        # الفوتر
        footer = QLabel("Developed by Abdou Ragab Nassar © 2026")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(QFont("Cairo", 8))
        footer.setObjectName("LoginFooter")
        main_container.addWidget(footer)

    def apply_stylesheet(self):
        self.setStyleSheet(config.LOGIN_STYLESHEET)

    # ====== وظائف مساعدة ======
    def toggle_password_visibility(self):
        if self.password_entry.echoMode() == QLineEdit.EchoMode.Password:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pwd_btn.setText("🙈")
        else:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pwd_btn.setText("👁")

    def load_saved_username(self):
        if os.path.exists(self.prefs_file):
            try:
                with open(self.prefs_file, 'r') as f:
                    data = json.load(f)
                if username := data.get("username", ""):
                    self.username_entry.setText(username)
                    self.remember_cb.setChecked(True)
            except (json.JSONDecodeError, IOError):
                pass

    def save_username(self, username):
        if self.remember_cb.isChecked():
            with open(self.prefs_file, 'w') as f:
                json.dump({"username": username}, f)
        else:
            if os.path.exists(self.prefs_file):
                os.remove(self.prefs_file)

    # ====== المصادقة الأساسية ======
    def authenticate(self):
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال اسم المستخدم وكلمة المرور.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("جاري التحقق...")
        self.progress_bar.show()
        
        QTimer.singleShot(100, self._perform_authentication)

    def _perform_authentication(self):
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()
        
        result = self.auth_service.authenticate(username, password)

        self.login_btn.setEnabled(True)
        self.login_btn.setText("تسجيل الدخول")
        self.progress_bar.hide()

        if result["success"]:
            if result["user"].get("must_change_password"):
                if not self.require_password_change(result["user"]["id"], password):
                    self.password_entry.clear()
                    return
            self.save_username(username)
            self.open_dashboard(
                result["user"]["id"],
                result["user"]["full_name"],
                result["user"]["role"]
            )
        else:
            QMessageBox.critical(self, "فشل تسجيل الدخول", result["message"])
            self.password_entry.clear()
            self.password_entry.setFocus()

    def require_password_change(self, user_id, old_password):
        dialog = QDialog(self)
        dialog.setWindowTitle("تغيير كلمة المرور الأولية")
        layout = QFormLayout(dialog)
        first = QLineEdit(dialog)
        second = QLineEdit(dialog)
        for field in (first, second):
            field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("كلمة مرور جديدة (12 حرفاً على الأقل):", first)
        layout.addRow("تأكيد كلمة المرور:", second)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(buttons)
        buttons.rejected.connect(dialog.reject)

        def submit():
            if first.text() != second.text():
                QMessageBox.warning(dialog, "تنبيه", "كلمتا المرور غير متطابقتين")
                return
            try:
                self.auth_service.change_password(user_id, old_password, first.text())
            except ValueError as error:
                QMessageBox.warning(dialog, "تنبيه", str(error))
                return
            dialog.accept()

        buttons.accepted.connect(submit)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def open_dashboard(self, user_id, full_name, role):
        try:
            from ui_dashboard import MainDashboard
            self.dashboard = MainDashboard(user_id, full_name, role)
            self.dashboard.show()
            self.close()
        except ImportError:
            QMessageBox.critical(self, "خطأ", "لم يتم العثور على ui_dashboard.py")