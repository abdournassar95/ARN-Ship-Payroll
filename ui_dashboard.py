# ui_dashboard.py
import sys
import sqlite3
import json
import calendar
from datetime import datetime
from dateutil.relativedelta import relativedelta
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QGraphicsDropShadowEffect, QAbstractItemView,
    QProgressDialog, QApplication, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QCursor, QIcon, QKeySequence, QShortcut

# استيراد الأدوات المساعدة
from utils import calculate_days_30, get_base_rank, get_rank_sort_key

# استيراد إعدادات التصميم والهوية الموحدة
import config

# استيراد النوافذ الأخرى
from ui_accounting import AccountingWindow
from ui_add_crew import AddCrewWindow
from ui_admin import AdminWindow

from report_service import ReportService
import os

# ============================================================
# 1. محرك الحسابات (منطق الأعمال)
# ============================================================
class PayrollEngine:
    """يتولى جميع عمليات الحساب وجلب البيانات من قاعدة البيانات"""

    def __init__(self, db_path='arn_ship_payroll.db'):
        self.db_path = db_path

    def get_system_info(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                data = conn.execute(
                    "SELECT company_name, vessel_name FROM system_settings WHERE id=1"
                ).fetchone()
            if data and len(data) == 2:
                return f"{data[1]} - {data[0]}"
            return "ARN Fleet - النظام المحاسبي"
        except sqlite3.Error:
            return "ARN Fleet - النظام المحاسبي"

    def load_crew_data(self, year, month, calc_mode):
        crew_data = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                crew_members = cursor.execute(
                    "SELECT * FROM CrewWages"
                ).fetchall()

                # 1. ترتيب البحارة بحسب الهيكل الوظيفي للرتب
                def rank_sort_key(m):
                    r_str = dict(m).get('Rank', '')
                    no_val = dict(m).get('No', 0)
                    return (get_rank_sort_key(r_str), no_val)

                crew_members = sorted(crew_members, key=rank_sort_key)

                # 2. إحصاء تكرار كل رتبة لترقيمها تلقائياً (مثال: MASTER 1, MASTER 2)
                from collections import Counter
                base_rank_counts = Counter(get_base_rank(dict(m).get('Rank', '')) for m in crew_members)
                base_rank_current_index = {}

                all_history = cursor.execute(
                    "SELECT * FROM payroll_history"
                ).fetchall()

                history_by_crew = {}
                for h in all_history:
                    cid = h['crew_id']
                    history_by_crew.setdefault(cid, []).append(dict(h))

                today = datetime.now()
                today_str = today.strftime("%Y-%m-%d")
                real_year, real_month = today.year, today.month

                selected_month_start = f"{year}-{month:02d}-01"
                last_day = calendar.monthrange(year, month)[1]
                selected_month_end = f"{year}-{month:02d}-{last_day:02d}"
                dt_selected_start = datetime.strptime(selected_month_start, "%Y-%m-%d")
                prev_month_end = (dt_selected_start - relativedelta(days=1)).strftime("%Y-%m-%d")

                if calc_mode == "today" and month == real_month and year == real_year:
                    cap_date = today_str
                else:
                    cap_date = selected_month_end

                for member in crew_members:
                    mem = dict(member)
                    crew_id = mem['No']
                    name = mem['Name']
                    raw_rank = mem['Rank'] or ''
                    base_rank = get_base_rank(raw_rank)

                    total_with_rank = base_rank_counts[base_rank]
                    if total_with_rank > 1:
                        base_rank_current_index[base_rank] = base_rank_current_index.get(base_rank, 0) + 1
                        rank_display = f"{base_rank} {base_rank_current_index[base_rank]}"
                    else:
                        rank_display = base_rank if base_rank != 'OTHER' else (raw_rank or 'OTHER')

                    period_from = mem['PeriodFrom'] or selected_month_start
                    wage = float(mem['MonthlyWage'] or 0)
                    prev_balance = float(mem['PREVIOUS'] or 0)
                    paid_data = json.loads(mem.get('PaidMonthsData') or '{}')
                    wage_history = json.loads(mem.get('WageHistory') or '{}')

                    if period_from > selected_month_end:
                        days_worked = 0
                    else:
                        days_worked = calculate_days_30(period_from, cap_date)

                    paid_days_past = 0
                    paid_days_current = 0
                    if days_worked > 0:
                        for m_key in paid_data.keys():
                            try:
                                y_num, m_num = map(int, m_key.split('-'))
                                m_start = f"{y_num}-{m_num:02d}-01"
                                m_last = calendar.monthrange(y_num, m_num)[1]
                                m_end = f"{y_num}-{m_num:02d}-{m_last:02d}"
                                actual_start = max(period_from, m_start)
                                actual_end = min(cap_date, m_end)
                                if actual_start <= actual_end:
                                    days = calculate_days_30(actual_start, actual_end)
                                    if y_num < year or (y_num == year and m_num < month):
                                        paid_days_past += days
                                    elif y_num == year and m_num == month:
                                        paid_days_current += days
                            except:
                                continue

                    days_worked_past = calculate_days_30(period_from, prev_month_end) if period_from <= prev_month_end else 0
                    net_days_past = max(0, days_worked_past - paid_days_past)
                    days_worked_current = max(0, days_worked - days_worked_past)
                    net_days_current = max(0, days_worked_current - paid_days_current)
                    net_days_total = net_days_past + net_days_current

                    past_unpaid_basic = 0
                    if period_from <= prev_month_end:
                        curr = datetime.strptime(period_from, "%Y-%m-%d").replace(day=1)
                        end = datetime.strptime(prev_month_end, "%Y-%m-%d").replace(day=1)
                        while curr <= end:
                            m_key = curr.strftime("%Y-%m")
                            m_start = curr.strftime("%Y-%m-01")
                            m_last = calendar.monthrange(curr.year, curr.month)[1]
                            m_end = curr.strftime(f"%Y-%m-{m_last:02d}")
                            actual_start = max(period_from, m_start)
                            actual_end = min(prev_month_end, m_end)
                            if actual_start <= actual_end:
                                days_in_month = calculate_days_30(actual_start, actual_end)
                                if m_key not in paid_data:
                                    w = float(wage_history.get(m_key, wage))
                                    past_unpaid_basic += round(days_in_month * (w / 30.0), 2)
                            curr += relativedelta(months=1)

                    wage_key = f"{year}-{month:02d}"
                    current_wage = float(wage_history.get(wage_key, wage))
                    current_basic = round(current_wage / 30.0 * net_days_current, 2) if net_days_current > 0 else 0.0

                    past_extra = past_ded = curr_extra = curr_ded = 0.0
                    cum_cash = cum_cig = cum_trans = 0.0

                    for h in history_by_crew.get(crew_id, []):
                        h_year, h_month = h['payroll_year'], h['payroll_month']
                        m_key_hist = f"{h_year}-{h_month:02d}"
                        if m_key_hist not in paid_data:
                            if h_year == year and h_month == month:
                                curr_extra += float(h['extra'])
                                curr_ded += float(h['deduction'])
                                cum_cash += float(h['payment_cash'])
                                cum_cig += float(h['cigarette'])
                                cum_trans += float(h['transfer'])
                            elif h_year < year or (h_year == year and h_month < month):
                                past_extra += float(h['extra'])
                                past_ded += float(h['deduction'])
                                cum_cash += float(h['payment_cash'])
                                cum_cig += float(h['cigarette'])
                                cum_trans += float(h['transfer'])

                    total_due = round(current_basic + curr_extra + prev_balance + past_unpaid_basic + past_extra - curr_ded - past_ded, 2)
                    total_received = round(cum_cash + cum_cig + cum_trans, 2)
                    final_balance = round(total_due - total_received, 2)


                    is_settled = wage_key in paid_data
                    days_display = "مسوى ✓" if is_settled else f"{net_days_total}"

                    crew_data.append({
                        'id': crew_id,
                        'index': len(crew_data) + 1,
                        'name': name,
                        'rank': rank_display,
                        'days_display': days_display,
                        'wage': current_wage,
                        'curr_extra': curr_extra,
                        'curr_ded': curr_ded,
                        'prev_balance': prev_balance,
                        'total_due': total_due,
                        'cum_cash': cum_cash,
                        'cum_cig': cum_cig,
                        'cum_trans': cum_trans,
                        'total_received': total_received,
                        'final_balance': final_balance,
                        'is_settled': is_settled,
                        'net_days': net_days_total
                    })

            return crew_data

        except sqlite3.Error as e:
            raise Exception(f"خطأ في قاعدة البيانات: {str(e)}")


# ============================================================
# 2. خيط تحميل البيانات
# ============================================================
class LoadDataThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, engine, year, month, calc_mode):
        super().__init__()
        self.engine = engine
        self.year = year
        self.month = month
        self.calc_mode = calc_mode

    def run(self):
        try:
            data = self.engine.load_crew_data(self.year, self.month, self.calc_mode)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


