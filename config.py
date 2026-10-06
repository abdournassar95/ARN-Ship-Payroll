# config.py
"""
إعدادات التصميم والهوية البصرية لنظام رواتب الأسطول (ARN Ship Payroll)
تصميم احترافي رسمي هادئ، مريح للعين، ومتزن هندسياً، خالي من التدرجات الفاقعة والنمطية المصطنعة.
ARN Technology (c) 2026 - تطوير وبرمجة: عبده رجب نصار
"""

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

# Spacing scale shared by the window layouts (logical pixels).
SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL = 4, 8, 12, 18, 24

# Keep selectors narrow: QLabel inherits QFrame in Qt. A generic "QFrame"
# rule draws borders on labels and creates the nested boxes seen in the UI.
STYLESHEET = f"""
QWidget {{ font-family: 'Cairo', 'Segoe UI', sans-serif; font-size: 10pt; color: {COLOR_TEXT_MAIN}; }}
QMainWindow, QDialog {{ background-color: {COLOR_BG}; }}
QFrame#Card, QFrame#StatCard, QFrame#FilterCard, QFrame#FleetFilterCard {{
    background-color: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: 10px;
}}
QFrame#FleetKpiTotal, QFrame#FleetKpiValid, QFrame#FleetKpiSoon, QFrame#FleetKpiExpired {{
    background-color: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: 10px;
}}
QFrame#FleetKpiTotal {{ border-top: 3px solid {COLOR_INFO}; }}
QFrame#FleetKpiValid {{ border-top: 3px solid {COLOR_SUCCESS}; }}
QFrame#FleetKpiSoon {{ border-top: 3px solid {COLOR_WARNING}; }}
QFrame#FleetKpiExpired {{ border-top: 3px solid {COLOR_DANGER}; }}
QScrollArea {{ border: none; background: transparent; }}
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
    background-color: {COLOR_BG}; color: {COLOR_TEXT_TITLE};
    border: 1px solid {COLOR_BORDER}; border-radius: 7px;
    padding: 7px 10px; selection-background-color: {COLOR_PRIMARY}; selection-color: white;
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border: 2px solid {COLOR_INFO}; }}
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {COLOR_SURFACE}; color: {COLOR_TEXT_MUTED};
}}
QComboBox::drop-down {{ border: none; width: 25px; }}
QComboBox QAbstractItemView {{ background-color: {COLOR_SURFACE}; color: {COLOR_TEXT_TITLE};
    selection-background-color: {COLOR_PRIMARY}; selection-color: white; border: 1px solid {COLOR_BORDER}; }}
QCalendarWidget QAbstractItemView {{ background-color: {COLOR_BG}; color: {COLOR_TEXT_MAIN}; selection-background-color: {COLOR_PRIMARY}; }}
QPushButton {{ background-color: {COLOR_SURFACE_HOVER}; color: {COLOR_TEXT_TITLE};
    border: 1px solid {COLOR_BORDER}; border-radius: 7px; padding: 7px 12px; font-weight: 700; }}
QPushButton:hover {{ background-color: #34455e; border-color: {COLOR_INFO}; }}
QPushButton:focus {{ border: 2px solid {COLOR_INFO}; }}
QPushButton:disabled {{ background-color: {COLOR_BORDER}; color: {COLOR_TEXT_MUTED}; border-color: {COLOR_BORDER}; }}
QPushButton#Primary {{ background-color: {COLOR_PRIMARY}; border-color: {COLOR_PRIMARY}; color: white; }}
QPushButton#Primary:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}
QPushButton#Success {{ background-color: {COLOR_SUCCESS}; border-color: {COLOR_SUCCESS}; color: white; }}
QPushButton#Success:hover {{ background-color: {COLOR_SUCCESS_HOVER}; }}
QPushButton#Danger {{ background-color: {COLOR_DANGER}; border-color: {COLOR_DANGER}; color: white; }}
QPushButton#Danger:hover {{ background-color: {COLOR_DANGER_HOVER}; }}
QPushButton#Warning {{ background-color: {COLOR_WARNING}; border-color: {COLOR_WARNING}; color: white; }}
QPushButton#Warning:hover {{ background-color: {COLOR_WARNING_HOVER}; }}
QPushButton#Outline, QPushButton#FilterChip {{ background-color: transparent; color: {COLOR_TEXT_MAIN}; border: 1px solid {COLOR_BORDER}; }}
QPushButton#Outline:hover, QPushButton#FilterChip:hover {{ background-color: {COLOR_SURFACE_HOVER}; border-color: {COLOR_INFO}; }}
QPushButton#FilterChip:checked {{ background-color: {COLOR_PRIMARY}; border-color: {COLOR_PRIMARY}; color: white; }}
QCheckBox {{ spacing: 8px; color: {COLOR_TEXT_MAIN}; }}
QCheckBox::indicator {{ width: 17px; height: 17px; border: 1px solid {COLOR_TEXT_MUTED}; border-radius: 4px; }}
QCheckBox::indicator:checked {{ background-color: {COLOR_PRIMARY}; border-color: {COLOR_PRIMARY}; }}
QTableWidget {{ background-color: {COLOR_SURFACE}; alternate-background-color: #19263a;
    border: 1px solid {COLOR_BORDER}; border-radius: 8px; gridline-color: transparent; }}
QTableWidget::item {{ padding: 5px 8px; border: none; }}
QTableWidget::item:selected {{ background-color: #284b72; color: white; }}
QHeaderView::section {{ background-color: {COLOR_BG}; color: {COLOR_TEXT_MUTED}; font-size: 10pt;
    font-weight: 700; padding: 9px 7px; border: none; border-bottom: 1px solid {COLOR_BORDER}; }}
QScrollBar:vertical {{ background: {COLOR_BG}; width: 9px; border: none; }}
QScrollBar:horizontal {{ background: {COLOR_BG}; height: 9px; border: none; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: #475569; border-radius: 4px; min-height: 22px; min-width: 22px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ border: none; background: none; }}
QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; background: {COLOR_SURFACE}; }}
QTabBar::tab {{ background: {COLOR_BG}; color: {COLOR_TEXT_MUTED}; padding: 8px 14px; }}
QTabBar::tab:selected {{ background: {COLOR_SURFACE}; color: {COLOR_TEXT_TITLE}; border-bottom: 2px solid {COLOR_INFO}; }}
QProgressBar {{ background-color: {COLOR_BORDER}; border: none; border-radius: 3px; }}
QProgressBar::chunk {{ background-color: {COLOR_INFO}; border-radius: 3px; }}
QToolTip {{ background-color: {COLOR_SURFACE}; color: {COLOR_TEXT_TITLE}; border: 1px solid {COLOR_BORDER}; padding: 6px; }}
"""

