# ui_master_cash.py
"""
نافذة إدارة صندوق القبطان والعهد النقدية وإقفال الشهور (Master Cash Management)
تطوير وبرمجة: عبده رجب نصار - شركة ARN Technology © 2026
"""

import sqlite3
import os
import calendar
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QDateEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
    QGraphicsDropShadowEffect, QAbstractItemView, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QCursor

from report_service import ReportService
from audit_service import AuditService


class MasterCashWindow(QDialog):
    """نافذة إدارة صندوق القبطان والعهد النقدية"""

    def __init__(self, parent=None, db_path='arn_ship_payroll.db'):
        super().__init__(parent)
        self.parent_window = parent
        self.db_path = db_path

        now = datetime.now()
        self.current_month = now.month
        self.current_year = now.year

        self.setWindowTitle("صندوق القبطان والعهد النقدية 💰 - ARN Fleet")
        self.resize(1100, 750)
        self.setMinimumSize(950, 650)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinMaxButtonsHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.apply_stylesheet()
        self.build_ui()
        self.load_cash_data()

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
            }
            QFrame#Card {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QLabel {
                color: #e2e8f0;
                font-family: 'Cairo', 'Segoe UI', sans-serif;
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 7px 12px;
                color: #f8fafc;
                font-family: 'Cairo';
                font-size: 11pt;
                font-weight: bold;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border-color: #3b82f6;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
                border: 1px solid #334155;
            }
            QPushButton {
                font-family: 'Cairo';
                font-weight: bold;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 11pt;
            }
            QPushButton#Primary { background-color: #3b82f6; color: #ffffff; border: none; }
            QPushButton#Primary:hover { background-color: #2563eb; }
            QPushButton#Success { background-color: #10b981; color: #ffffff; border: none; }
            QPushButton#Success:hover { background-color: #059669; }
            QPushButton#Danger { background-color: #ef4444; color: #ffffff; border: none; }
            QPushButton#Danger:hover { background-color: #dc2626; }
            QPushButton#Outline { background-color: transparent; border: 1px solid #475569; color: #94a3b8; }
            QPushButton#Outline:hover { background-color: #334155; color: #e2e8f0; }

            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                gridline-color: #33415540;
                color: #e2e8f0;
                font-family: 'Cairo';
                border-radius: 8px;
                selection-background-color: #3b82f640;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                padding: 9px;
                border: none;
                border-bottom: 2px solid #3b82f6;
                font-weight: bold;
                font-size: 11pt;
            }
        """)

    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(14)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 60))
        widget.setGraphicsEffect(shadow)

    def create_kpi_card(self, title, color_hex):
        card = QFrame()
        card.setObjectName("Card")
        self.add_shadow(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #94a3b8;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_val = QLabel("$0.00")
        lbl_val.setFont(QFont("Cairo", 15, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {color_hex};")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return card, lbl_val

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. شريط العنوان واختيار الفترة
        header_layout = QHBoxLayout()
        title_lbl = QLabel("🚢 إدارة صندوق القبطان والعهد النقدية (Master Cash)")
        title_lbl.setFont(QFont("Cairo", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38bdf8;")
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()

        lbl_status = QLabel("")
        lbl_status.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        self.lbl_month_status = lbl_status
        header_layout.addWidget(self.lbl_month_status)

        # محدد السنة والشهر
        lbl_year = QLabel("السنة:")
        lbl_year.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        self.year_entry = QLineEdit(str(self.current_year))
        self.year_entry.setFixedWidth(75)
        self.year_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.year_entry.editingFinished.connect(self.on_period_changed)

        lbl_month = QLabel("الشهر:")
        lbl_month.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        self.month_combo = QComboBox()
        self.month_combo.setMinimumWidth(150)
        months_arabic = [
            "1 - يناير", "2 - فبراير", "3 - مارس", "4 - أبريل", "5 - مايو", "6 - يونيو",
            "7 - يوليو", "8 - أغسطس", "9 - سبتمبر", "10 - أكتوبر", "11 - نوفمبر", "12 - ديسمبر"
        ]
        for m_name in months_arabic:
            self.month_combo.addItem(m_name)
        self.month_combo.setCurrentIndex(self.current_month - 1)
        self.month_combo.currentIndexChanged.connect(self.on_period_changed)

        header_layout.addWidget(lbl_year)
        header_layout.addWidget(self.year_entry)
        header_layout.addWidget(lbl_month)
        header_layout.addWidget(self.month_combo)

        main_layout.addLayout(header_layout)

        # 2. بطاقات مؤشرات الصندوق (KPI Cards)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        card_in, self.val_kpi_in = self.create_kpi_card("إجمالي الوارد (Income) 📈", "#10b981")
        card_out, self.val_kpi_out = self.create_kpi_card("المصروفات العامة (Expenses) 📉", "#ef4444")
        card_adv, self.val_kpi_adv = self.create_kpi_card("سلف البحارة للشهر (Advances) 👥", "#f59e0b")
        card_net, self.val_kpi_net = self.create_kpi_card("الرصيد الصافي المتبقي (Net Cash) 💰", "#38bdf8")

        kpi_layout.addWidget(card_in)
        kpi_layout.addWidget(card_out)
        kpi_layout.addWidget(card_adv)
        kpi_layout.addWidget(card_net)
        main_layout.addLayout(kpi_layout)

        # 3. شريط إضافة حركة جديدة سريعة (كارد إدخال)
        add_card = QFrame()
        add_card.setObjectName("Card")
        self.add_shadow(add_card)
        add_layout = QHBoxLayout(add_card)
        add_layout.setContentsMargins(15, 12, 15, 12)
        add_layout.setSpacing(10)

        lbl_add_title = QLabel("إضافة قيد نقدي:")
        lbl_add_title.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        lbl_add_title.setStyleSheet("color: #a78bfa;")
        add_layout.addWidget(lbl_add_title)

        self.date_entry = QDateEdit()
        self.date_entry.setCalendarPopup(True)
        self.date_entry.setDisplayFormat("yyyy-MM-dd")
        self.date_entry.setDate(QDate.currentDate())
        self.date_entry.setFixedWidth(130)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["وارد", "صادر"])
        self.type_combo.setFixedWidth(100)

        self.amount_entry = QLineEdit()
        self.amount_entry.setPlaceholderText("المبلغ ($)")
        self.amount_entry.setFixedWidth(110)
        self.amount_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.desc_entry = QLineEdit()
        self.desc_entry.setPlaceholderText("بيان الحركة (مثال: تمويل الصندوق من الوكيل، مشتريات خضار ولحوم...)")

        self.btn_save_tx = QPushButton("حفظ الحركة ➕")
        self.btn_save_tx.setObjectName("Primary")
        self.btn_save_tx.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_save_tx.clicked.connect(self.add_transaction)

        add_layout.addWidget(self.date_entry)
        add_layout.addWidget(self.type_combo)
        add_layout.addWidget(self.amount_entry)
        add_layout.addWidget(self.desc_entry)
        add_layout.addWidget(self.btn_save_tx)

        main_layout.addWidget(add_card)

        # 4. جدول حركات الصندوق
        table_card = QFrame()
        table_card.setObjectName("Card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 12, 12, 12)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "م", "التاريخ", "البيان", "النوع", "المبلغ ($)", "الرصيد التراكمي ($)", "الإجراءات"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # البيان ممدود
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 45)   # م
        self.table.setColumnWidth(1, 110)  # التاريخ
        self.table.setColumnWidth(2, 280)  # البيان
        self.table.setColumnWidth(3, 85)   # النوع
        self.table.setColumnWidth(4, 110)  # المبلغ
        self.table.setColumnWidth(5, 130)  # الرصيد
        self.table.setColumnWidth(6, 90)   # الإجراءات

        table_layout.addWidget(self.table)
        main_layout.addWidget(table_card)

        # 5. شريط الأزرار السفلية (طباعة، إكسيل، إقفال، تسليم العهدة)
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_print = QPushButton("🖨️  طباعة كشف الصندوق (PDF)")
        self.btn_print.setObjectName("Primary")
        self.btn_print.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_print.clicked.connect(self.print_report)

        self.btn_excel = QPushButton("📊  تصدير Excel (.xlsx)")
        self.btn_excel.setObjectName("Success")
        self.btn_excel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_excel.clicked.connect(self.export_excel)

        self.btn_close_month = QPushButton("🔒  إقفال الشهر")
        self.btn_close_month.setObjectName("Outline")
        self.btn_close_month.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close_month.clicked.connect(self.toggle_month_closure)

        self.btn_handover = QPushButton("🤝  تسليم واستلام العهدة")
        self.btn_handover.setObjectName("Danger")
        self.btn_handover.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_handover.setToolTip("تصفير العهدة المنصرفة وتوثيق محضر تسليم بين القادة")
        self.btn_handover.clicked.connect(self.handle_handover_reset)

        btn_bar.addWidget(self.btn_print)
        btn_bar.addWidget(self.btn_excel)
        btn_bar.addWidget(self.btn_close_month)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_handover)

        main_layout.addLayout(btn_bar)

    def on_period_changed(self):
        try:
            self.current_year = int(self.year_entry.text().strip())
            self.current_month = self.month_combo.currentIndex() + 1
            self.load_cash_data()
        except ValueError:
            pass

    def is_month_closed(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                res = conn.execute(
                    "SELECT COUNT(*) FROM cash_closed_months WHERE month=? AND year=?",
                    (self.current_month, self.current_year)
                ).fetchone()
                return res[0] > 0
        except Exception:
            return False

    def load_cash_data(self):
        """تحميل وتحديث حركات الصندوق وحساب الإحصائيات"""
        closed = self.is_month_closed()
        if closed:
            self.lbl_month_status.setText("🔒 الشهر مقفل محاسبياً")
            self.lbl_month_status.setStyleSheet("color: #ef4444; font-weight: bold;")
            self.btn_close_month.setText("🔓  إلغاء إقفال الشهر")
            self.btn_save_tx.setEnabled(False)
            self.btn_save_tx.setStyleSheet("background-color: #475569; color: #94a3b8;")
        else:
            self.lbl_month_status.setText("🔓 الشهر مفتوح للقيود")
            self.lbl_month_status.setStyleSheet("color: #10b981; font-weight: bold;")
            self.btn_close_month.setText("🔒  إقفال الشهر")
            self.btn_save_tx.setEnabled(True)
            self.btn_save_tx.setStyleSheet("")

        # تحديد تاريخ بداية ونهاية الشهر المختار
        m_start = f"{self.current_year}-{self.current_month:02d}-01"
        last_day = calendar.monthrange(self.current_year, self.current_month)[1]
        m_end = f"{self.current_year}-{self.current_month:02d}-{last_day:02d}"

        transactions = []
        total_in = 0.0
        total_out = 0.0
        crew_advances = 0.0
        cleared_advances = 0.0

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 1. سلف البحارة لهذا الشهر من جدول الرواتب
                adv_row = cursor.execute("""
                    SELECT COALESCE(SUM(payment_cash), 0) as total_adv 
                    FROM payroll_history 
                    WHERE payroll_month = ? AND payroll_year = ?
                """, (self.current_month, self.current_year)).fetchone()
                crew_advances = float(adv_row['total_adv']) if adv_row else 0.0

                # 2. فحص السلف المصفاة بموجب محضر استلام
                snap_row = cursor.execute("""
                    SELECT COALESCE(SUM(cleared_cash), 0) as total_cleared 
                    FROM cash_reset_snapshot 
                    WHERE payroll_month = ? AND payroll_year = ?
                """, (self.current_month, self.current_year)).fetchone()
                cleared_advances = float(snap_row['total_cleared']) if snap_row else 0.0

                # 3. حركات الصندوق العامة ضمن هذا الشهر
                rows = cursor.execute("""
                    SELECT id, date, description, type, amount 
                    FROM general_cash 
                    WHERE date >= ? AND date <= ? 
                    ORDER BY date ASC, id ASC
                """, (m_start, m_end)).fetchall()
                transactions = [dict(r) for r in rows]

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل قراءة بيانات الصندوق: {e}")
            return

        # حساب الإجماليات
        for tx in transactions:
            amt = float(tx['amount'] or 0)
            if tx['type'] == 'وارد':
                total_in += amt
            else:
                total_out += amt

        # صافي سلف البحارة المحملة على الصندوق لهذا الشهر
        effective_crew_adv = max(0.0, crew_advances - cleared_advances)
        net_cash = total_in - total_out - effective_crew_adv

        # تحديث كروت المؤشرات
        self.val_kpi_in.setText(f"+${total_in:,.2f}")
        self.val_kpi_out.setText(f"-${total_out:,.2f}")
        self.val_kpi_adv.setText(f"-${effective_crew_adv:,.2f}")
        self.val_kpi_net.setText(f"${net_cash:,.2f}")
        if net_cash >= 0:
            self.val_kpi_net.setStyleSheet("color: #38bdf8;")
        else:
            self.val_kpi_net.setStyleSheet("color: #ef4444;")

        # تعبئة الجدول
        self.table.setRowCount(0)
        running_bal = 0.0

        for i, tx in enumerate(transactions):
            self.table.insertRow(i)
            self.table.setRowHeight(i, 44)
            amt = float(tx['amount'] or 0)

            if tx['type'] == 'وارد':
                running_bal += amt
                color_type = "#10b981"
                sign = "+"
            else:
                running_bal -= amt
                color_type = "#ef4444"
                sign = "-"

            # م
            it_idx = QTableWidgetItem(str(i + 1))
            it_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_idx.setForeground(QColor("#64748b"))
            self.table.setItem(i, 0, it_idx)

            # التاريخ
            it_date = QTableWidgetItem(str(tx['date'] or ''))
            it_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_date.setFont(QFont("Cairo", 10))
            self.table.setItem(i, 1, it_date)

            # البيان
            it_desc = QTableWidgetItem(str(tx['description'] or ''))
            it_desc.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            it_desc.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
            self.table.setItem(i, 2, it_desc)

            # النوع
            it_type = QTableWidgetItem(str(tx['type']))
            it_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_type.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
            it_type.setForeground(QColor(color_type))
            self.table.setItem(i, 3, it_type)

            # المبلغ
            it_amt = QTableWidgetItem(f"{sign}${amt:,.2f}")
            it_amt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_amt.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
            it_amt.setForeground(QColor(color_type))
            self.table.setItem(i, 4, it_amt)

            # الرصيد التراكمي
            it_bal = QTableWidgetItem(f"${running_bal:,.2f}")
            it_bal.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_bal.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
            it_bal.setForeground(QColor("#38bdf8"))
            self.table.setItem(i, 5, it_bal)

            # زر الحذف
            btn_del = QPushButton("🗑️ حذف")
            btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_del.setStyleSheet("""
                QPushButton {
                    background-color: #4c0519; color: #f43f5e;
                    border: 1px solid #e11d48; border-radius: 5px;
                    padding: 3px 8px; font-size: 10px; font-weight: bold;
                }
                QPushButton:hover { background-color: #e11d48; color: #ffffff; }
            """)
            btn_del.setEnabled(not closed)
            btn_del.clicked.connect(lambda _, tx_id=tx['id'], desc=tx['description']: self.delete_transaction(tx_id, desc))
            self.table.setCellWidget(i, 6, btn_del)

        self.latest_transactions = transactions
        self.latest_summary = {
            'in': total_in,
            'out': total_out,
            'crew_adv': effective_crew_adv,
            'net': net_cash,
            'old_adv': 0.0
        }

    def add_transaction(self):
        """إضافة قيد نقدي جديد إلى جدول general_cash"""
        if self.is_month_closed():
            QMessageBox.warning(self, "حظر", "هذا الشهر مقفل محاسبياً، يرجى إلغاء الإقفال أولاً لإضافة قيود.")
            return

        date_str = self.date_entry.date().toString("yyyy-MM-dd")
        tx_type = self.type_combo.currentText()
        desc = self.desc_entry.text().strip()
        amt_str = self.amount_entry.text().strip()

        if not desc:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة بيان واضح للحركة النقدية.")
            return

        try:
            amount = float(amt_str)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "خطأ في الإدخال", "يرجى إدخال مبلغ صحيح وموجب.")
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO general_cash (amount, type, description, date)
                    VALUES (?, ?, ?, ?)
                """, (amount, tx_type, desc, date_str))
                tx_id = cursor.lastrowid
                conn.commit()

            # تسجيل في سجل التدقيق
            try:
                AuditService(self.db_path).log(
                    1, "ADMIN", "CREATE", "general_cash", tx_id,
                    f"إضافة قيد نقدي ({tx_type}) بمبلغ ${amount:,.2f} - {desc}"
                )
            except Exception:
                pass

            self.amount_entry.clear()
            self.desc_entry.clear()
            self.load_cash_data()
            QMessageBox.information(self, "نجاح", "تم حفظ الحركة النقدية بنجاح!")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء حفظ الحركة:\n{e}")

    def delete_transaction(self, tx_id, description):
        """حذف قيد نقدي محدد"""
        if self.is_month_closed():
            QMessageBox.warning(self, "حظر", "الشهر مقفل محاسبياً، لا يمكن حذف القيود.")
            return

        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل أنت متأكد من رغبتك في حذف القيد:\n'{description}'؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM general_cash WHERE id = ?", (tx_id,))
                    conn.commit()

                try:
                    AuditService(self.db_path).log(
                        1, "ADMIN", "DELETE", "general_cash", tx_id,
                        f"حذف قيد نقدي رقم {tx_id}: {description}"
                    )
                except Exception:
                    pass

                self.load_cash_data()
                QMessageBox.information(self, "نجاح", "تم حذف القيد بنجاح.")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر حذف القيد:\n{e}")

    def toggle_month_closure(self):
        """إقفال أو إلغاء إقفال الشهر المحدد"""
        closed = self.is_month_closed()
        if closed:
            reply = QMessageBox.question(
                self, "إلغاء الإقفال",
                f"هل تريد إعادة فتح شهر ({self.current_month:02d}-{self.current_year}) للسماح بالتعديل؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            "DELETE FROM cash_closed_months WHERE month=? AND year=?",
                            (self.current_month, self.current_year)
                        )
                        conn.commit()
                    AuditService(self.db_path).log(
                        1, "ADMIN", "UPDATE", "cash_closed_months", 0,
                        f"إلغاء إقفال شهر الصندوق {self.current_month}/{self.current_year}"
                    )
                    self.load_cash_data()
                    QMessageBox.information(self, "تم", "تم فتح الشهر للقيود والتعديلات.")
                except Exception as e:
                    QMessageBox.critical(self, "خطأ", f"فشل فتح الشهر: {e}")
        else:
            reply = QMessageBox.question(
                self, "إقفال الشهر",
                f"هل أنت متأكد من إقفال شهر ({self.current_month:02d}-{self.current_year}) محاسبياً؟\n\nلن يتمكن أي مستخدم من تعديل أو حذف القيود بعد الإقفال.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            "INSERT OR IGNORE INTO cash_closed_months (month, year) VALUES (?, ?)",
                            (self.current_month, self.current_year)
                        )
                        conn.commit()
                    AuditService(self.db_path).log(
                        1, "ADMIN", "LOCK", "cash_closed_months", 0,
                        f"إقفال شهر الصندوق {self.current_month}/{self.current_year}"
                    )
                    self.load_cash_data()
                    QMessageBox.information(self, "تم", "تم إقفال الشهر بنجاح.")
                except Exception as e:
                    QMessageBox.critical(self, "خطأ", f"فشل إقفال الشهر: {e}")

    def handle_handover_reset(self):
        """تسليم واستلام العهدة البحرية وتصفير المسحوبات للقائد الجديد"""
        reply = QMessageBox.warning(
            self, "تسليم واستلام العهدة البحرية 🤝",
            f"هذا الإجراء يقوم بتصفير عهدة وسلف البحارة المستلمة لشهر ({self.current_month:02d}-{self.current_year}) "
            "وتوثيق لقطة مالية في النظام لحساب القبطان الجديد.\n\nهل ترغب في المتابعة؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    # جلب كافة سلف البحارة في هذا الشهر
                    advances = cursor.execute("""
                        SELECT crew_id, payment_cash 
                        FROM payroll_history 
                        WHERE payroll_month = ? AND payroll_year = ? AND payment_cash > 0
                    """, (self.current_month, self.current_year)).fetchall()

                    total_cleared = 0.0
                    for row in advances:
                        cid, pcash = row[0], float(row[1])
                        total_cleared += pcash
                        cursor.execute("""
                            INSERT INTO cash_reset_snapshot (crew_id, payroll_month, payroll_year, cleared_cash)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(crew_id, payroll_month, payroll_year)
                            DO UPDATE SET cleared_cash = excluded.cleared_cash
                        """, (cid, self.current_month, self.current_year, pcash))

                    # تسجيل حركة إدارية في الصندوق
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    cursor.execute("""
                        INSERT INTO general_cash (amount, type, description, date)
                        VALUES (?, ?, ?, ?)
                    """, (0.0, "وارد", f"محضر تسليم واستلام العهدة البحرية - تصفية سلف بقيمة ${total_cleared:,.2f}", today_str))

                    conn.commit()

                AuditService(self.db_path).log(
                    1, "ADMIN", "HANDOVER", "cash_reset_snapshot", 0,
                    f"تسليم واستلام عهدة القبطان لشهر {self.current_month}/{self.current_year} بإجمالي سلف مصفاة ${total_cleared:,.2f}"
                )

                self.load_cash_data()
                QMessageBox.information(
                    self, "تم التسليم بنجاح",
                    f"تم توثيق محضر تسليم العهدة وتصفية ${total_cleared:,.2f} من سلف البحارة بنجاح!"
                )
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء تسليم العهدة: {e}")

    def print_report(self):
        """طباعة تقرير صندوق القبطان الرسمي بصيغة PDF"""
        try:
            pdf_path = ReportService.generate_master_cash_report(
                self.current_month,
                self.current_year,
                getattr(self, 'latest_transactions', []),
                getattr(self, 'latest_summary', {})
            )
            QMessageBox.information(
                self, "نجاح الطباعة 🖨️",
                f"تم توليد تقرير صندوق القبطان PDF بنجاح:\n\n{pdf_path}"
            )
            os.startfile(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الطباعة", f"تعذر إنشاء ملف PDF:\n{e}")

    def export_excel(self):
        """تصدير كشف الصندوق إلى ملف Excel (.xlsx) عبر ReportService"""
        try:
            default_name = f"MasterCash_{self.current_year}_{self.current_month:02d}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "حفظ كشف الصندوق Excel", default_name, "Excel Files (*.xlsx)"
            )
            if not file_path:
                return

            ReportService.export_master_cash_to_excel(
                getattr(self, 'latest_transactions', []),
                getattr(self, 'latest_summary', {}),
                self.current_month,
                self.current_year,
                file_path
            )
            QMessageBox.information(
                self, "نجاح التصدير 📊",
                f"تم تصدير كشف الصندوق إلى Excel بنجاح:\n\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر تصدير ملف Excel:\n{e}")
