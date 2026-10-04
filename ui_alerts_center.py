# ui_alerts_center.py
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QFileDialog, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QCursor
from alert_service import AlertService
from ui_alerts_rules import AlertRulesDialog

class AlertsCenterWindow(QDialog):
    """
    نافذة مركز التنبيهات الذكية وإدارتها
    """
    def __init__(self, db_path: str = 'arn_ship_payroll.db', current_user_id: int = 1, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.current_user_id = current_user_id
        self.service = AlertService(db_path)

        self.setWindowTitle("مركز التنبيهات الذكية 🔔 | ARN Alerts Center")
        self.resize(1150, 720)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QFrame#StatCard {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px 16px;
            }
            QLabel { color: #e2e8f0; font-family: 'Cairo'; }
            QPushButton {
                font-family: 'Cairo'; font-size: 10pt; font-weight: bold;
                border-radius: 6px; padding: 7px 16px;
            }
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

        self.init_ui()
        self.refresh_alerts()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. شريط العنوان
        header_layout = QHBoxLayout()
        title_lbl = QLabel("🔔 مركز التنبيهات الذكية والإنذار المبكر")
        title_lbl.setFont(QFont("Cairo", 15, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38bdf8;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        btn_rules = QPushButton("إدارة القواعد ⚙️")
        btn_rules.setStyleSheet("background-color: #334155; color: white;")
        btn_rules.clicked.connect(self.open_rules_dialog)
        header_layout.addWidget(btn_rules)

        btn_refresh = QPushButton("تحديث 🔄")
        btn_refresh.setStyleSheet("background-color: #3b82f6; color: white;")
        btn_refresh.clicked.connect(self.refresh_alerts)
        header_layout.addWidget(btn_refresh)

        main_layout.addLayout(header_layout)

        # 2. بطاقات الإحصائيات
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        self.card_crit = self.create_stat_card("🔴 تنبيهات حرجة", "0", "#ef4444")
        self.card_warn = self.create_stat_card("🟡 تحذيرات", "0", "#f59e0b")
        self.card_info = self.create_stat_card("🔵 معلومات", "0", "#38bdf8")
        self.card_unread = self.create_stat_card("📩 غير مقروءة", "0", "#10b981")

        stats_layout.addWidget(self.card_crit)
        stats_layout.addWidget(self.card_warn)
        stats_layout.addWidget(self.card_info)
        stats_layout.addWidget(self.card_unread)
        main_layout.addLayout(stats_layout)

        # 3. أزرار الفلترة
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("تصفية بحسب الخطورة:"))
        
        self.filter_buttons = {}
        for key, text in [("ALL", "الكل"), ("CRITICAL", "حرج 🔴"), ("WARNING", "تحذير 🟡"), ("INFO", "معلومات 🔵"), ("RESOLVED", "المحلولة سابقاً")]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if key == "ALL":
                btn.setChecked(True)
                btn.setStyleSheet("background-color: #3b82f6; color: white;")
            else:
                btn.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;")
            btn.clicked.connect(lambda checked, k=key: self.set_filter(k))
            self.filter_buttons[key] = btn
            filter_bar.addWidget(btn)

        filter_bar.addStretch()

        self.btn_mark_all = QPushButton("تعليم الكل كمقروء ✓")
        self.btn_mark_all.setStyleSheet("background-color: #475569; color: white; font-size: 9pt;")
        self.btn_mark_all.clicked.connect(self.mark_all_read)
        filter_bar.addWidget(self.btn_mark_all)

        main_layout.addLayout(filter_bar)

        # 4. جدول التنبيهات
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "الوقت", "الخطورة", "الهدف", "نص التنبيه", "الحالة", "إجراء"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.table)

        # 5. الشريط السفلي
        bottom_layout = QHBoxLayout()
        btn_export = QPushButton("تصدير تقرير PDF 📄")
        btn_export.setStyleSheet("background-color: #10b981; color: white;")
        btn_export.clicked.connect(self.export_pdf)

        btn_close = QPushButton("إغلاق ❌")
        btn_close.setStyleSheet("background-color: #334155; color: white;")
        btn_close.clicked.connect(self.close)

        bottom_layout.addWidget(btn_export)
        bottom_layout.addStretch()
        bottom_layout.addWidget(btn_close)
        main_layout.addLayout(bottom_layout)

        self.current_filter = "ALL"

    def create_stat_card(self, title, val, color):
        frame = QFrame()
        frame.setObjectName("StatCard")
        l = QVBoxLayout(frame)
        l.setContentsMargins(10, 8, 10, 8)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"color: {color}; font-size: 10pt; font-weight: bold;")
        lbl_v = QLabel(val)
        lbl_v.setFont(QFont("Cairo", 16, QFont.Weight.Bold))
        lbl_v.setStyleSheet("color: white;")
        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        frame.lbl_val = lbl_v
        return frame

    def set_filter(self, filter_key):
        self.current_filter = filter_key
        for k, b in self.filter_buttons.items():
            if k == filter_key:
                b.setChecked(True)
                b.setStyleSheet("background-color: #3b82f6; color: white;")
            else:
                b.setChecked(False)
                b.setStyleSheet("background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;")
        self.refresh_alerts()

    def open_rules_dialog(self):
        dlg = AlertRulesDialog(self.db_path, self)
        dlg.exec()
        self.refresh_alerts()

    def refresh_alerts(self):
        # 1. تحديث بطاقات الإحصاء
        counts = self.service.get_alerts_counts()
        self.card_crit.lbl_val.setText(str(counts['critical']))
        self.card_warn.lbl_val.setText(str(counts['warning']))
        self.card_info.lbl_val.setText(str(counts['info']))
        self.card_unread.lbl_val.setText(str(counts['unread']))

        # 2. جلب التنبيهات بحسب الفلتر
        if self.current_filter == "RESOLVED":
            self.current_alerts = self.service.get_alerts(only_unresolved=False, limit=200)
            self.current_alerts = [a for a in self.current_alerts if a.get('is_resolved')]
        else:
            sev = None if self.current_filter == "ALL" else self.current_filter
            self.current_alerts = self.service.get_alerts(severity=sev, only_unresolved=True, limit=200)

        self.table.setRowCount(len(self.current_alerts))

        for i, a in enumerate(self.current_alerts):
            self.table.setItem(i, 0, QTableWidgetItem(str(a['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(str(a['triggered_at'])[:16]))

            # الخطورة
            sev_item = QTableWidgetItem(a['severity'])
            sev = a['severity'].upper()
            if sev == "CRITICAL":
                sev_item.setForeground(QColor("#ef4444"))
            elif sev == "WARNING":
                sev_item.setForeground(QColor("#f59e0b"))
            else:
                sev_item.setForeground(QColor("#38bdf8"))
            self.table.setItem(i, 2, sev_item)

            self.table.setItem(i, 3, QTableWidgetItem(str(a.get('target_name') or '-')))
            self.table.setItem(i, 4, QTableWidgetItem(str(a['message'])))

            # الحالة
            status_str = "محلول ✅" if a.get('is_resolved') else ("مقروء 👀" if a.get('is_read') else "جديد 🔔")
            self.table.setItem(i, 5, QTableWidgetItem(status_str))

            # ويدجت الإجراء (زر الحل)
            if not a.get('is_resolved'):
                btn_resolve = QPushButton("حل ✅")
                btn_resolve.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn_resolve.setStyleSheet("background-color: #10b981; color: white; padding: 3px 8px; font-size: 9pt;")
                btn_resolve.clicked.connect(lambda ch, aid=a['id']: self.resolve_alert(aid))
                self.table.setCellWidget(i, 6, btn_resolve)
            else:
                lbl_done = QLabel("مكتمل")
                lbl_done.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_done.setStyleSheet("color: #64748b; font-size: 9pt;")
                self.table.setCellWidget(i, 6, lbl_done)

    def resolve_alert(self, alert_id: int):
        if self.service.resolve_alert(alert_id, self.current_user_id):
            self.refresh_alerts()

    def mark_all_read(self):
        if self.service.mark_all_as_read():
            self.refresh_alerts()

    def export_pdf(self):
        if not hasattr(self, 'current_alerts') or not self.current_alerts:
            QMessageBox.information(self, "تنبيه", "لا توجد تنبيهات لتصديرها.")
            return

        default_filename = f"Alerts_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "حفظ تقرير التنبيهات", default_filename, "PDF Files (*.pdf)")
        if not file_path:
            return

        if self.service.export_pdf(file_path, self.current_alerts):
            QMessageBox.information(self, "نجاح التصدير", f"تم تصدير تقرير التنبيهات بنجاح:\n{file_path}")
        else:
            QMessageBox.critical(self, "خطأ", "تعذر تصدير تقرير PDF.")