LOGIN_STYLESHEET = STYLESHEET + f"""
QWidget#LoginWindow {{ background-color: {COLOR_BG}; }}
QFrame#LoginCard {{ background-color: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: 16px; }}
QLabel#LoginBrand {{ color: {COLOR_INFO_MUTED}; font-size: 13pt; font-weight: 700; }}
QLabel#LoginTitle {{ color: {COLOR_TEXT_TITLE}; font-size: 20pt; font-weight: 700; }}
QLabel#LoginSubtitle, QLabel#LoginFooter {{ color: {COLOR_TEXT_MUTED}; font-size: 9pt; }}
QLabel#LoginFieldLabel {{ color: {COLOR_TEXT_MAIN}; font-size: 10pt; font-weight: 700; }}
QLabel#LoginMark {{ color: {COLOR_INFO}; font-size: 30pt; }}
QPushButton#PrimaryButton {{ background-color: {COLOR_PRIMARY}; color: white; border: none; border-radius: 8px; font-weight: 700; }}
QPushButton#PrimaryButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}
QPushButton#PrimaryButton:disabled {{ background-color: {COLOR_BORDER}; color: {COLOR_TEXT_MUTED}; }}
QToolButton {{ background: transparent; color: {COLOR_TEXT_MAIN}; border: none; padding: 7px; }}
QToolButton:hover {{ background-color: {COLOR_SURFACE_HOVER}; }}
"""
