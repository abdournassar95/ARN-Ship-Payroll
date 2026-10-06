# ui_crew_documents.py
"""
منظومة إدارة الشهادات والوثائق البحرية للطاقم - ARN Ship Payroll
تطوير وبرمجة: عبده رجب نصار - ARN Technology (c) 2026
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QLineEdit, QDateEdit, QFormLayout, QFrame,
    QComboBox, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QCursor

from audit_service import AuditService
from alert_service import AlertService


COMMON_DOC_TYPES = [
    "جواز سفر بحري (Seaman's Discharge Book)",
    "شهادة الأهلية والربانية (CoC - Certificate of Competency)",
    "شهادة الكشف الطبي البحري (Maritime Medical Fitness)",
    "شهادة السلامة البحرية الحتمية (STCW Basic Safety Training)",
    "شهادة مكافحة الحريق المتقدمة (Advanced Fire Fighting - AFF)",
    "شهادة الإسعافات الأولية والرعاية الطبية (Medical First Aid / Care)",
    "شهادة قوارب النجاة وسفن الإنقاذ (PSCRB - Survival Craft)",
    "شهادة أمن السفن والمرافق البحرية (Ship Security / DSD)",
    "جواز السفر الدولي (International Passport)",
    "شهادة التطعيم الدولي والحمى الصفراء (Yellow Fever Vaccination)",
    "تأشيرة دخول بحارة (Seafarer Visa)",
    "شهادة الرادار والأربا والخرائط الإلكترونية (GMDSS / ARPA / ECDIS)",
    "شهادة فحص السموم والمخدرات (Drug & Alcohol Screening)",
    "عقد العمل البحري المعتمد (Seafarer Employment Agreement)"
]


class AddDocDialog(QDialog):
    """نافذة إضافة شهادة أو وثيقة ملاحية جديدة"""
    def __init__(self, crew_list: Optional[List[tuple]] = None, default_crew_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة شهادة / وثيقة ملاحية جديدة 📜")
        self.setFixedSize(520, 420)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(12)

        # اختيار البحار
        self.crew_combo = None
        self.default_crew_id = default_crew_id
        if crew_list:
            self.crew_combo = QComboBox()
            for cid, cname, crank in crew_list:
                self.crew_combo.addItem(f"{cname} ({crank})", cid)
            if default_crew_id:
                idx = self.crew_combo.findData(default_crew_id)
                if idx >= 0:
                    self.crew_combo.setCurrentIndex(idx)
            form.addRow("اسم البحار *:", self.crew_combo)

        # نوع الشهادة مع اقتراحات شائعة وإمكانية الكتابة اليدوية
        self.doc_type_combo = QComboBox()
        self.doc_type_combo.setEditable(True)
        self.doc_type_combo.addItems(COMMON_DOC_TYPES)
        self.doc_type_combo.setPlaceholderText("اختر أو اكتب نوع الشهادة أو الوثيقة")
        self.doc_type_combo.lineEdit().setPlaceholderText("اختر أو اكتب نوع الشهادة أو الوثيقة")
        form.addRow("نوع الشهادة / الوثيقة *:", self.doc_type_combo)

        self.doc_num_e = QLineEdit()
        self.doc_num_e.setPlaceholderText("رقم الشهادة أو الوثيقة (اختياري)")
        form.addRow("رقم الوثيقة:", self.doc_num_e)

        self.issue_date_e = QDateEdit()
        self.issue_date_e.setCalendarPopup(True)
        self.issue_date_e.setDisplayFormat("yyyy-MM-dd")
        self.issue_date_e.setDate(QDate.currentDate())
        form.addRow("تاريخ الإصدار:", self.issue_date_e)

        self.expiry_date_e = QDateEdit()
        self.expiry_date_e.setCalendarPopup(True)
        self.expiry_date_e.setDisplayFormat("yyyy-MM-dd")
        self.expiry_date_e.setDate(QDate.currentDate().addYears(1))
        form.addRow("تاريخ الانتهاء *:", self.expiry_date_e)

        self.notes_e = QLineEdit()
        self.notes_e.setPlaceholderText("ملاحظات إضافية، جهة الإصدار، إلخ (اختياري)")
        form.addRow("ملاحظات:", self.notes_e)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("إلغاء")
        btn_cancel.setObjectName("Outline")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("حفظ الشهادة 💾")
        btn_save.setObjectName("Success")
        btn_save.clicked.connect(self.accept)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_data(self) -> Dict[str, Any]:
        cid = self.crew_combo.currentData() if self.crew_combo else self.default_crew_id
        return {
            'crew_id': cid,
            'doc_type': self.doc_type_combo.currentText().strip(),
            'doc_number': self.doc_num_e.text().strip(),
            'issue_date': self.issue_date_e.date().toString("yyyy-MM-dd"),
            'expiry_date': self.expiry_date_e.date().toString("yyyy-MM-dd"),
            'notes': self.notes_e.text().strip()
        }


class EditDocDialog(QDialog):
    """نافذة تعديل بيانات وتاريخ تجديد شهادة بحرية"""
    def __init__(self, doc_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("تعديل / تجديد الشهادة الملاحية ✏️")
        self.setFixedSize(500, 380)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(12)

        # نوع الشهادة
        self.doc_type_combo = QComboBox()
        self.doc_type_combo.setEditable(True)
        self.doc_type_combo.addItems(COMMON_DOC_TYPES)
        cur_type = doc_data.get('doc_type', '')
        if cur_type not in COMMON_DOC_TYPES and cur_type:
            self.doc_type_combo.insertItem(0, cur_type)
        self.doc_type_combo.setCurrentText(cur_type)
        form.addRow("نوع الشهادة / الوثيقة *:", self.doc_type_combo)

        # رقم الوثيقة
        self.doc_num_e = QLineEdit(doc_data.get('doc_number') or '')
        form.addRow("رقم الوثيقة:", self.doc_num_e)

        # تاريخ الإصدار
        self.issue_date_e = QDateEdit()
        self.issue_date_e.setCalendarPopup(True)
        self.issue_date_e.setDisplayFormat("yyyy-MM-dd")
        if doc_data.get('issue_date'):
            try:
                self.issue_date_e.setDate(QDate.fromString(doc_data['issue_date'][:10], "yyyy-MM-dd"))
            except Exception:
                self.issue_date_e.setDate(QDate.currentDate())
        form.addRow("تاريخ الإصدار:", self.issue_date_e)

        # تاريخ الانتهاء
        self.expiry_date_e = QDateEdit()
        self.expiry_date_e.setCalendarPopup(True)
        self.expiry_date_e.setDisplayFormat("yyyy-MM-dd")
        if doc_data.get('expiry_date'):
            try:
                self.expiry_date_e.setDate(QDate.fromString(doc_data['expiry_date'][:10], "yyyy-MM-dd"))
            except Exception:
                self.expiry_date_e.setDate(QDate.currentDate().addYears(1))
        form.addRow("تاريخ الانتهاء *:", self.expiry_date_e)

        # ملاحظات
        self.notes_e = QLineEdit(doc_data.get('notes') or '')
        form.addRow("ملاحظات:", self.notes_e)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("إلغاء")
        btn_cancel.setObjectName("Outline")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("حفظ التعديلات 💾")
        btn_save.setObjectName("Primary")
        btn_save.clicked.connect(self.accept)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_data(self) -> Dict[str, Any]:
        return {
            'doc_type': self.doc_type_combo.currentText().strip(),
            'doc_number': self.doc_num_e.text().strip(),
            'issue_date': self.issue_date_e.date().toString("yyyy-MM-dd"),
            'expiry_date': self.expiry_date_e.date().toString("yyyy-MM-dd"),
            'notes': self.notes_e.text().strip()
        }


class CrewDocumentsWidget(QWidget):
    """ويدجت عرض وإدارة وثائق وشهادات بحار محدد"""
    def __init__(self, crew_id: int, db_path: str = 'arn_ship_payroll.db', parent=None):
        super().__init__(parent)
        self.crew_id = crew_id
        self.db_path = db_path
        self.init_ui()
        self.load_documents()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # شريط أزرار التحكم
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_add = QPushButton("➕ إضافة شهادة جديدة")
        self.btn_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #10b981; color: white; font-family: 'Cairo';
                font-weight: bold; border-radius: 6px; padding: 6px 14px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_add.clicked.connect(self.add_document)

        self.btn_edit = QPushButton("✏️ تعديل الشهادة")
        self.btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #0284c7; color: white; font-family: 'Cairo';
                font-weight: bold; border-radius: 6px; padding: 6px 14px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_edit.clicked.connect(self.edit_document)

        self.btn_delete = QPushButton("🗑️ حذف الشهادة")
        self.btn_delete.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #ef4444; color: white; font-family: 'Cairo';
                font-weight: bold; border-radius: 6px; padding: 6px 14px;
            }
            QPushButton:hover { background-color: #dc2626; }
        """)
        self.btn_delete.clicked.connect(self.delete_document)

        btn_bar.addWidget(self.btn_add)
        btn_bar.addWidget(self.btn_edit)
        btn_bar.addWidget(self.btn_delete)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # جدول الشهادات
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "نوع الشهادة", "رقم الوثيقة", "تاريخ الإصدار", "تاريخ الانتهاء", "الأيام المتبقية", "ملاحظات"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
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
        layout.addWidget(self.table)

    def load_documents(self):
        self.table.setRowCount(0)
        if not self.crew_id:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("""
                    SELECT id, doc_type, doc_number, issue_date, expiry_date, notes 
                    FROM crew_documents WHERE crew_id = ? ORDER BY expiry_date ASC
                """, (self.crew_id,))
                rows = c.fetchall()

            self.table.setRowCount(len(rows))
            today = datetime.now().date()

            for i, r in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(r['id'])))
                self.table.setItem(i, 1, QTableWidgetItem(str(r['doc_type'])))
                self.table.setItem(i, 2, QTableWidgetItem(str(r['doc_number'] or '-')))
                self.table.setItem(i, 3, QTableWidgetItem(str(r['issue_date'] or '-')))
                
                exp_item = QTableWidgetItem(str(r['expiry_date']))
                days_item = QTableWidgetItem("-")
                
                try:
                    exp_dt = datetime.strptime(r['expiry_date'][:10], "%Y-%m-%d").date()
                    days_left = (exp_dt - today).days
                    days_item.setText(f"{days_left} يوم" if days_left >= 0 else f"منتهية منذ {-days_left} يوم")
                    
                    if days_left < 0:
                        exp_item.setForeground(QColor("#ef4444"))
                        days_item.setForeground(QColor("#ef4444"))
                    elif days_left <= 60:
                        exp_item.setForeground(QColor("#f59e0b"))
                        days_item.setForeground(QColor("#f59e0b"))
                    else:
                        exp_item.setForeground(QColor("#10b981"))
                        days_item.setForeground(QColor("#10b981"))
                except Exception:
                    pass

                self.table.setItem(i, 4, exp_item)
                self.table.setItem(i, 5, days_item)
                self.table.setItem(i, 6, QTableWidgetItem(str(r['notes'] or '-')))

        except Exception as e:
            print(f"⚠️ خطأ تحميل شهادات البحار: {e}")

    def add_document(self):
        if not self.crew_id:
            QMessageBox.warning(self, "تنبيه", "يرجى حفظ بيانات البحار أولاً قبل إضافة شهاداته.")
            return

        dlg = AddDocDialog(default_crew_id=self.crew_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data['doc_type']:
                QMessageBox.warning(self, "تنبيه", "يرجى إدخال نوع الشهادة.")
                return

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO crew_documents (crew_id, doc_type, doc_number, issue_date, expiry_date, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (self.crew_id, data['doc_type'], data['doc_number'], data['issue_date'], data['expiry_date'], data['notes']))
                    conn.commit()

                AuditService(self.db_path).log(1, "ADMIN", "CREATE", "crew_documents", self.crew_id, f"إضافة شهادة {data['doc_type']} للبحار رقم {self.crew_id}")
                AlertService(self.db_path).check_cert_expiry()
                self.load_documents()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر حفظ الشهادة: {e}")

    def edit_document(self):
        cur_row = self.table.currentRow()
        if cur_row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد شهادة لتعديلها.")
            return

        doc_id = int(self.table.item(cur_row, 0).text())
        doc_type = self.table.item(cur_row, 1).text()
        doc_num = self.table.item(cur_row, 2).text()
        issue_d = self.table.item(cur_row, 3).text()
        expiry_d = self.table.item(cur_row, 4).text()
        notes = self.table.item(cur_row, 6).text()

        dlg = EditDocDialog({
            'doc_type': doc_type,
            'doc_number': "" if doc_num == "-" else doc_num,
            'issue_date': issue_d,
            'expiry_date': expiry_d,
            'notes': "" if notes == "-" else notes
        }, parent=self)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE crew_documents 
                        SET doc_type = ?, doc_number = ?, issue_date = ?, expiry_date = ?, notes = ?
                        WHERE id = ?
                    """, (data['doc_type'], data['doc_number'], data['issue_date'], data['expiry_date'], data['notes'], doc_id))
                    conn.commit()

                AuditService(self.db_path).log(1, "ADMIN", "UPDATE", "crew_documents", doc_id, f"تعديل شهادة {data['doc_type']} رقم {doc_id}")
                AlertService(self.db_path).check_cert_expiry()
                self.load_documents()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر تحديث الشهادة: {e}")

    def delete_document(self):
        cur_row = self.table.currentRow()
        if cur_row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى تحديد شهادة لحذفها.")
            return

        doc_id = int(self.table.item(cur_row, 0).text())
        doc_type = self.table.item(cur_row, 1).text()

        confirm = QMessageBox.question(
            self, "تأكيد الحذف", f"هل أنت متأكد من حذف شهادة ({doc_type})؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM crew_documents WHERE id = ?", (doc_id,))
                    conn.commit()

                AuditService(self.db_path).log(1, "ADMIN", "DELETE", "crew_documents", doc_id, f"حذف شهادة {doc_type} رقم {doc_id}")
                AlertService(self.db_path).check_cert_expiry()
                self.load_documents()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر الحذف: {e}")


class CrewDocumentsDialog(QDialog):
    """نافذة منبثقة مستقلة لعرض وإدارة شهادات ووثائق بحار محدد"""
    def __init__(self, crew_id: int, crew_name: str = "", db_path: str = 'arn_ship_payroll.db', parent=None):
        super().__init__(parent)
        self.crew_id = crew_id
        self.crew_name = crew_name
        self.db_path = db_path

        self.setWindowTitle(f"وثائق وشهادات البحار: {crew_name or crew_id} 📜")
        self.resize(850, 560)
        self.setMinimumSize(700, 460)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_lbl = QLabel(f"📜 سجل الشهادات والوثائق الملاحية: {crew_name}")
        title_lbl.setFont(QFont("Cairo", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38bdf8; margin-bottom: 4px;")
        layout.addWidget(title_lbl)

        self.doc_widget = CrewDocumentsWidget(crew_id, db_path, parent=self)
        layout.addWidget(self.doc_widget)

        btn_layout = QHBoxLayout()
        btn_close = QPushButton("إغلاق")
        btn_close.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #334155; color: white; border-radius: 6px; padding: 7px 24px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)


class FleetDocumentsDialog(QDialog):
    """
    المنظومة المركزية الشاملة لإدارة ومتابعة الشهادات والوثائق البحرية لكافة أفراد الطاقم
    (Crew Maritime Documents & STCW Compliance Console)
    """
    def __init__(self, default_crew_id: Optional[int] = None, db_path: str = 'arn_ship_payroll.db', parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.default_crew_id = default_crew_id
        self.all_docs_cache: List[Dict[str, Any]] = []

        self.setWindowTitle("📜 منظومة الشهادات والوثائق والخدمة البحرية للطاقم - ARN Maritime Docs")
        self.resize(1180, 800)
        self.setMinimumSize(900, 640)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.init_ui()
        self.load_crew_list()
        self.load_fleet_documents()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 22, 24, 20)
        main_layout.setSpacing(18)

        # 1. الترويسة الرئيسية
        header_layout = QHBoxLayout()
        header_title = QLabel("⚓ منظومة إدارة الوثائق والشهادات البحرية وتواريخ الصلاحية")
        header_title.setFont(QFont("Cairo", 15, QFont.Weight.Bold))
        header_title.setWordWrap(True)
        header_title.setStyleSheet("color: #38bdf8;")

        sub_title = QLabel("نظام الرقابة والتوافق الملاحي (STCW / Flag State / Port State Control)")
        sub_title.setFont(QFont("Cairo", 9))
        sub_title.setStyleSheet("color: #94a3b8;")

        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(4)
        header_vbox.addWidget(header_title)
        header_vbox.addWidget(sub_title)
        header_layout.addLayout(header_vbox)
        header_layout.addStretch()

        # أزرار الإجراءات العلوية
        self.btn_add_doc = QPushButton("➕ إضافة وثيقة جديدة")
        self.btn_add_doc.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        self.btn_add_doc.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add_doc.setObjectName("Success")
        self.btn_add_doc.setMinimumHeight(42)
        self.btn_add_doc.clicked.connect(self.add_new_document)

        self.btn_print_report = QPushButton("🖨️ طباعة تقرير الشهادات (PDF)")
        self.btn_print_report.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        self.btn_print_report.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_print_report.setObjectName("Primary")
        self.btn_print_report.setMinimumHeight(42)
        self.btn_print_report.clicked.connect(self.print_documents_report)

        # Keep actions on a separate row so long Arabic titles never compete for width.
        main_layout.addLayout(header_layout)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.addWidget(self.btn_add_doc)
        actions_layout.addWidget(self.btn_print_report)
        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # 2. كروت الإحصائيات (KPI Cards)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)

        self.kpi_total = self._create_kpi_card("📄 إجمالي الشهادات", "0", "#38bdf8")
        self.kpi_valid = self._create_kpi_card("✅ شهادات سارية", "0", "#10b981")
        self.kpi_expiring = self._create_kpi_card("⚠️ تنتهي قريباً (خلال 60 يوماً)", "0", "#f59e0b")
        self.kpi_expired = self._create_kpi_card("🚨 منتهية الصلاحية", "0", "#ef4444")

        kpi_layout.addWidget(self.kpi_total['frame'], 1)
        kpi_layout.addWidget(self.kpi_valid['frame'], 1)
        kpi_layout.addWidget(self.kpi_expiring['frame'], 1)
        kpi_layout.addWidget(self.kpi_expired['frame'], 1)
        main_layout.addLayout(kpi_layout)

        # 3. شريط الفلاتر والبحث
        filter_frame = QFrame()
        filter_frame.setObjectName("FleetFilterCard")
        filter_layout = QVBoxLayout(filter_frame)
        filter_layout.setContentsMargins(14, 10, 14, 10)
        filter_layout.setSpacing(8)
        fields_row = QHBoxLayout()
        fields_row.setSpacing(10)
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        lbl_crew = QLabel("البحار:")
        lbl_crew.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        lbl_crew.setStyleSheet("color: #94a3b8;")
        self.combo_crew_filter = QComboBox()
        self.combo_crew_filter.setMinimumWidth(220)
        self.combo_crew_filter.currentIndexChanged.connect(self.apply_filters)

        lbl_status = QLabel("حالة الصلاحية:")
        lbl_status.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        lbl_status.setStyleSheet("color: #94a3b8;")
        self.combo_status_filter = QComboBox()
        self.combo_status_filter.addItems(["جميع الحالات 📋", "⚠️ تنتهي قريباً (خلال 60 يوماً)", "🚨 منتهية الصلاحية", "✅ سارية الصلاحية"])
        self.combo_status_filter.currentIndexChanged.connect(self.apply_filters)

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("🔍 بحث سريع (اسم البحار، نوع الشهادة، رقم الوثيقة...)")
        self.search_entry.setClearButtonEnabled(True)
        self.search_entry.setMinimumHeight(40)
        self.search_entry.textChanged.connect(self.apply_filters)

        btn_refresh = QPushButton("🔄 تحديث")
        btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_refresh.setObjectName("Outline")
        btn_refresh.setMinimumHeight(40)
        btn_refresh.clicked.connect(self.load_fleet_documents)

        fields_row.addWidget(lbl_crew)
        fields_row.addWidget(self.combo_crew_filter, 1)
        fields_row.addWidget(lbl_status)
        fields_row.addWidget(self.combo_status_filter, 1)
        search_row.addWidget(self.search_entry, 1)
        search_row.addWidget(btn_refresh)
        filter_layout.addLayout(fields_row)
        filter_layout.addLayout(search_row)
        main_layout.addWidget(filter_frame)

        # 4. جدول الشهادات المركزي
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "م", "اسم البحار", "الرتبة", "نوع الشهادة / الوثيقة", "رقم الوثيقة",
            "تاريخ الإصدار", "تاريخ الانتهاء", "الأيام المتبقية", "الحالة", "الإجراءات"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column, width in enumerate((45, 170, 100, 205, 135, 125, 125, 110, 105, 170)):
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(200)
        main_layout.addWidget(self.table, 1)

        # 5. زر الإغلاق السفلي
        footer_layout = QHBoxLayout()
        self.lbl_count = QLabel("إجمالي السجلات المعروضة: 0")
        self.lbl_count.setStyleSheet("color: #64748b; font-size: 10pt; font-weight: bold;")
        footer_layout.addWidget(self.lbl_count)
        footer_layout.addStretch()

        btn_close = QPushButton("إغلاق النافذة")
        btn_close.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.setObjectName("Outline")
        btn_close.setMinimumHeight(40)
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)
        main_layout.addLayout(footer_layout)

    def _create_kpi_card(self, title: str, val: str, color_hex: str) -> Dict[str, Any]:
        frame = QFrame()
        # No stylesheet on the parent frame: Qt can propagate it to child
        # QLabel (which also inherits QFrame), drawing nested borders.
        frame.setObjectName({
            "#38bdf8": "FleetKpiTotal",
            "#10b981": "FleetKpiValid",
            "#f59e0b": "FleetKpiSoon",
            "#ef4444": "FleetKpiExpired",
        }.get(color_hex, "FleetKpiTotal"))
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        frame.setMinimumHeight(98)

        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Cairo", 9, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #94a3b8; border: none; background: transparent; padding: 0;")
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_lbl.setWordWrap(True)
        t_lbl.setMinimumHeight(36)

        v_lbl = QLabel(val)
        v_lbl.setFont(QFont("Cairo", 16, QFont.Weight.Bold))
        v_lbl.setStyleSheet(f"color: {color_hex}; border: none; background: transparent; padding: 0;")
        v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        return {'frame': frame, 'label': v_lbl}

    def load_crew_list(self):
        """تحميل قائمة أفراد الطاقم في صندوق الاختيار"""
        self.combo_crew_filter.blockSignals(True)
        self.combo_crew_filter.clear()
        self.combo_crew_filter.addItem("🌊 كافة أفراد الطاقم (عرض الأسطول)", None)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT No, Name, Rank FROM CrewWages ORDER BY No ASC")
                for r in c.fetchall():
                    self.combo_crew_filter.addItem(f"{r['Name']} ({r['Rank']})", r['No'])

            if self.default_crew_id:
                idx = self.combo_crew_filter.findData(self.default_crew_id)
                if idx >= 0:
                    self.combo_crew_filter.setCurrentIndex(idx)
        except Exception as e:
            print(f"⚠️ خطأ تحميل قائمة البحارة: {e}")
        finally:
            self.combo_crew_filter.blockSignals(False)

    def load_fleet_documents(self):
        """استرجاع كافة شهادات ووثائق الطاقم وتحديث بطاقات المؤشرات والجدول"""
        self.all_docs_cache.clear()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("""
                    SELECT d.id, d.crew_id, d.doc_type, d.doc_number, d.issue_date, d.expiry_date, d.notes,
                           c.Name as crew_name, c.Rank as crew_rank
                    FROM crew_documents d
                    JOIN CrewWages c ON d.crew_id = c.No
                    ORDER BY d.expiry_date ASC
                """)
                for row in c.fetchall():
                    self.all_docs_cache.append(dict(row))
        except Exception as e:
            print(f"⚠️ خطأ تحميل وثائق الأسطول: {e}")

        # تحديث مؤشرات KPIs
        today = datetime.now().date()
        total_count = len(self.all_docs_cache)
        valid_count = 0
        expiring_count = 0
        expired_count = 0

        for doc in self.all_docs_cache:
            try:
                exp_dt = datetime.strptime(doc['expiry_date'][:10], "%Y-%m-%d").date()
                diff = (exp_dt - today).days
                if diff < 0:
                    expired_count += 1
                elif diff <= 60:
                    expiring_count += 1
                else:
                    valid_count += 1
            except Exception:
                valid_count += 1

        self.kpi_total['label'].setText(str(total_count))
        self.kpi_valid['label'].setText(str(valid_count))
        self.kpi_expiring['label'].setText(str(expiring_count))
        self.kpi_expired['label'].setText(str(expired_count))

        self.apply_filters()

    def apply_filters(self):
        """تطبيق فلاتر البحار وحالة الصلاحية وحقل البحث النصي على الجدول"""
        selected_crew_id = self.combo_crew_filter.currentData()
        status_mode = self.combo_status_filter.currentIndex() # 0: all, 1: expiring <= 60, 2: expired < 0, 3: valid > 60
        search_query = self.search_entry.text().strip().lower()

        today = datetime.now().date()
        filtered = []

        for doc in self.all_docs_cache:
            # 1. فلتر البحار
            if selected_crew_id is not None and doc['crew_id'] != selected_crew_id:
                continue

            # 2. حساب الأيام وحالة الصلاحية
            days_left = 999
            try:
                exp_dt = datetime.strptime(doc['expiry_date'][:10], "%Y-%m-%d").date()
                days_left = (exp_dt - today).days
            except Exception:
                pass

            # فلتر الحالة
            if status_mode == 1 and not (0 <= days_left <= 60):
                continue
            elif status_mode == 2 and not (days_left < 0):
                continue
            elif status_mode == 3 and not (days_left > 60):
                continue

            # 3. فلتر البحث النصي
            if search_query:
                combined = f"{doc.get('crew_name', '')} {doc.get('crew_rank', '')} {doc.get('doc_type', '')} {doc.get('doc_number', '')} {doc.get('notes', '')}".lower()
                if search_query not in combined:
                    continue

            doc_copy = dict(doc)
            doc_copy['days_left'] = days_left
            filtered.append(doc_copy)

        self._populate_table(filtered)

    def _populate_table(self, docs_list: List[Dict[str, Any]]):
        self.table.setRowCount(len(docs_list))
        self.lbl_count.setText(f"إجمالي السجلات المعروضة: {len(docs_list)}")

        for i, d in enumerate(docs_list):
            self.table.setRowHeight(i, 44)

            # م
            it_id = QTableWidgetItem(str(d['id']))
            it_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_id.setForeground(QColor("#64748b"))
            self.table.setItem(i, 0, it_id)

            # اسم البحار
            it_name = QTableWidgetItem(str(d.get('crew_name', '')))
            it_name.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            it_name.setFont(QFont("Cairo", 10, QFont.Weight.Bold))
            it_name.setForeground(QColor("#f8fafc"))
            self.table.setItem(i, 1, it_name)

            # الرتبة
            it_rank = QTableWidgetItem(str(d.get('crew_rank', '')))
            it_rank.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_rank.setForeground(QColor("#38bdf8"))
            self.table.setItem(i, 2, it_rank)

            # نوع الشهادة
            it_type = QTableWidgetItem(str(d.get('doc_type', '')))
            it_type.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            it_type.setForeground(QColor("#e2e8f0"))
            self.table.setItem(i, 3, it_type)

            # رقم الوثيقة
            it_num = QTableWidgetItem(str(d.get('doc_number') or '-'))
            it_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_num.setForeground(QColor("#cbd5e1"))
            self.table.setItem(i, 4, it_num)

            # تاريخ الإصدار
            it_iss = QTableWidgetItem(str(d.get('issue_date') or '-'))
            it_iss.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_iss.setForeground(QColor("#94a3b8"))
            self.table.setItem(i, 5, it_iss)

            # تاريخ الانتهاء
            it_exp = QTableWidgetItem(str(d.get('expiry_date') or '-'))
            it_exp.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_exp.setFont(QFont("Cairo", 10, QFont.Weight.Bold))

            # الأيام المتبقية والحالة
            days_left = d.get('days_left', 999)
            if days_left < 0:
                it_exp.setForeground(QColor("#ef4444"))
                it_days = QTableWidgetItem(f"منتهية ({abs(days_left)} يوم)")
                it_days.setForeground(QColor("#ef4444"))
                status_badge = "🚨 منتهية الصلاحية"
                badge_color = "#ef4444"
            elif days_left <= 60:
                it_exp.setForeground(QColor("#f59e0b"))
                it_days = QTableWidgetItem(f"{days_left} يوم")
                it_days.setForeground(QColor("#f59e0b"))
                status_badge = "⚠️ تنتهي قريباً"
                badge_color = "#f59e0b"
            else:
                it_exp.setForeground(QColor("#10b981"))
                it_days = QTableWidgetItem(f"{days_left} يوم")
                it_days.setForeground(QColor("#10b981"))
                status_badge = "✅ سارية الصلاحية"
                badge_color = "#10b981"

            it_days.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 6, it_exp)
            self.table.setItem(i, 7, it_days)

            it_status = QTableWidgetItem(status_badge)
            it_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_status.setFont(QFont("Cairo", 9, QFont.Weight.Bold))
            it_status.setForeground(QColor(badge_color))
            self.table.setItem(i, 8, it_status)

            # أزرار الإجراءات
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_e = QPushButton("✏️")
            btn_e.setToolTip("تعديل / تجديد الشهادة")
            btn_e.setStyleSheet("""
                QPushButton {
                    background-color: #0c4a6e; color: #38bdf8; border: 1px solid #0284c7;
                    border-radius: 4px; padding: 3px 8px; font-weight: bold;
                }
                QPushButton:hover { background-color: #0284c7; color: white; }
            """)
            btn_e.clicked.connect(lambda _, doc_data=d: self.edit_specific_document(doc_data))

            btn_d = QPushButton("🗑️")
            btn_d.setToolTip("حذف الشهادة")
            btn_d.setStyleSheet("""
                QPushButton {
                    background-color: #4c0519; color: #f43f5e; border: 1px solid #e11d48;
                    border-radius: 4px; padding: 3px 8px; font-weight: bold;
                }
                QPushButton:hover { background-color: #e11d48; color: white; }
            """)
            btn_d.clicked.connect(lambda _, doc_id=d['id'], doc_name=d['doc_type'], c_name=d.get('crew_name', ''): self.delete_specific_document(doc_id, doc_name, c_name))

            act_layout.addWidget(btn_e)
            act_layout.addWidget(btn_d)
            self.table.setCellWidget(i, 9, act_widget)

    def add_new_document(self):
        """إضافة شهادة جديدة مع دعم اختيار البحار ونوع الشهادة"""
        crew_tuples = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT No, Name, Rank FROM CrewWages ORDER BY No ASC")
                for r in c.fetchall():
                    crew_tuples.append((r['No'], r['Name'], r['Rank']))
        except Exception:
            pass

        if not crew_tuples:
            QMessageBox.warning(self, "تنبيه", "لا يوجد أي بحارة مسجلين في النظام بعد. يرجى إضافة بحار أولاً.")
            return

        def_cid = self.combo_crew_filter.currentData() or (crew_tuples[0][0] if crew_tuples else None)
        dlg = AddDocDialog(crew_list=crew_tuples, default_crew_id=def_cid, parent=self)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data['crew_id']:
                QMessageBox.warning(self, "تنبيه", "يرجى تحديد البحار.")
                return
            if not data['doc_type']:
                QMessageBox.warning(self, "تنبيه", "يرجى إدخال أو اختيار نوع الشهادة.")
                return

            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO crew_documents (crew_id, doc_type, doc_number, issue_date, expiry_date, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (data['crew_id'], data['doc_type'], data['doc_number'], data['issue_date'], data['expiry_date'], data['notes']))
                    conn.commit()

                AuditService(self.db_path).log(1, "ADMIN", "CREATE", "crew_documents", data['crew_id'], f"إضافة شهادة {data['doc_type']} للبحار رقم {data['crew_id']}")
                AlertService(self.db_path).check_cert_expiry()
                self.load_fleet_documents()
                QMessageBox.information(self, "نجاح", f"تمت إضافة وثيقة ({data['doc_type']}) بنجاح.")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر حفظ الشهادة: {e}")

    def edit_specific_document(self, doc_data: Dict[str, Any]):
        dlg = EditDocDialog(doc_data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE crew_documents 
                        SET doc_type = ?, doc_number = ?, issue_date = ?, expiry_date = ?, notes = ?
                        WHERE id = ?
                    """, (data['doc_type'], data['doc_number'], data['issue_date'], data['expiry_date'], data['notes'], doc_data['id']))
                    conn.commit()

                AuditService(self.db_path).log(1, "ADMIN", "UPDATE", "crew_documents", doc_data['id'], f"تعديل وتجديد شهادة {data['doc_type']} رقم {doc_data['id']}")
                AlertService(self.db_path).check_cert_expiry()
                self.load_fleet_documents()
                QMessageBox.information(self, "نجاح", f"تم تحديث بيانات الشهادة بنجاح.")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر تحديث الشهادة: {e}")

    def delete_specific_document(self, doc_id: int, doc_name: str, crew_name: str):
        confirm = QMessageBox.question(
            self, "تأكيد الحذف", f"هل أنت متأكد من حذف وثيقة ({doc_name}) الخاصة بالبحار ({crew_name})؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM crew_documents WHERE id = ?", (doc_id,))
                    conn.commit()

                AuditService(self.db_path).log(1, "ADMIN", "DELETE", "crew_documents", doc_id, f"حذف شهادة {doc_name} رقم {doc_id}")
                AlertService(self.db_path).check_cert_expiry()
                self.load_fleet_documents()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر الحذف: {e}")

    def print_documents_report(self):
        """إنشاء وطباعة تقرير فحص الشهادات والوثائق بصيغة PDF"""
        if not self.all_docs_cache:
            QMessageBox.warning(self, "تنبيه", "لا توجد شهادات أو وثائق مسجلة لطباعة التقرير.")
            return

        try:
            from report_service import ReportService
            crew_filter_name = self.combo_crew_filter.currentText()
            pdf_path = ReportService.generate_documents_report(self.all_docs_cache, filter_title=crew_filter_name)
            os.startfile(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الطباعة", f"فشل إنشاء تقرير الوثائق الملاحية:\n{e}")
