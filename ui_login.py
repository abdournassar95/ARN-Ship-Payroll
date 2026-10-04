# ui_login.py
import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QMessageBox, QFrame, QProgressBar,
    QToolButton, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QFont, QColor, QCursor

from auth_service import AuthService

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        # إزالة إطار النظام لعنوان مخصص
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 620)
        
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
        main_container.setContentsMargins(30, 30, 30, 40)

        # البطاقة الزجاجية
        self.card = QFrame()
        self.card.setObjectName("GlassCard")
        
        # ✅ إضافة الظل بالطريقة الصحيحة (بدلاً من box-shadow في QSS)
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 80))  # ظل أسود شفاف
        self.card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(25, 20, 25, 30)
        card_layout.setSpacing(10)

        # ---- شريط العنوان المخصص ----
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        
        app_title = QLabel("⚓ ARN Fleet")
        app_title.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        app_title.setStyleSheet("color: #0f172a;")
        
        btn_minimize = QToolButton()
        btn_minimize.setText("─")
        btn_minimize.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_minimize.setStyleSheet("QToolButton { background: transparent; font-size: 16px; padding: 5px; }")
        btn_minimize.clicked.connect(self.showMinimized)
        
        btn_close = QToolButton()
        btn_close.setText("✕")
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.setStyleSheet("QToolButton { background: transparent; font-size: 16px; padding: 5px; color: #ef4444; }")
        btn_close.clicked.connect(self.close)

        title_bar.addWidget(app_title)
        title_bar.addStretch()
        title_bar.addWidget(btn_minimize)
        title_bar.addWidget(btn_close)
        card_layout.addLayout(title_bar)
        
        # فاصل
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #e2e8f0; max-height: 1px;")
        card_layout.addWidget(line)

        card_layout.addSpacing(5)

        # الشعار
        logo = QLabel("🔐")
        logo.setFont(QFont("Arial", 45))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(logo)

        # العناوين
        title = QLabel("تسجيل الدخول")
        title.setFont(QFont("Cairo", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #0f172a;")
        card_layout.addWidget(title)

        subtitle = QLabel("أدخل بياناتك للوصول إلى لوحة القيادة")
        subtitle.setFont(QFont("Cairo", 9))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #64748b; margin-bottom: 10px;")
        card_layout.addWidget(subtitle)

        # ---- حقل اسم المستخدم ----
        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("👤  اسم المستخدم")
        self.username_entry.setMinimumHeight(42)
        card_layout.addWidget(self.username_entry)

        # ---- حقل كلمة المرور ----
        pwd_layout = QHBoxLayout()
        self.password_entry = QLineEdit()
        self.password_entry.setPlaceholderText("🔑  كلمة المرور")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setMinimumHeight(42)

        self.toggle_pwd_btn = QToolButton()
        self.toggle_pwd_btn.setText("👁")
        self.toggle_pwd_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.toggle_pwd_btn.setStyleSheet("QToolButton { border: none; padding: 0px 10px; background: transparent; }")
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
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: rgba(0,0,0,0.05);
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #38bdf8;
                border-radius: 2px;
            }
        """)
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
        footer.setStyleSheet("color: #94a3b8; margin-top: 5px;")
        main_container.addWidget(footer)

    def apply_stylesheet(self):
        # ✅ تم حذف خاصية box-shadow نهائياً من هنا
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                font-family: 'Cairo';
            }
            QFrame#GlassCard {
                background-color: rgba(255, 255, 255, 210);
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.6);
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.9);
                border: 1.5px solid #e2e8f0;
                border-radius: 12px;
                padding: 8px 15px;
                font-size: 13px;
                color: #1e293b;
            }
            QLineEdit:focus {
                border: 1.5px solid #38bdf8;
                background-color: white;
            }
            QCheckBox {
                color: #475569;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 1.5px solid #cbd5e1;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #0ea5e9;
                border: 1.5px solid #0ea5e9;
            }
            QPushButton#PrimaryButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #38bdf8, stop:1 #0284c7);
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton#PrimaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #0ea5e9, stop:1 #0369a1);
            }
            QPushButton#PrimaryButton:pressed {
                background: #075985;
            }
            QPushButton#PrimaryButton:disabled {
                background: #94a3b8;
            }
        """)

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

    def open_dashboard(self, user_id, full_name, role):
        try:
            from ui_dashboard import MainDashboard
            self.dashboard = MainDashboard(user_id, full_name, role)
            self.dashboard.show()
            self.close()
        except ImportError:
            QMessageBox.critical(self, "خطأ", "لم يتم العثور على ui_dashboard.py")