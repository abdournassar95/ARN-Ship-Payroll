# main.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import qInstallMessageHandler, QtMsgType
from database import init_db
from ui_login import LoginWindow
import config

def qt_message_handler(mode, context, message):
    if "setPointSize" in message:
        return
    # طباعة الرسائل الأخرى فقط إذا وُجدت
    if mode == QtMsgType.QtFatalMsg:
        print(f"Fatal: {message}")

if __name__ == "__main__":
    # تصفية تحذيرات الخطوط الافتراضية من Qt
    qInstallMessageHandler(qt_message_handler)

    # تهيئة قاعدة البيانات والتأكد من وجود الجداول الأساسية
    init_db()
    
    # تشغيل محرك PyQt6
    app = QApplication(sys.argv)
    
    # تحديد الخط الافتراضي مع حجم محدد لمنع تحذير QFont::setPointSize
    app.setFont(QFont("Cairo", 11))
    
    # تطبيق التصميم الموحد على مستوى البرنامج بالكامل
    app.setStyleSheet(config.STYLESHEET)
    
    # فتح شاشة تسجيل الدخول
    login_window = LoginWindow()
    login_window.show()
    
    sys.exit(app.exec())