# ============================================================
# 3. نافذة الداشبورد الرئيسية
# ============================================================
class MainDashboard(QMainWindow):
    def __init__(self, user_id=1, full_name="عبده رجب نصار", role="Admin"):
        super().__init__()
        self.current_user = {"id": user_id, "name": full_name, "role": role}
        self.current_month = datetime.now().month
        self.current_year = datetime.now().year
        self.calc_mode = "today"

        self.engine = PayrollEngine()
        self.system_info = self.engine.get_system_info()

        self.setWindowTitle(f"ARN Fleet | {self.system_info}")
        self.setMinimumSize(1350, 850)

        self.apply_stylesheet()
        self.build_ui()

        self.load_data_thread = None
        self.progress_dialog = None
        self.update_month_options()
        self.refresh_data()

        # تسجيل مستمع شارة التنبيهات وتشغيل الفحص الشامل في الخلفية
        try:
            from notification_service import NotificationService
            NotificationService.register_badge_listener(self.on_badge_update)
            self.run_startup_alerts_check()
        except Exception:
            pass

        # اختصارات لوحة المفاتيح
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)
        QShortcut(QKeySequence("Ctrl+P"), self, self.print_master_payroll_sheet)
        QShortcut(QKeySequence("Ctrl+N"), self, self.open_add_crew)
        QShortcut(QKeySequence("F5"), self, self.refresh_data)

    # ---------- التصميم الداكن الفخم والمتزن ----------
    def apply_stylesheet(self):
        self.setStyleSheet(config.STYLESHEET)

    def create_kpi_card(self, title, color_hex):
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(f"""
            QFrame#Card {{
                border: 1px solid {config.COLOR_BORDER};
                background-color: {config.COLOR_SURFACE};
                border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {config.COLOR_TEXT_MUTED}; background: transparent;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_val = QLabel("0")
        lbl_val.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {color_hex}; background: transparent;")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return card, lbl_val

    def build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ---------- الهيدر ----------
        header_layout = QHBoxLayout()
        user_info = QLabel(f"👤  مرحباً بك، كابتن {self.current_user['name']}")
        user_info.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        user_info.setStyleSheet(f"color: {config.COLOR_INFO_MUTED};")
        header_layout.addWidget(user_info)

        header_layout.addStretch()

        # زر مركز التنبيهات الذكية مع الشارة
        self.btn_alerts = QPushButton("🔔 التنبيهات")
        self.btn_alerts.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_alerts.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.COLOR_SURFACE};
                color: {config.COLOR_TEXT_MAIN};
                font-size: 13px;
                font-weight: bold;
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 8px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{ border-color: {config.COLOR_PRIMARY}; color: #ffffff; background-color: {config.COLOR_SURFACE_HOVER}; }}
            QPushButton:pressed {{ background-color: {config.COLOR_BG}; }}
        """)
        self.btn_alerts.clicked.connect(self.open_alerts_center)
        header_layout.addWidget(self.btn_alerts)

        # زر سجل التدقيق
        self.btn_audit = QPushButton("📋 سجل التدقيق")
        self.btn_audit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_audit.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.COLOR_SURFACE};
                color: {config.COLOR_TEXT_MUTED};
                font-size: 13px;
                font-weight: bold;
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 8px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{ border-color: {config.COLOR_SUCCESS}; color: #ffffff; background-color: {config.COLOR_SURFACE_HOVER}; }}
            QPushButton:pressed {{ background-color: {config.COLOR_BG}; }}
        """)
        self.btn_audit.clicked.connect(self.open_audit_log)
        header_layout.addWidget(self.btn_audit)

        btn_about = QPushButton("ℹ️ حول البرنامج")
        btn_about.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_about.setStyleSheet(f"background: transparent; color: {config.COLOR_TEXT_MUTED}; font-size: 13px; font-weight: bold; border: none; padding: 0 12px;")
        btn_about.clicked.connect(self.show_about_dialog)
        header_layout.addWidget(btn_about)

        title_info = QLabel(f"🚢  {self.system_info}")
        title_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        title_info.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        title_info.setStyleSheet(f"color: {config.COLOR_TEXT_TITLE};")
        header_layout.addWidget(title_info)
        main_layout.addLayout(header_layout)

        # ---------- كروت المؤشرات المباشرة (KPI Summary Cards) ----------
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        # ألوان هادئة ومتناسقة بدون فقع لوني
        card_net, self.val_kpi_net = self.create_kpi_card("صافي الرواتب المستحقة 💰", "#34d399")
        card_adv, self.val_kpi_advances = self.create_kpi_card("إجمالي المسحوبات والسلف 🔻", "#f87171")
        card_due, self.val_kpi_due = self.create_kpi_card("إجمالي المستحقات 📈", "#93c5fd")
        card_crew, self.val_kpi_crew = self.create_kpi_card("طاقم السفينة 👥", "#cbd5e1")

        kpi_layout.addWidget(card_net)
        kpi_layout.addWidget(card_adv)
        kpi_layout.addWidget(card_due)
        kpi_layout.addWidget(card_crew)
        main_layout.addLayout(kpi_layout)

        # ---------- لوحة التحكم (كارد) ----------
        control_panel = QFrame()
        control_panel.setObjectName("Card")
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(15, 10, 15, 10)
        control_layout.setSpacing(10)

        role = self.current_user["role"].lower()

        if role in ["admin", "captain"]:
            btn_cash = QPushButton("💰  القبطان")
            btn_cash.setObjectName("Primary")
            btn_cash.setMinimumHeight(38)
            btn_cash.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_cash.clicked.connect(self.open_master_cash)
            control_layout.addWidget(btn_cash)

            btn_analytics = QPushButton("📊  التحليلات البيانية")
            btn_analytics.setObjectName("Outline")
            btn_analytics.setMinimumHeight(38)
            btn_analytics.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_analytics.clicked.connect(self.open_analytics)
            control_layout.addWidget(btn_analytics)

        if role in ["admin", "captain", "accountant"]:
            btn_crew_docs = QPushButton("📜  وثائق وشهادات الطاقم")
            btn_crew_docs.setObjectName("Outline")
            btn_crew_docs.setMinimumHeight(38)
            btn_crew_docs.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_crew_docs.setToolTip("فتح منظومة متابعة الشهادات والوثائق الملاحية للطاقم وتواريخ انتهائها")
            btn_crew_docs.clicked.connect(self.open_all_crew_documents)
            control_layout.addWidget(btn_crew_docs)

        if role in ["admin", "captain"]:
            btn_admin = QPushButton("⚙️  إدارة النظام")
            btn_admin.setObjectName("Outline")
            btn_admin.setMinimumHeight(38)
            btn_admin.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_admin.clicked.connect(self.open_admin)
            control_layout.addWidget(btn_admin)

        if role in ["admin", "accountant"]:
            btn_add_crew = QPushButton("➕  إضافة بحار")
            btn_add_crew.setObjectName("Success")
            btn_add_crew.setMinimumHeight(38)
            btn_add_crew.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_add_crew.clicked.connect(self.open_add_crew)
            control_layout.addWidget(btn_add_crew)

        if role in ["admin", "captain"]:
            btn_reset = QPushButton("🧹  تهيئة النظام")
            btn_reset.setObjectName("Danger")
            btn_reset.setMinimumHeight(38)
            btn_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_reset.setToolTip("تصفير كافة البيانات وتهيئة النظام لاستخدام جديد")
            btn_reset.clicked.connect(self.reset_all_data)
            control_layout.addWidget(btn_reset)

        control_layout.addStretch()

        # عناصر اختيار السنة والشهر
        lbl_year = QLabel("السنة:")
        lbl_year.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        self.year_entry = QLineEdit(str(self.current_year))
        self.year_entry.setFixedWidth(70)
        self.year_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.year_entry.editingFinished.connect(self.on_year_changed)

        lbl_month = QLabel("الشهر:")
        lbl_month.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        self.month_combo = QComboBox()
        self.month_combo.setMinimumWidth(160)
        self.month_combo.currentIndexChanged.connect(self.on_month_changed)

        btn_calc_mode = QPushButton("🔄  اليوم")
        btn_calc_mode.setObjectName("Outline")
        btn_calc_mode.setMinimumHeight(38)
        btn_calc_mode.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_calc_mode.clicked.connect(self.toggle_calc_mode)

        btn_print_all = QPushButton("🖨️  طباعة الكل")
        btn_print_all.setObjectName("Primary")
        btn_print_all.setMinimumHeight(38)
        btn_print_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_print_all.clicked.connect(self.print_all_crew_payslips)

        control_layout.addWidget(lbl_year)
        control_layout.addWidget(self.year_entry)
        control_layout.addWidget(lbl_month)
        control_layout.addWidget(self.month_combo)
        control_layout.addWidget(btn_calc_mode)
        control_layout.addWidget(btn_print_all)

        main_layout.addWidget(control_panel)

        # ---------- جدول البيانات المخصص ----------
        table_card = QFrame()
        table_card.setObjectName("Card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)
        table_layout.setSpacing(10)

        # شريط البحث والتصفية السريعة والتقارير المجمعة
        search_bar = QHBoxLayout()
        search_bar.setSpacing(10)

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("🔍  ابحث بالاسم أو الرتبة... (Ctrl+F)")
        self.search_entry.setClearButtonEnabled(True)
        self.search_entry.setMinimumWidth(260)
        self.search_entry.textChanged.connect(self.apply_filter)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "كل الطاقم (الجميع)",
            "تسوية منتهية (مسدد) 🔒",
            "قيد العمل (غير مسدد) 🔓",
            "سلف نشطة 🔻"
        ])
        self.filter_combo.setMinimumWidth(170)
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)

        btn_master_sheet = QPushButton("📋  كشف المسير المجمع (PDF)")
        btn_master_sheet.setObjectName("Primary")
        btn_master_sheet.setMinimumHeight(36)
        btn_master_sheet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_master_sheet.setToolTip("توليد كشف المسير الشهري المجمع لكافة الطاقم بصيغة Landscape A4 (Ctrl+P)")
        btn_master_sheet.clicked.connect(self.print_master_payroll_sheet)

        btn_excel = QPushButton("📊  تصدير Excel (.xlsx)")
        btn_excel.setObjectName("Success")
        btn_excel.setMinimumHeight(36)
        btn_excel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_excel.clicked.connect(self.export_payroll_excel)

        search_bar.addWidget(self.search_entry)
        search_bar.addWidget(self.filter_combo)
        search_bar.addStretch()
        search_bar.addWidget(btn_master_sheet)
        search_bar.addWidget(btn_excel)

        table_layout.addLayout(search_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(15)
        self.table.setHorizontalHeaderLabels([
            "م", "الاسم الكامل للبحار", "الرتبة", "الأيام", "الراتب", "إضافي", "خصم",
            "سابق", "المستحق", "سلفة", "سجائر", "تحويل", "المستلم", "الصافي", "الإجراءات"
        ])
        
        # إخفاء الترقيم الخارجي العمودي الافتراضي للجدول
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # تمديد خلية الاسم لتأخذ أقصى مساحة متاحة
        header.setSectionResizeMode(14, QHeaderView.ResizeMode.Fixed)   # تثبيت عرض عمود الإجراءات

        # تحديد أبعاد الخانات بدقة لراحة العين وقراءة الأسماء كاملة
        self.table.setColumnWidth(0, 40)   # م
        self.table.setColumnWidth(1, 220)  # الاسم الكامل (ممدود)
        self.table.setColumnWidth(2, 100)  # الرتبة
        self.table.setColumnWidth(3, 55)   # الأيام
        self.table.setColumnWidth(4, 85)   # الراتب
        self.table.setColumnWidth(5, 75)   # إضافي
        self.table.setColumnWidth(6, 75)   # خصم
        self.table.setColumnWidth(7, 80)   # سابق
        self.table.setColumnWidth(8, 95)   # المستحق
        self.table.setColumnWidth(9, 80)   # سلفة
        self.table.setColumnWidth(10, 70)  # سجائر
        self.table.setColumnWidth(11, 80)  # تحويل
        self.table.setColumnWidth(12, 90)  # المستلم
        self.table.setColumnWidth(13, 95)  # الصافي
        self.table.setColumnWidth(14, 290) # الإجراءات (يتسع لـ 4 أزرار مريحة)

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        table_layout.addWidget(self.table)
        main_layout.addWidget(table_card)

    def toggle_calc_mode(self):
        if self.calc_mode == "today":
            self.calc_mode = "full_month"
            self.sender().setText("📅  شهر كامل")
        else:
            self.calc_mode = "today"
            self.sender().setText("🔄  اليوم")
        self.refresh_data()

    def update_month_options(self):
        self.month_combo.blockSignals(True)
        self.month_combo.clear()
        months_arabic = [
            "1 - يناير", "2 - فبراير", "3 - مارس", "4 - أبريل", "5 - مايو", "6 - يونيو",
            "7 - يوليو", "8 - أغسطس", "9 - سبتمبر", "10 - أكتوبر", "11 - نوفمبر", "12 - ديسمبر"
        ]
        now = datetime.now()
        max_month = now.month if self.current_year == now.year else 12

        for i in range(1, max_month + 1):
            self.month_combo.addItem(months_arabic[i - 1])

        if self.current_month <= max_month:
            self.month_combo.setCurrentIndex(self.current_month - 1)
        else:
            self.month_combo.setCurrentIndex(max_month - 1)
            self.current_month = max_month

        self.month_combo.blockSignals(False)

    def on_year_changed(self):
        self.refresh_data()

    def on_month_changed(self, index):
        if index != -1:
            self.current_month = int(self.month_combo.currentText().split(" - ")[0])
            self.refresh_data()

    # ---------- تحميل البيانات (مع خيط منفصل) ----------
    def load_data(self):
        self.refresh_data()

    def refresh_data(self):
        try:
            self.current_year = int(self.year_entry.text())
            self.update_month_options()
        except:
            return

        self.progress_dialog = QProgressDialog("جاري تحميل البيانات...", "إلغاء", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()

        self.load_data_thread = LoadDataThread(
            self.engine,
            self.current_year,
            self.current_month,
            self.calc_mode
        )
        self.load_data_thread.finished.connect(self.on_data_loaded)
        self.load_data_thread.error.connect(self.on_load_error)
        self.load_data_thread.start()

    def on_data_loaded(self, crew_data):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.latest_crew_data = crew_data
        self.populate_table(crew_data)

    def on_load_error(self, error_msg):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        QMessageBox.critical(self, "خطأ في التحميل", error_msg)

    # ---------- ملء الجدول ----------
    def populate_table(self, crew_data):
        self.table.setRowCount(0)

        # تحديث كروت المؤشرات المباشرة
        total_crew = len(crew_data)
        total_due = sum(d.get('total_due', 0) for d in crew_data)
        total_advances = sum(d.get('total_received', 0) for d in crew_data)
        total_net = sum(d.get('final_balance', 0) for d in crew_data)

        if hasattr(self, 'val_kpi_crew'):
            self.val_kpi_crew.setText(f"{total_crew} بحار")
            self.val_kpi_due.setText(f"${total_due:,.0f}")
            self.val_kpi_advances.setText(f"${total_advances:,.0f}")
            self.val_kpi_net.setText(f"${total_net:,.0f}")

        for row_idx, data in enumerate(crew_data):
            self.table.insertRow(row_idx)

            text_color = "#cbd5e1"
            success_color = "#34d399"
            danger_color = "#f87171"
            primary_color = "#93c5fd"
            faint_color = "#64748b"

            # العمود 0: المسلسل
            self.table.setItem(row_idx, 0, self._create_item(f"{data['index']:02d}", faint_color, is_number=True))

            # العمود 1: الاسم (محاذاة لليسار ومظهورة بالكامل)
            name_item = self._create_item(data['name'], "#f8fafc", bold=True, font_size=12)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, name_item)

            # العمود 2: الرتبة
            self.table.setItem(row_idx, 2, self._create_item(data['rank'], text_color, font_size=11))

            # العمود 3: الأيام
            days_color = success_color if data['is_settled'] else text_color
            self.table.setItem(row_idx, 3, self._create_item(data['days_display'], days_color, bold=True, is_number=True))

            # العمود 4: الراتب
            self.table.setItem(row_idx, 4, self._create_item(f"${data['wage']:,.0f}", text_color, is_number=True))

            # العمود 5: إضافي
            self.table.setItem(row_idx, 5, self._create_item(f"+${data['curr_extra']:,.0f}", success_color, is_number=True))

            # العمود 6: خصم
            self.table.setItem(row_idx, 6, self._create_item(f"-${data['curr_ded']:,.0f}", danger_color, is_number=True))

            # العمود 7: سابق
            self.table.setItem(row_idx, 7, self._create_item(f"${data['prev_balance']:,.0f}", text_color, is_number=True))

            # العمود 8: المستحق
            self.table.setItem(row_idx, 8, self._create_item(f"${data['total_due']:,.0f}", primary_color, bold=True, font_size=12, is_number=True))

            # العمود 9: سلف
            self.table.setItem(row_idx, 9, self._create_item(f"${data['cum_cash']:,.0f}", text_color, is_number=True))

            # العمود 10: سجائر
            self.table.setItem(row_idx, 10, self._create_item(f"${data['cum_cig']:,.0f}", text_color, is_number=True))

            # العمود 11: تحويل
            self.table.setItem(row_idx, 11, self._create_item(f"${data['cum_trans']:,.0f}", text_color, is_number=True))

            # العمود 12: المستلم
            self.table.setItem(row_idx, 12, self._create_item(f"${data['total_received']:,.0f}", text_color, is_number=True))

            # العمود 13: الصافي
            balance_color = success_color if data['final_balance'] > 0 else (danger_color if data['final_balance'] < 0 else text_color)
            self.table.setItem(row_idx, 13, self._create_item(f"${data['final_balance']:,.0f}", balance_color, bold=True, font_size=12, is_number=True))

            # العمود 14: أزرار الإجراءات (المحسّنة)
            actions_widget = self._create_actions_widget(data['id'], data.get('name', ''))
            self.table.setCellWidget(row_idx, 14, actions_widget)
            self.table.setRowHeight(row_idx, 52)

        self.apply_filter()

    def _create_item(self, text, color=None, bold=False, font_size=11, is_number=False):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        font = QFont("Consolas" if is_number else "Cairo", font_size)
        if bold:
            font.setBold(True)
        item.setFont(font)
        if color:
            item.setForeground(QColor(color))
        return item

    def _create_actions_widget(self, crew_id, crew_name=""):
        """إنشاء أزرار إجراءات واضحة وملونة برصانة رسمية مريحة للعين وبمساحة نقر ممتازة"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        style_print = """
            QPushButton {
                background-color: #1e293b;
                color: #93c5fd;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 62px;
                min-height: 32px;
                font-family: 'Segoe UI Emoji', 'Segoe UI', 'Cairo', sans-serif;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #273549; border-color: #3b82f6; color: #ffffff; }
            QPushButton:pressed { background-color: #0f172a; border-color: #1d4ed8; }
        """
        style_docs = """
            QPushButton {
                background-color: #1e293b;
                color: #86efac;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 60px;
                min-height: 32px;
                font-family: 'Segoe UI Emoji', 'Segoe UI', 'Cairo', sans-serif;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #273549; border-color: #10b981; color: #ffffff; }
            QPushButton:pressed { background-color: #0f172a; border-color: #059669; }
        """
        style_edit = """
            QPushButton {
                background-color: #1e293b;
                color: #fde047;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 60px;
                min-height: 32px;
                font-family: 'Segoe UI Emoji', 'Segoe UI', 'Cairo', sans-serif;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #273549; border-color: #d97706; color: #ffffff; }
            QPushButton:pressed { background-color: #0f172a; border-color: #b45309; }
        """
        style_del = """
            QPushButton {
                background-color: #1e293b;
                color: #fca5a5;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 42px;
                min-height: 32px;
                font-family: 'Segoe UI Emoji', 'Segoe UI', 'Cairo', sans-serif;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #273549; border-color: #dc2626; color: #ffffff; }
            QPushButton:pressed { background-color: #0f172a; border-color: #b91c1c; }
        """

        # زر الطباعة
        btn_print = QPushButton("🖨️ قسيمة")
        btn_print.setStyleSheet(style_print)
        btn_print.setToolTip("طباعة قسيمة الراتب PDF")
        btn_print.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_print.clicked.connect(lambda _, cid=crew_id: self.print_crew(cid))

        # زر الوثائق والشهادات
        btn_docs = QPushButton("📜 وثائق")
        btn_docs.setStyleSheet(style_docs)
        btn_docs.setToolTip("استعراض وإدارة وثائق وشهادات البحار")
        btn_docs.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_docs.clicked.connect(lambda _, cid=crew_id, cname=crew_name: self.open_crew_documents(cid, cname))

        # زر التعديل
        btn_edit = QPushButton("✏️ تعديل")
        btn_edit.setStyleSheet(style_edit)
        btn_edit.setToolTip("تعديل بيانات الحسابات")
        btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_edit.clicked.connect(lambda _, cid=crew_id: self.open_accounting(cid))

        # زر الحذف
        btn_del = QPushButton("🗑️")
        btn_del.setStyleSheet(style_del)
        btn_del.setToolTip("حذف البحار")
        btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_del.clicked.connect(lambda _, cid=crew_id: self.delete_crew(cid))

        layout.addWidget(btn_print)
        layout.addWidget(btn_docs)
        layout.addWidget(btn_edit)
        layout.addWidget(btn_del)

        return widget

    # ---------- وظائف الأزرار ----------
    def focus_search(self):
        if hasattr(self, 'search_entry'):
            self.search_entry.setFocus()
            self.search_entry.selectAll()

    def apply_filter(self):
        """تصفية الصفوف في الجدول طبقاً لنص البحث وحالة الفلتر المحددة"""
        if not hasattr(self, 'search_entry') or not hasattr(self, 'filter_combo'):
            return

        query = self.search_entry.text().strip().lower()
        filter_mode = self.filter_combo.currentIndex()  # 0: الكل, 1: مسدد, 2: غير مسدد, 3: سلف

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 1)
            rank_item = self.table.item(row, 2)
            name_text = (name_item.text() if name_item else "").lower()
            rank_text = (rank_item.text() if rank_item else "").lower()

            matches_search = (not query) or (query in name_text) or (query in rank_text)

            matches_status = True
            if filter_mode != 0 and hasattr(self, 'latest_crew_data') and row < len(self.latest_crew_data):
                crew_info = self.latest_crew_data[row]
                is_settled = crew_info.get('is_settled', False)
                cum_cash = float(crew_info.get('cum_cash', 0))

                if filter_mode == 1:
                    matches_status = bool(is_settled)
                elif filter_mode == 2:
                    matches_status = not bool(is_settled)
                elif filter_mode == 3:
                    matches_status = cum_cash > 0

            self.table.setRowHidden(row, not (matches_search and matches_status))

    def print_master_payroll_sheet(self):
        """طباعة كشف مسير الرواتب الشهري المجمع لكافة الطاقم (Landscape A4 PDF)"""
        if not hasattr(self, 'latest_crew_data') or not self.latest_crew_data:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات طاقم لطباعتها في كشف المسير.")
            return

        try:
            pdf_path = ReportService.generate_monthly_payroll_sheet(
                self.latest_crew_data,
                self.current_month,
                self.current_year
            )
            QMessageBox.information(
                self, "نجاح 🖨️",
                f"تم توليد كشف مسير الرواتب المجمع بنجاح:\n\n{pdf_path}"
            )
            os.startfile(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الطباعة", f"تعذر إنشاء كشف المسير:\n{e}")

    def export_payroll_excel(self):
        """تصدير كشف مسير الرواتب الشهري إلى Excel (.xlsx)"""
        if not hasattr(self, 'latest_crew_data') or not self.latest_crew_data:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات لتصديرها إلى Excel.")
            return

        try:
            default_name = f"Payroll_Sheet_{self.current_year}_{self.current_month:02d}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "حفظ كشف المسير Excel", default_name, "Excel Files (*.xlsx)"
            )
            if not file_path:
                return

            ReportService.export_payroll_to_excel(
                self.latest_crew_data,
                self.current_month,
                self.current_year,
                file_path
            )
            QMessageBox.information(
                self, "نجاح التصدير 📊",
                f"تم حفظ ملف Excel بنجاح في:\n\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر تصدير ملف Excel:\n{e}")

    def open_all_crew_documents(self):
        try:
            from ui_crew_documents import FleetDocumentsDialog
            dlg = FleetDocumentsDialog(db_path=self.engine.db_path, parent=self)
            dlg.exec()
            self.run_startup_alerts_check()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح منظومة الشهادات والوثائق:\n{e}")

    def open_crew_documents(self, crew_id, crew_name=""):
        try:
            from ui_crew_documents import FleetDocumentsDialog
            dlg = FleetDocumentsDialog(default_crew_id=crew_id, db_path=self.engine.db_path, parent=self)
            dlg.exec()
            self.run_startup_alerts_check()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح وثائق البحار:\n{e}")

    def print_crew(self, crew_id):
        target_crew = None
        if hasattr(self, 'latest_crew_data') and self.latest_crew_data:
            for item in self.latest_crew_data:
                if item.get('id') == crew_id:
                    target_crew = item
                    break
        
        if not target_crew:
            QMessageBox.warning(self, "تنبيه", "لم يتم العثور على بيانات هذا البحار لطباعتها.")
            return

        try:
            pdf_path = ReportService.generate_crew_payslip(target_crew)
            os.startfile(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الطباعة", f"فشل إنشاء التقرير:\n{str(e)}")

    def print_all_crew_payslips(self):
        if not hasattr(self, 'latest_crew_data') or not self.latest_crew_data:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات بحارة لطباعتها.")
            return

        try:
            pdf_path = ReportService.generate_batch_crew_payslips(self.latest_crew_data)
            os.startfile(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الطباعة", f"فشل إنشاء كشوف رواتب الجميع:\n{str(e)}")

    def delete_crew(self, crew_id):
        reply = QMessageBox.question(
            self, 'تأكيد الحذف',
            'هل أنت متأكد من حذف هذا البحار بشكل نهائي؟',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with sqlite3.connect('arn_ship_payroll.db') as conn:
                    conn.execute("DELETE FROM CrewWages WHERE No=?", (crew_id,))
                    conn.execute("DELETE FROM payroll_history WHERE crew_id=?", (crew_id,))
                    conn.commit()
                self.refresh_data()
                try:
                    from audit_service import AuditService
                    AuditService(self.engine.db_path).log_delete(
                        self.current_user["id"], self.current_user["name"], "CrewWages", crew_id, f"حذف البحار رقم {crew_id}"
                    )
                except Exception:
                    pass
                QMessageBox.information(self, "تم", "تم حذف البحار بنجاح.")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الحذف:\n{str(e)}")

    def on_badge_update(self, unread_count: int, has_critical: bool):
        """تحديث نص ولون زر التنبيهات في الهيدر"""
        if unread_count > 0:
            color = "#ef4444" if has_critical else "#f59e0b"
            self.btn_alerts.setText(f"🔔 التنبيهات ({unread_count})")
            self.btn_alerts.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color}25;
                    color: {color};
                    font-size: 13px;
                    font-weight: bold;
                    border: 1.5px solid {color};
                    border-radius: 8px;
                    padding: 6px 14px;
                }}
            """)
        else:
            self.btn_alerts.setText("🔔 التنبيهات")
            self.btn_alerts.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #e2e8f0;
                    font-size: 13px;
                    font-weight: bold;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 6px 14px;
                }
                QPushButton:hover { border-color: #38bdf8; color: #38bdf8; }
            """)

    def run_startup_alerts_check(self):
        """تشغيل الفحص الشامل للتنبيهات في خيط منفصل عند بدء التشغيل"""
        import threading
        def _check():
            try:
                from alert_service import AlertService
                svc = AlertService(self.engine.db_path)
                svc.check_all()
                counts = svc.get_alerts_counts()
                unread = counts.get('unread', 0)
                has_crit = counts.get('critical', 0) > 0
                QTimer.singleShot(0, lambda: self.on_badge_update(unread, has_crit))
            except Exception as e:
                print(f"⚠️ خطأ أثناء فحص التنبيهات عند البدء: {e}")
        threading.Thread(target=_check, daemon=True).start()

    def open_alerts_center(self):
        try:
            from ui_alerts_center import AlertsCenterWindow
            dlg = AlertsCenterWindow(self.engine.db_path, self.current_user["id"], self)
            dlg.exec()
            from alert_service import AlertService
            counts = AlertService(self.engine.db_path).get_alerts_counts()
            self.on_badge_update(counts['unread'], counts['critical'] > 0)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح مركز التنبيهات:\n{e}")

    def open_audit_log(self):
        try:
            from ui_audit_log import AuditLogWindow
            dlg = AuditLogWindow(self.engine.db_path, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح سجل التدقيق:\n{e}")

    def open_accounting(self, crew_id):
        self.acc_win = AccountingWindow(self, crew_id, self.current_month, self.current_year)
        self.acc_win.show()

    def open_add_crew(self):
        self.add_win = AddCrewWindow(self)
        self.add_win.show()

    def open_admin(self):
        self.admin_win = AdminWindow(self)
        self.admin_win.show()

    def open_master_cash(self):
        try:
            from ui_master_cash import MasterCashWindow
            self.cash_win = MasterCashWindow(self, db_path=self.engine.db_path)
            self.cash_win.show()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح صندوق القبطان: {e}")

    def open_analytics(self):
        try:
            from ui_analytics import AnalyticsWindow
            self.analytics_win = AnalyticsWindow(self, self.current_year, self.current_month)
            self.analytics_win.show()
        except ImportError as e:
            QMessageBox.critical(self, "خطأ", f"لم يتم العثور على ui_analytics.py: {e}")

    def reset_all_data(self):
        """تصفير كافة بيانات النظام وتهيئته لاستخدام قبطان أو مستخدم جديد"""
        reply = QMessageBox.warning(
            self,
            "⚠️ تحذير خطير - تهيئة وتصفير النظام",
            "هل أنت متأكد من رغبتك في تصفير ومسح كافة بيانات البحارة والحسابات والرواتب بالكامل؟\n\n"
            "هذا الإجراء سيقوم بتهيئة البرنامج لقبطان/مستخدم جديد ولا يمكن التراجع عنه!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            confirm = QMessageBox.question(
                self,
                "تأكيد نهائي",
                "تأكيد أخير: هل تريد الاستمرار والاستغناء عن كافة السجلات الحالية؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    conn = sqlite3.connect('arn_ship_payroll.db')
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM CrewWages")
                    cursor.execute("DELETE FROM payroll_history")
                    cursor.execute("DELETE FROM general_cash")
                    cursor.execute("DELETE FROM cash_closed_months")
                    cursor.execute("DELETE FROM cash_reset_snapshot")
                    try:
                        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('CrewWages', 'payroll_history', 'general_cash', 'cash_closed_months', 'cash_reset_snapshot')")
                    except:
                        pass
                    conn.commit()
                    conn.close()

                    self.refresh_data()
                    QMessageBox.information(self, "نجاح", "تم تصفير وتهيئة كافة بيانات النظام بنجاح!")
                except Exception as e:
                    QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء تصفير البيانات:\n{str(e)}")

    def show_about_dialog(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import Qt, QUrl
        from PyQt6.QtGui import QDesktopServices, QFont, QCursor

        dialog = QDialog(self)
        dialog.setWindowTitle("حول البرنامج - ARN Technology")
        dialog.setMinimumWidth(450)
        dialog.setStyleSheet("QDialog { background-color: #0f172a; } QLabel { color: #e2e8f0; font-family: 'Cairo'; }")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 25, 20, 20)
        layout.setSpacing(15)
        
        # Text Info
        info_label = QLabel(
            "<h2 style='color: #38bdf8; text-align: center; margin-bottom: 0px;'>ARN Fleet - النظام المحاسبي</h2>"
            "<p style='text-align: center; color: #94a3b8; font-size: 13px;'>الإصدار 1.0.0</p>"
            "<hr style='background-color: #334155; height: 1px; border: none; margin: 10px 0;'>"
            "<p style='text-align: center; font-size: 14px;'><b>حقوق النشر (c) 2026 لشركة ARN Technology.<br>جميع الحقوق محفوظة.</b></p>"
            "<p style='text-align: center; font-size: 14px;'>تطوير وبرمجة: <span style='color: #10b981; font-weight: bold;'>عبده رجب نصار</span></p>"
            "<p style='text-align: center; font-size: 12px; color: #64748b;'>يُمنع نسخ أو تعديل هذا البرنامج دون إذن مسبق.</p>"
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Social Buttons
        social_layout = QHBoxLayout()
        social_layout.setSpacing(20)
        social_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize
        
        # WhatsApp
        btn_wa = QPushButton()
        btn_wa.setFixedSize(50, 50)
        btn_wa.setIcon(QIcon("assets/icons/whatsapp.png"))
        btn_wa.setIconSize(QSize(40, 40))
        btn_wa.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_wa.setStyleSheet("QPushButton { background-color: transparent; border-radius: 25px; border: 1px solid transparent; } QPushButton:hover { background-color: #1e293b; border: 1px solid #334155; }")
        btn_wa.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://wa.me/201556710314")))

        # Telegram
        btn_tg = QPushButton()
        btn_tg.setFixedSize(50, 50)
        btn_tg.setIcon(QIcon("assets/icons/telegram.png"))
        btn_tg.setIconSize(QSize(40, 40))
        btn_tg.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_tg.setStyleSheet("QPushButton { background-color: transparent; border-radius: 25px; border: 1px solid transparent; } QPushButton:hover { background-color: #1e293b; border: 1px solid #334155; }")
        btn_tg.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://t.me/ABDOURNASSAR95")))

        # Facebook
        btn_fb = QPushButton()
        btn_fb.setFixedSize(50, 50)
        btn_fb.setIcon(QIcon("assets/icons/facebook.png"))
        btn_fb.setIconSize(QSize(40, 40))
        btn_fb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_fb.setStyleSheet("QPushButton { background-color: transparent; border-radius: 25px; border: 1px solid transparent; } QPushButton:hover { background-color: #1e293b; border: 1px solid #334155; }")
        btn_fb.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.facebook.com/abdouragab.nassar")))

        # Messenger
        btn_ms = QPushButton()
        btn_ms.setFixedSize(50, 50)
        btn_ms.setIcon(QIcon("assets/icons/messenger.png"))
        btn_ms.setIconSize(QSize(40, 40))
        btn_ms.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_ms.setStyleSheet("QPushButton { background-color: transparent; border-radius: 25px; border: 1px solid transparent; } QPushButton:hover { background-color: #1e293b; border: 1px solid #334155; }")
        btn_ms.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://m.me/abdouragab.nassar")))

        social_layout.addWidget(btn_wa)
        social_layout.addWidget(btn_tg)
        social_layout.addWidget(btn_fb)
        social_layout.addWidget(btn_ms)
        
        layout.addLayout(social_layout)
        
        # Close Button
        btn_close = QPushButton("إغلاق")
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.setStyleSheet("QPushButton { background-color: #334155; color: white; border-radius: 8px; padding: 10px; font-weight: bold; font-size: 14px; font-family: 'Cairo'; margin-top: 10px; } QPushButton:hover { background-color: #475569; }")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)
        
        dialog.exec()
