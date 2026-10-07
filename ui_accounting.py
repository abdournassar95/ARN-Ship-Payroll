# ui_accounting.py
import paths
import sqlite3
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                             QPushButton, QComboBox, QLineEdit, QFrame, 
                             QGraphicsDropShadowEffect, QMessageBox, QDateEdit, QCheckBox, 
                             QScrollArea, QWidget, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from ui_crew_documents import CrewDocumentsDialog


class WageHistoryDialog(QDialog):
    """نافذة استعراض سجل تدرج وزيادات راتب البحار"""
    def __init__(self, crew_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("سجل تاريخ زيادات الرواتب 📈")
        self.resize(520, 420)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("QDialog { background-color: #0f172a; } QLabel { color: #e2e8f0; font-family: 'Cairo'; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        name = crew_data.get('Name', '')
        current_wage = float(crew_data.get('MonthlyWage') or 0)
        history_raw = crew_data.get('WageHistory') or '{}'
        try:
            history = json.loads(history_raw) if isinstance(history_raw, str) else history_raw
        except Exception:
            history = {}

        lbl = QLabel(f"📈 تدرج الراتب للبحار: {name}")
        lbl.setFont(QFont("Cairo", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #38bdf8;")
        layout.addWidget(lbl)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["الفترة (سنة-شهر)", "الراتب الشهري", "الحالة"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b; border: 1px solid #334155; color: #f8fafc; font-family: 'Cairo';
            }
            QHeaderView::section {
                background-color: #0f172a; color: #94a3b8; font-weight: bold; border: none; padding: 6px;
            }
        """)

        rows = []
        for m_key in sorted(history.keys(), reverse=True):
            rows.append((m_key, float(history[m_key]), "راتب سابق"))
        rows.insert(0, ("الحالي ومستقبلاً", current_wage, "الراتب الساري الآن ⭐"))

        table.setRowCount(len(rows))
        for i, (period, wage, status) in enumerate(rows):
            it_p = QTableWidgetItem(period)
            it_p.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_w = QTableWidgetItem(f"${wage:,.2f}")
            it_w.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_w.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
            it_w.setForeground(QColor("#10b981" if i == 0 else "#94a3b8"))

            it_s = QTableWidgetItem(status)
            it_s.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_s.setForeground(QColor("#38bdf8" if i == 0 else "#64748b"))

            table.setItem(i, 0, it_p)
            table.setItem(i, 1, it_w)
            table.setItem(i, 2, it_s)

        layout.addWidget(table)

        btn_close = QPushButton("إغلاق")
        btn_close.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        btn_close.setStyleSheet("background-color: #334155; color: white; border-radius: 6px; padding: 6px 18px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignLeft)


class AccountingWindow(QDialog):
    def __init__(self, parent, crew_id, current_month, current_year):
        super().__init__(parent)
        self.parent_window = parent
        # المسار من لوحة القيادة (المحرك) وإلا من paths (ثابت) — العيب F12
        engine = getattr(parent, 'engine', None)
        self.db_path = str(getattr(engine, 'db_path', '') or paths.db_path_str())
        self.crew_id = crew_id
        self.current_month = current_month
        self.current_year = current_year
        
        self.history_cache = {} # Cache for edited months: (year, month) -> dict
        self.month_widgets = {} # (year, month) -> tuple of (frame, checkbox, btn)
        
        self.setWindowTitle("تعديل بيانات وحسابات البحار")
        self.resize(820, 750)
        self.setMinimumSize(720, 580)
        
        # Add maximize/minimize & close buttons to dialog title bar
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Apply dark theme stylesheet matching main dashboard
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QLabel {
                color: #e2e8f0;
                font-family: 'Cairo';
            }
            QCheckBox {
                color: #e2e8f0;
                font-family: 'Cairo';
                font-weight: bold;
            }
        """)
        
        self.load_db_data()
        self.build_ui()

    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 80))
        widget.setGraphicsEffect(shadow)

    def load_db_data(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        crew = cursor.execute("SELECT * FROM CrewWages WHERE No = ?", (self.crew_id,)).fetchone()
        self.crew_data = dict(crew) if crew else {}
        conn.close()
        
        self.paid_months_data = json.loads(self.crew_data.get('PaidMonthsData') or '{}')
        self.load_month_history(self.current_year, self.current_month)

    def load_month_history(self, year, month):
        key = (year, month)
        if key in self.history_cache:
            return self.history_cache[key]
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        hist = cursor.execute("SELECT * FROM payroll_history WHERE crew_id = ? AND payroll_month = ? AND payroll_year = ?", 
                              (self.crew_id, month, year)).fetchone()
        conn.close()
        
        data = dict(hist) if hist else {'extra': 0, 'deduction': 0, 'payment_cash': 0, 'cigarette': 0, 'transfer': 0}
        self.history_cache[key] = data
        return data

    def create_form_field(self, label_text, default_value="0", is_date=False, text_color=None, border_color=None):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        label = QLabel(label_text)
        label.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        label.setStyleSheet("color: #94a3b8;")
        label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        b_color = border_color if border_color else "#334155"
        t_color = text_color if text_color else "#f8fafc"
        
        if is_date:
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setStyleSheet(f"""
                QDateEdit {{
                    background-color: #0f172a;
                    border: 1px solid {b_color};
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-family: 'Cairo';
                    font-size: 11pt;
                    font-weight: bold;
                    color: {t_color};
                }}
                QDateEdit:focus {{
                    border-color: #3b82f6;
                    background-color: #1e293b;
                }}
            """)
            try:
                dt = QDate.fromString(str(default_value), "yyyy-MM-dd")
                if not dt.isValid(): dt = QDate.currentDate()
            except:
                dt = QDate.currentDate()
            widget.setDate(dt)
        else:
            widget = QLineEdit()
            widget.setText(str(default_value if default_value is not None else "0"))
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setStyleSheet(f"""
                QLineEdit {{
                    background-color: #0f172a;
                    border: 1px solid {b_color};
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-family: 'Cairo';
                    font-size: 11pt;
                    font-weight: bold;
                    color: {t_color};
                }}
                QLineEdit:focus {{
                    border-color: #3b82f6;
                    background-color: #1e293b;
                }}
            """)
            
        layout.addWidget(label)
        layout.addWidget(widget)
        return container, widget

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)
        
        # Scroll Area for main content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(16)

        # ==========================================
        # Card 1: البيانات الأساسية للبحار
        # ==========================================
        card1 = QFrame()
        card1.setObjectName("Card")
        card1.setStyleSheet("QFrame#Card { background-color: #1e293b; border: 1px solid #334155; border-radius: 14px; }")
        self.add_shadow(card1)
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(18, 18, 18, 18)
        card1_layout.setSpacing(12)
        
        title1 = QLabel("البيانات الأساسية للبحار 👤")
        title1.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        title1.setStyleSheet("color: #60a5fa;")
        title1.setAlignment(Qt.AlignmentFlag.AlignRight)
        card1_layout.addWidget(title1)
        
        grid1 = QGridLayout()
        grid1.setHorizontalSpacing(16)
        grid1.setVerticalSpacing(10)
        
        field_name, self.name_e = self.create_form_field("اسم البحار الكامل:", self.crew_data.get('Name'))
        grid1.addWidget(field_name, 0, 1)
        
        # Combo Rank
        rank_container = QWidget()
        rank_vbox = QVBoxLayout(rank_container)
        rank_vbox.setContentsMargins(0, 0, 0, 0)
        rank_vbox.setSpacing(4)
        rank_lbl = QLabel("الرتبة البحرية:")
        rank_lbl.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        rank_lbl.setStyleSheet("color: #94a3b8;")
        rank_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.rank_combo = QComboBox()
        ranks = ['MASTER', 'CH.OFF', '2nd.OFF', '3rd.OFF', 'CH.ENG', '2nd.ENG', '3rd.ENG', 'ELECTRICIAN', 'BOSUN', 'FITTER', 'PUMP MAN', 'A/B', 'O/S', 'OILER', 'WIPER', 'COOK', 'MESS BOY', 'CADET']
        c_rank = str(self.crew_data.get('Rank', 'OTHER'))
        if c_rank not in ranks: ranks.append(c_rank)
        self.rank_combo.addItems(ranks)
        self.rank_combo.setCurrentText(c_rank)
        self.rank_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
                font-family: 'Cairo';
                font-size: 11pt;
                font-weight: bold;
                color: #f8fafc;
            }
            QComboBox:focus { border-color: #3b82f6; }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }
        """)
        rank_vbox.addWidget(rank_lbl)
        rank_vbox.addWidget(self.rank_combo)
        grid1.addWidget(rank_container, 0, 0)
        
        field_wage, self.wage_e = self.create_form_field("الراتب الشهري الأساسي ($):", self.crew_data.get('MonthlyWage'))
        grid1.addWidget(field_wage, 1, 1)
        
        field_period, self.period_cal = self.create_form_field("تاريخ بدء الخدمة:", self.crew_data.get('PeriodFrom'), is_date=True)
        grid1.addWidget(field_period, 1, 0)

        field_cstart, self.contract_start_cal = self.create_form_field("تاريخ بدء العقد:", self.crew_data.get('contract_start'), is_date=True)
        grid1.addWidget(field_cstart, 2, 1)

        field_cend, self.contract_end_cal = self.create_form_field("تاريخ انتهاء العقد:", self.crew_data.get('contract_end'), is_date=True)
        grid1.addWidget(field_cend, 2, 0)
        
        card1_layout.addLayout(grid1)

        # أزرار الإجراءات الإضافية للبحار (وثائق وتاريخ رواتب)
        extra_btns_layout = QHBoxLayout()
        extra_btns_layout.setSpacing(10)

        btn_docs = QPushButton("📜 إدارة الشهادات والوثائق")
        btn_docs.setFont(QFont("Cairo", 9, QFont.Weight.Bold))
        btn_docs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_docs.setStyleSheet("""
            QPushButton {
                background-color: #0c4a6e; color: #38bdf8;
                border: 1px solid #0284c7; border-radius: 6px; padding: 6px 14px;
            }
            QPushButton:hover { background-color: #0284c7; color: #ffffff; }
        """)
        btn_docs.clicked.connect(self.open_crew_documents)

        btn_whist = QPushButton("📈 سجل تاريخ الرواتب")
        btn_whist.setFont(QFont("Cairo", 9, QFont.Weight.Bold))
        btn_whist.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_whist.setStyleSheet("""
            QPushButton {
                background-color: #2e1065; color: #c084fc;
                border: 1px solid #7c3aed; border-radius: 6px; padding: 6px 14px;
            }
            QPushButton:hover { background-color: #7c3aed; color: #ffffff; }
        """)
        btn_whist.clicked.connect(self.open_wage_history)

        extra_btns_layout.addWidget(btn_docs)
        extra_btns_layout.addWidget(btn_whist)
        extra_btns_layout.addStretch()
        card1_layout.addLayout(extra_btns_layout)

        content_layout.addWidget(card1)

        # ==========================================
        # Card 2: سجل الشهور والتسويات (مع تشيك بوكس مباشر)
        # ==========================================
        card_months = QFrame()
        card_months.setObjectName("Card")
        card_months.setStyleSheet("QFrame#Card { background-color: #1e293b; border: 1px solid #334155; border-radius: 14px; }")
        self.add_shadow(card_months)
        cm_layout = QVBoxLayout(card_months)
        cm_layout.setContentsMargins(18, 18, 18, 18)
        cm_layout.setSpacing(10)
        
        cm_header = QHBoxLayout()
        sub_desc = QLabel("فعّل الخيار (☑) بجوار الشهر لإقفاله، أو اضغط تعديل 💡")
        sub_desc.setFont(QFont("Cairo", 9, QFont.Weight.Bold))
        sub_desc.setStyleSheet("color: #94a3b8;")
        
        title_months = QLabel("سجل الشهور والتسويات 📅")
        title_months.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        title_months.setStyleSheet("color: #a78bfa;")
        
        cm_header.addWidget(sub_desc, alignment=Qt.AlignmentFlag.AlignLeft)
        cm_header.addStretch()
        cm_header.addWidget(title_months, alignment=Qt.AlignmentFlag.AlignRight)
        cm_layout.addLayout(cm_header)
        
        # Scroll Area for Month items
        months_scroll = QScrollArea()
        months_scroll.setWidgetResizable(True)
        months_scroll.setFixedHeight(190)
        months_scroll.setStyleSheet("QScrollArea { border: 1px solid #334155; background-color: #0f172a; border-radius: 10px; }")
        
        self.months_container = QWidget()
        self.months_grid = QGridLayout(self.months_container)
        self.months_grid.setContentsMargins(10, 10, 10, 10)
        self.months_grid.setHorizontalSpacing(10)
        self.months_grid.setVerticalSpacing(10)
        
        months_scroll.setWidget(self.months_container)
        cm_layout.addWidget(months_scroll)
        content_layout.addWidget(card_months)

        # ==========================================
        # Card 3: المعاملات المالية للشهر المحدد
        # ==========================================
        card2 = QFrame()
        card2.setObjectName("Card")
        card2.setStyleSheet("QFrame#Card { background-color: #1e293b; border: 1px solid #334155; border-radius: 14px; }")
        self.add_shadow(card2)
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(18, 18, 18, 18)
        card2_layout.setSpacing(12)
        
        self.title2 = QLabel(f"معاملات شهر ({self.current_month:02d}-{self.current_year}) 💰")
        self.title2.setFont(QFont("Cairo", 13, QFont.Weight.Bold))
        self.title2.setStyleSheet("color: #fbbf24;")
        self.title2.setAlignment(Qt.AlignmentFlag.AlignRight)
        card2_layout.addWidget(self.title2)
        
        grid2 = QGridLayout()
        grid2.setHorizontalSpacing(16)
        grid2.setVerticalSpacing(10)
        
        cur_hist = self.history_cache.get((self.current_year, self.current_month), {})
        
        f_extra, self.extra_e = self.create_form_field("إضافي / مكافآت ($):", cur_hist.get('extra', 0), text_color="#34d399", border_color="#059669")
        grid2.addWidget(f_extra, 0, 1)
        
        f_deduct, self.deduct_e = self.create_form_field("خصم مباشر ($):", cur_hist.get('deduction', 0), text_color="#f87171", border_color="#dc2626")
        grid2.addWidget(f_deduct, 0, 0)
        
        f_cash, self.cash_e = self.create_form_field("سلفة نقدية (Cash) ($):", cur_hist.get('payment_cash', 0))
        grid2.addWidget(f_cash, 1, 1)
        
        f_cig, self.cig_e = self.create_form_field("سجائر وستور ($):", cur_hist.get('cigarette', 0))
        grid2.addWidget(f_cig, 1, 0)
        
        f_trans, self.trans_e = self.create_form_field("تحويل بنكي ($):", cur_hist.get('transfer', 0))
        grid2.addWidget(f_trans, 2, 1)
        
        f_prev, self.prev_e = self.create_form_field("رصيد مرحل استثنائي ($):", self.crew_data.get('PREVIOUS', 0))
        grid2.addWidget(f_prev, 2, 0)
        
        card2_layout.addLayout(grid2)
        content_layout.addWidget(card2)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        self.populate_months_grid()

        # ==========================================
        # Bottom Buttons
        # ==========================================
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(14)
        
        btn_cancel = QPushButton("إلغاء ❌")
        btn_cancel.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #475569;
                color: #94a3b8;
                border-radius: 8px;
                padding: 10px 24px;
            }
            QPushButton:hover { background-color: #334155; color: #e2e8f0; }
        """)
        btn_cancel.clicked.connect(self.close)
        
        btn_save = QPushButton("حفظ التعديلات 💾")
        btn_save.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 28px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        btn_save.clicked.connect(self.save_data)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)

    def populate_months_grid(self):
        # Clear existing items in grid
        for i in reversed(range(self.months_grid.count())):
            w = self.months_grid.itemAt(i).widget()
            if w:
                w.setParent(None)
                
        self.month_widgets.clear()
        
        period_from = self.crew_data.get('PeriodFrom')
        start_date = None
        if period_from:
            try: start_date = datetime.strptime(period_from, "%Y-%m-%d")
            except: pass
        
        if not start_date:
            start_date = datetime(self.current_year, 1, 1)
            
        now = datetime.now()
        end_date = datetime(now.year, now.month, 1)
        
        requested_date = datetime(self.current_year, self.current_month, 1)
        if requested_date > end_date:
            end_date = requested_date

        months_list = []
        current = start_date.replace(day=1)
        while current <= end_date:
            months_list.append((current.year, current.month))
            current += relativedelta(months=1)
            
        months_list.reverse()
        
        month_arabic = {
            1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل', 5: 'مايو', 6: 'يونيو',
            7: 'يوليو', 8: 'أغسطس', 9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
        }
        
        for idx, (y, m) in enumerate(months_list):
            m_key = f"{y}-{m:02d}"
            is_settled = self.paid_months_data.get(m_key, False)
            is_active = (y == self.current_year and m == self.current_month)
            
            frame = QFrame()
            f_layout = QHBoxLayout(frame)
            f_layout.setContentsMargins(10, 6, 10, 6)
            f_layout.setSpacing(8)
            
            # Checkbox for settlement
            cb = QCheckBox("تسوية 🔒" if is_settled else "تفتيح 🔓")
            cb.setFont(QFont("Cairo", 9, QFont.Weight.Bold))
            cb.setChecked(bool(is_settled))
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Label for month
            lbl_name = QLabel(f"{month_arabic.get(m, m)} {y} ({m:02d})")
            lbl_name.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
            lbl_name.setStyleSheet("color: #e2e8f0;")
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignRight)
            
            btn_select = QPushButton("تعديل ✏️" if not is_active else "محدد 📍")
            btn_select.setFont(QFont("Cairo", 9, QFont.Weight.Bold))
            btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
            
            if is_active:
                btn_select.setStyleSheet("""
                    QPushButton {
                        background-color: #10b981;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 4px 10px;
                    }
                """)
                btn_select.setEnabled(False)
            else:
                btn_select.setStyleSheet("""
                    QPushButton {
                        background-color: #3b82f6;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 4px 10px;
                    }
                    QPushButton:hover { background-color: #2563eb; }
                """)
            
            # Connect Checkbox toggle
            def make_cb_handler(key, check_box, item_frame, year_val, month_val):
                def handler(state):
                    checked = (state == Qt.CheckState.Checked.value or state == True or state == 2)
                    self.paid_months_data[key] = checked
                    check_box.setText("تسوية 🔒" if checked else "تفتيح 🔓")
                    self.update_month_frame_style(item_frame, checked, (year_val == self.current_year and month_val == self.current_month))
                return handler

            cb.stateChanged.connect(make_cb_handler(m_key, cb, frame, y, m))
            
            # Connect Select button
            btn_select.clicked.connect(lambda _, year=y, month=m: self.select_month(year, month))
            
            f_layout.addWidget(cb, alignment=Qt.AlignmentFlag.AlignLeft)
            f_layout.addWidget(btn_select)
            f_layout.addStretch()
            f_layout.addWidget(lbl_name)
            
            self.update_month_frame_style(frame, is_settled, is_active)
            self.month_widgets[(y, m)] = (frame, cb, btn_select)
            
            row = idx // 2
            col = idx % 2
            self.months_grid.addWidget(frame, row, col)

    def update_month_frame_style(self, frame, is_settled, is_active):
        if is_active:
            frame.setStyleSheet("""
                QFrame {
                    background-color: #1e3a8a;
                    border: 2px solid #3b82f6;
                    border-radius: 8px;
                }
            """)
        elif is_settled:
            frame.setStyleSheet("""
                QFrame {
                    background-color: #064e3b;
                    border: 1.5px solid #10b981;
                    border-radius: 8px;
                }
            """)
        else:
            frame.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 8px;
                }
            """)

    def save_current_form_to_cache(self):
        try:
            extra = float(self.extra_e.text() or 0)
            deduct = float(self.deduct_e.text() or 0)
            cash = float(self.cash_e.text() or 0)
            cig = float(self.cig_e.text() or 0)
            trans = float(self.trans_e.text() or 0)
            self.history_cache[(self.current_year, self.current_month)] = {
                'extra': extra,
                'deduction': deduct,
                'payment_cash': cash,
                'cigarette': cig,
                'transfer': trans
            }
        except ValueError:
            pass

    def select_month(self, year, month):
        # 1. Save current form values to cache
        self.save_current_form_to_cache()
        
        # 2. Switch current month
        self.current_year = year
        self.current_month = month
        
        # 3. Load values for new month
        cur_hist = self.load_month_history(self.current_year, self.current_month)
        
        self.extra_e.setText(str(cur_hist.get('extra', 0)))
        self.deduct_e.setText(str(cur_hist.get('deduction', 0)))
        self.cash_e.setText(str(cur_hist.get('payment_cash', 0)))
        self.cig_e.setText(str(cur_hist.get('cigarette', 0)))
        self.trans_e.setText(str(cur_hist.get('transfer', 0)))
        
        self.title2.setText(f"معاملات شهر ({self.current_month:02d}-{self.current_year}) 💰")
        
        # 4. Refresh grid styles
        self.populate_months_grid()

    def save_data(self):
        try:
            # Save active form
            self.save_current_form_to_cache()
            
            name = self.name_e.text()
            rank = self.rank_combo.currentText()
            new_wage = float(self.wage_e.text() or 0)
            period_from = self.period_cal.date().toString("yyyy-MM-dd")
            contract_start = self.contract_start_cal.date().toString("yyyy-MM-dd")
            contract_end = self.contract_end_cal.date().toString("yyyy-MM-dd")
            previous = float(self.prev_e.text() or 0)
            
            # Clean up paid_months_data: remove False entries
            cleaned_paid = {k: True for k, v in self.paid_months_data.items() if v}
            paid_data_json = json.dumps(cleaned_paid)

            old_wage = float(self.crew_data.get('MonthlyWage') or 0)
            wage_history = json.loads(self.crew_data.get('WageHistory') or '{}')
            
            if old_wage != new_wage:
                start_str = period_from if period_from else f"{self.current_year}-{self.current_month:02d}-01"
                try: start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(day=1)
                except: start_date = datetime(self.current_year, self.current_month, 1)
                end_date = datetime(self.current_year, self.current_month, 1) - relativedelta(months=1)
                
                current = start_date
                while current <= end_date:
                    m_key = current.strftime("%Y-%m")
                    if m_key not in wage_history: wage_history[m_key] = old_wage
                    current += relativedelta(months=1)
                    
                current_edit_key = f"{self.current_year}-{self.current_month:02d}"
                keys_to_remove = [k for k in wage_history.keys() if k >= current_edit_key]
                for k in keys_to_remove: del wage_history[k]
                    
            wage_history_json = json.dumps(wage_history)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE CrewWages 
                SET Name=?, Rank=?, MonthlyWage=?, PeriodFrom=?, contract_start=?, contract_end=?, PREVIOUS=?, PaidMonthsData=?, WageHistory=? 
                WHERE No=?
            """, (name, rank, new_wage, period_from, contract_start, contract_end, previous, paid_data_json, wage_history_json, self.crew_id))
            
            # Write all edited months from history_cache to DB
            for (y, m), hdata in self.history_cache.items():
                cursor.execute("""
                    INSERT INTO payroll_history (crew_id, payroll_month, payroll_year, extra, deduction, payment_cash, cigarette, transfer)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(crew_id, payroll_month, payroll_year) 
                    DO UPDATE SET extra=excluded.extra, deduction=excluded.deduction, payment_cash=excluded.payment_cash, cigarette=excluded.cigarette, transfer=excluded.transfer
                """, (self.crew_id, m, y, hdata.get('extra', 0), hdata.get('deduction', 0), hdata.get('payment_cash', 0), hdata.get('cigarette', 0), hdata.get('transfer', 0)))
                
            conn.commit()
            conn.close()

            # تسجيل في سجل التدقيق وفحص التنبيهات
            try:
                from audit_service import AuditService
                from alert_service import AlertService
                audit = AuditService()
                if old_wage != new_wage:
                    audit.log(1, "ADMIN", "UPDATE_WAGE", "CrewWages", self.crew_id, f"تعديل راتب البحار {name} من ${old_wage:,.2f} إلى ${new_wage:,.2f}")
                audit.log_update(1, "ADMIN", "CrewWages", self.crew_id, f"تحديث حسابات وتسويات البحار {name}")
                
                alert_svc = AlertService()
                alert_svc.check_contract_expiry()
                alert_svc.check_high_advance(self.crew_id, self.current_month, self.current_year)
                alert_svc.check_unusual_deduction(self.crew_id, self.current_month, self.current_year)
            except Exception as e:
                print(f"⚠️ خطأ غير معطل في التدقيق/التنبيهات: {e}")
            
            if hasattr(self.parent_window, 'load_data'):
                self.parent_window.load_data()
            elif hasattr(self.parent_window, 'refresh_data'):
                self.parent_window.refresh_data()
                
            QMessageBox.information(self, "نجاح", "تم حفظ كافة التعديلات والتسويات بنجاح!")
            self.close()

        except ValueError:
            QMessageBox.critical(self, "خطأ في الإدخال", "يرجى إدخال أرقام صحيحة.")

    def open_crew_documents(self):
        try:
            crew_name = self.name_e.text().strip() or str(self.crew_id)
            dlg = CrewDocumentsDialog(self.crew_id, crew_name, parent=self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح وثائق البحار: {e}")

    def open_wage_history(self):
        try:
            dlg = WageHistoryDialog(self.crew_data, parent=self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر فتح سجل تاريخ الرواتب: {e}")