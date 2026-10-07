# config.py
"""
إعدادات التصميم والهوية البصرية لنظام رواتب الأسطول (ARN Ship Payroll)
تصميم احترافي رسمي هادئ، مريح للعين، ومتزن هندسياً، خالي من التدرجات الفاقعة والنمطية المصطنعة.
ARN Technology (c) 2026 - تطوير وبرمجة: عبده رجب نصار
"""

# ============================================================
# الصلاحيات المعروفة في النظام (مصدر واحد — تُستخدم في شاشة المستخدمين والتحقق)
# ============================================================
KNOWN_ROLES = ["Admin", "Captain", "Accountant", "Officer"]

# ============================================================
# ثوابت الألوان الرسمية المريحة للعين (Corporate Maritime Dark)
# ============================================================
COLOR_BG = "#0f172a"           # خلفية كحلية مسودة هادئة ومريحة
COLOR_SURFACE = "#1e293b"      # أسطح الكروت واللوحات والجداول
COLOR_SURFACE_HOVER = "#273549"# أسطح التمرير
COLOR_BORDER = "#334155"       # حدود هادئة ورصينة
COLOR_BORDER_FOCUS = "#3b82f6" # إطار التركيز

# درجات النصوص المتدرجة بانسجام
COLOR_TEXT_MAIN = "#e2e8f0"    # نص رئيسي أبيض حليبي مريح للقراءة
COLOR_TEXT_TITLE = "#f8fafc"   # عناوين بارزة وواضحة
COLOR_TEXT_MUTED = "#94a3b8"   # نصوص ثانوية وبيانات توضيحية
COLOR_TEXT_FAINT = "#64748b"   # أرقام المسلسل والعناصر الباهتة

# ألوان ولهجات دلالية مهنية متزنة (Muted Corporate Accents)
COLOR_PRIMARY = "#2563eb"      # أزرق رسمي متزن
COLOR_PRIMARY_HOVER = "#1d4ed8"
COLOR_PRIMARY_PRESSED = "#1e40af"

COLOR_SUCCESS = "#059669"      # أخضر زمردي مهني هادئ
COLOR_SUCCESS_HOVER = "#047857"
COLOR_SUCCESS_PRESSED = "#065f46"

COLOR_DANGER = "#dc2626"       # أحمر قرميدي رصين
COLOR_DANGER_HOVER = "#b91c1c"
COLOR_DANGER_PRESSED = "#991b1b"

COLOR_WARNING = "#d97706"      # كهرماني دافئ
COLOR_WARNING_HOVER = "#b45309"
COLOR_WARNING_PRESSED = "#92400e"

COLOR_INFO = "#38bdf8"
COLOR_INFO_MUTED = "#93c5fd"

STYLESHEET = f"""
/* الإعدادات العامة للخطوط والخلفيات */
QWidget {{
    font-family: 'Cairo';
    font-size: 11pt;
    color: {COLOR_TEXT_MAIN};
}}
QMainWindow, QDialog, QScrollArea {{
    background-color: {COLOR_BG};
}}

/* الكروت والحاويات */
QFrame#Card {{
    background-color: {COLOR_SURFACE};
    border-radius: 12px;
    border: 1px solid {COLOR_BORDER};
}}

/* حقول الإدخال والقوائم والتقويم */
QLineEdit, QComboBox, QDateEdit {{
    padding: 8px 14px;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_TITLE};
    font-weight: bold;
    selection-background-color: {COLOR_PRIMARY};
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
    border: 1.5px solid {COLOR_BORDER_FOCUS};
    background-color: {COLOR_SURFACE};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    background-color: {COLOR_SURFACE};
    selection-background-color: {COLOR_PRIMARY};
    selection-color: #ffffff;
    color: {COLOR_TEXT_TITLE};
}}

/* الأزرار العصرية واللمسية (Tactile Buttons) */
QPushButton {{
    font-family: 'Cairo';
    font-weight: 700;
    border-radius: 8px;
    padding: 8px 16px;
    color: #ffffff;
    border: none;
}}
QPushButton:hover {{
    background-color: {COLOR_SURFACE_HOVER};
}}
QPushButton:pressed {{
    background-color: #172333;
}}

QPushButton#Primary {{
    background-color: {COLOR_PRIMARY};
}}
QPushButton#Primary:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}
QPushButton#Primary:pressed {{
    background-color: {COLOR_PRIMARY_PRESSED};
}}

QPushButton#Success {{
    background-color: {COLOR_SUCCESS};
}}
QPushButton#Success:hover {{
    background-color: {COLOR_SUCCESS_HOVER};
}}
QPushButton#Success:pressed {{
    background-color: {COLOR_SUCCESS_PRESSED};
}}

QPushButton#Danger {{
    background-color: {COLOR_DANGER};
}}
QPushButton#Danger:hover {{
    background-color: {COLOR_DANGER_HOVER};
}}
QPushButton#Danger:pressed {{
    background-color: {COLOR_DANGER_PRESSED};
}}

QPushButton#Warning {{
    background-color: {COLOR_WARNING};
    color: #ffffff;
}}
QPushButton#Warning:hover {{
    background-color: {COLOR_WARNING_HOVER};
}}
QPushButton#Warning:pressed {{
    background-color: {COLOR_WARNING_PRESSED};
}}

QPushButton#Outline {{
    background-color: transparent;
    border: 1px solid {COLOR_BORDER};
    color: {COLOR_TEXT_MUTED};
}}
QPushButton#Outline:hover {{
    border-color: #475569;
    background-color: {COLOR_SURFACE};
    color: {COLOR_TEXT_MAIN};
}}
QPushButton#Outline:pressed {{
    background-color: {COLOR_BG};
    border-color: {COLOR_BORDER};
}}

/* الجداول الاحترافية */
QTableWidget {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    gridline-color: transparent;
    outline: none;
    color: {COLOR_TEXT_MAIN};
}}
QTableWidget::item {{
    border-bottom: 1px solid #283548;
    padding: 6px 8px;
}}
QTableWidget::item:selected {{
    background-color: {COLOR_SURFACE_HOVER};
    color: #ffffff;
}}
QHeaderView::section {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_MUTED};
    font-weight: 800;
    font-size: 12px;
    padding: 12px 10px;
    border: none;
    border-bottom: 2px solid {COLOR_BORDER};
}}

/* شريط التمرير (Scrollbar) */
QScrollBar:vertical {{
    border: none;
    background: {COLOR_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #334155;
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #475569;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}
"""
