# ui_audit_log.py
import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDateEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFrame, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QCursor
from audit_service import AuditService

class AuditLogWindow(QDialog):
    """
    نافذة عرض وتصفية وتصدير سجل التدقيق (Audit Trail)
    """
    def __init__(self, db_path: str = 'arn_ship_payroll.db', parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.service = AuditService(db_path)

        self.setWindowTitle("سجل التدقيق والمراقبة 📋 | ARN Audit Trail")
        self.resize(1150, 720)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QFrame#FilterCard {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px;
            }
            QLabel { color: #94a3b8; font-family: 'Cairo'; font-size: 10pt; font-weight: bold; }
            QLineEdit, QComboBox, QDateEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8fafc;
                font-family: 'Cairo';
                font-size: 10pt;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border-color: #3b82f6; }
            QPushButton {
                font-family: 'Cairo'; font-size: 10pt; font-weight: bold;
                border-radius: 6px; padding: 7px 16px;
            }
        """)

        self.init_ui()
        self.load_filters_data()
        self.refresh_logs()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. شريط العنوان
        header_layout = QHBoxLayout()
        title_lbl = QLabel("📋 سجل التدقيق والرقابة الأمنية (Audit Trail)")
        title_lbl.setFont(QFont("Cairo", 15, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38bdf8;")

        self.lbl_count = QLabel("إجمالي السجلات: 0")
        self.lbl_count.setStyleSheet("color: #10b981; font-weight: bold;")

        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_count)
        main_layout.addLayout(header_layout)

        # 2. بطاقة الفلاتر والبحث
        filter_card = QFrame()
        filter_card.setObjectName("FilterCard")
        f_layout = QVBoxLayout(filter_card)
        f_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("المستخدم:"))
        self.combo_user = QComboBox()
        self.combo_user.addItem("الكل")
        row1.addWidget(self.combo_user)

        row1.addWidget(QLabel("الإجراء:"))
        self.combo_action = QComboBox()
        self.combo_action.addItem("الكل")
        for act in ["CREATE", "UPDATE", "DELETE", "LOGIN", "LOGIN_FAILED", "CLOSE_MONTH", "HANDOVER", "UPDATE_WAGE", "ALERT_FIRED"]:
            self.combo_action.addItem(act)
        row1.addWidget(self.combo_action)

        self.chk_date = QCheckBox("تفعيل فلتر التاريخ:")
        self.chk_date.setStyleSheet("color: #f8fafc; font-weight: bold;")
        self.chk_date.toggled.connect(self.toggle_date_filter)
        row1.addWidget(self.chk_date)

        row1.addWidget(QLabel("من:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setEnabled(False)
        row1.addWidget(self.date_from)

        row1.addWidget(QLabel("إلى:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setEnabled(False)
        row1.addWidget(self.date_to)

        f_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("بحث في التفاصيل:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("اكتب نصاً للبحث في الوصف أو اسم الجدول...")
        self.txt_search.textChanged.connect(self.refresh_logs)
        row2.addWidget(self.txt_search)

        btn_filter = QPushButton("تطبيق الفلترة 🔍")
        btn_filter.setStyleSheet("background-color: #3b82f6; color: white;")
        btn_filter.clicked.connect(self.refresh_logs)
        row2.addWidget(btn_filter)

        btn_reset = QPushButton("إعادة تعيين 🧹")
        btn_reset.setStyleSheet("background-color: #475569; color: white;")
        btn_reset.clicked.connect(self.reset_filters)
        row2.addWidget(btn_reset)

        f_layout.addLayout(row2)
        main_layout.addWidget(filter_card)

        # 3. جدول السجلات
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "الوقت والتاريخ", "المستخدم", "الإجراء", "الجدول", "المعرف", "تفاصيل الحدث"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                gridline-color: #334155;
                color: #f8fafc;
                font-family: 'Cairo';
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #334155;
            }
        """)
        main_layout.addWidget(self.table)

        # 4. شريط الأزرار السفلي
        bottom_layout = QHBoxLayout()
        self.btn_export = QPushButton("تصدير تقرير PDF 📄")
        self.btn_export.setStyleSheet("background-color: #10b981; color: white;")
        self.btn_export.clicked.connect(self.export_pdf)

        btn_close = QPushButton("إغلاق ❌")
        btn_close.setStyleSheet("background-color: #334155; color: white;")
        btn_close.clicked.connect(self.close)

        bottom_layout.addWidget(self.btn_export)
        bottom_layout.addStretch()
        bottom_layout.addWidget(btn_close)
        main_layout.addLayout(bottom_layout)

    def toggle_date_filter(self, checked):
        self.date_from.setEnabled(checked)
        self.date_to.setEnabled(checked)
        self.refresh_logs()

    def load_filters_data(self):
        users = self.service.get_distinct_users()
        for u in users:
            self.combo_user.addItem(u)

    def reset_filters(self):
        self.combo_user.setCurrentIndex(0)
        self.combo_action.setCurrentIndex(0)
        self.chk_date.setChecked(False)
        self.txt_search.clear()
        self.refresh_logs()

    def refresh_logs(self):
        u_filter = self.combo_user.currentText()
        a_filter = self.combo_action.currentText()
        from_d = self.date_from.date().toString("yyyy-MM-dd") if self.chk_date.isChecked() else None
        to_d = self.date_to.date().toString("yyyy-MM-dd") if self.chk_date.isChecked() else None
        search = self.txt_search.text().strip() or None

        self.current_logs = self.service.get_logs(
            user_filter=u_filter,
            action_filter=a_filter,
            from_date=from_d,
            to_date=to_d,
            search_text=search,
            limit=500
        )

        self.table.setRowCount(len(self.current_logs))
        self.lbl_count.setText(f"إجمالي السجلات: {len(self.current_logs)}")

        for i, row in enumerate(self.current_logs):
            self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(str(row['timestamp'])))
            self.table.setItem(i, 2, QTableWidgetItem(str(row['username'])))

            act_item = QTableWidgetItem(str(row['action']))
            act = str(row['action']).upper()
            if act in ["CREATE", "LOGIN"]:
                act_item.setForeground(QColor("#10b981"))
            elif act in ["DELETE", "LOGIN_FAILED", "ALERT_FIRED"]:
                act_item.setForeground(QColor("#ef4444"))
            elif act in ["UPDATE", "UPDATE_WAGE", "HANDOVER"]:
                act_item.setForeground(QColor("#f59e0b"))
            elif act in ["CLOSE_MONTH"]:
                act_item.setForeground(QColor("#38bdf8"))

            self.table.setItem(i, 3, act_item)
            self.table.setItem(i, 4, QTableWidgetItem(str(row['table_name'] or '-')))
            self.table.setItem(i, 5, QTableWidgetItem(str(row['record_id'] or '-')))
            self.table.setItem(i, 6, QTableWidgetItem(str(row['description'])))

    def export_pdf(self):
        if not hasattr(self, 'current_logs') or not self.current_logs:
            QMessageBox.information(self, "تنبيه", "لا توجد سجلات لتصديرها.")
            return

        default_filename = f"Audit_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "حفظ تقرير سجل التدقيق", default_filename, "PDF Files (*.pdf)")
        if not file_path:
            return

        if self.service.export_pdf(file_path, self.current_logs):
            QMessageBox.information(self, "نجاح التصدير", f"تم تصدير تقرير سجل التدقيق بنجاح:\n{file_path}")
        else:
            QMessageBox.critical(self, "خطأ", "تعذر تصدير تقرير PDF.")
