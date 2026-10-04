# ui_add_crew.py
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QLineEdit, QFrame, 
                             QGraphicsDropShadowEffect, QMessageBox, QDateEdit)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QCursor

class AddCrewWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("إضافة بحار جديد")
        self.resize(620, 560)
        self.setMinimumSize(580, 500)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
            }
            QFrame#Card {
                background-color: #1e293b;
                border-radius: 14px;
                border: 1px solid #334155;
            }
            QLabel {
                color: #e2e8f0;
                font-family: 'Cairo';
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
                color: #f8fafc;
                font-size: 11pt;
                font-family: 'Cairo';
                font-weight: bold;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border-color: #3b82f6;
            }
        """)
        
        self.build_ui()

    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        widget.setGraphicsEffect(shadow)

    def create_input_group(self, layout, label_text, default_value="0", is_date=False):
        group_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        label.setStyleSheet("color: #94a3b8;")
        label.setFixedWidth(150)
        
        if is_date:
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setDate(QDate.currentDate())
        else:
            widget = QLineEdit()
            widget.setText(str(default_value))
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        group_layout.addWidget(widget)
        group_layout.addWidget(label)
        layout.addLayout(group_layout)
        return widget

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(18)

        # كارت البيانات
        card = QFrame()
        card.setObjectName("Card")
        self.add_shadow(card)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        title = QLabel("تسجيل بيانات بحار جديد 👤")
        title.setFont(QFont("Cairo", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #60a5fa;")
        title.setAlignment(Qt.AlignmentFlag.AlignRight)
        card_layout.addWidget(title)
        card_layout.addSpacing(5)

        self.name_e = self.create_input_group(card_layout, "اسم البحار الكامل:", "")
        
        # الرتبة
        rank_layout = QHBoxLayout()
        self.rank_combo = QComboBox()
        ranks = ['MASTER', 'CH.OFF', '2nd.OFF', '3rd.OFF', 'CH.ENG', '2nd.ENG', '3rd.ENG', 'ELECTRICIAN', 'BOSUN', 'FITTER', 'PUMP MAN', 'A/B', 'O/S', 'OILER', 'WIPER', 'COOK', 'MESS BOY', 'CADET']
        self.rank_combo.addItems(ranks)
        self.rank_combo.setCurrentText('A/B')
        
        rank_label = QLabel("الرتبة البحرية:")
        rank_label.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        rank_label.setStyleSheet("color: #94a3b8;")
        rank_label.setFixedWidth(150)
        rank_layout.addWidget(self.rank_combo)
        rank_layout.addWidget(rank_label)
        card_layout.addLayout(rank_layout)

        self.wage_e = self.create_input_group(card_layout, "الراتب الشهري الأساسي $:")
        self.wage_e.setStyleSheet("color: #34d399;")
        
        self.period_cal = self.create_input_group(card_layout, "تاريخ بدء الخدمة:", is_date=True)
        
        self.contract_start_cal = self.create_input_group(card_layout, "تاريخ بدء العقد:", is_date=True)
        self.contract_end_cal = self.create_input_group(card_layout, "تاريخ انتهاء العقد:", is_date=True)
        self.contract_end_cal.setDate(QDate.currentDate().addMonths(6))
        
        self.prev_e = self.create_input_group(card_layout, "رصيد دائن/مدين (سابق) $:")
        self.prev_e.setStyleSheet("color: #fbbf24;")

        main_layout.addWidget(card)

        # الأزرار
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        btn_cancel = QPushButton("إلغاء ❌")
        btn_cancel.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #475569;
                color: #94a3b8;
                border-radius: 8px;
                padding: 10px 22px;
            }
            QPushButton:hover { background-color: #334155; color: #e2e8f0; }
        """)
        btn_cancel.clicked.connect(self.close)
        
        btn_save = QPushButton("حفظ وإضافة 💾")
        btn_save.setFont(QFont("Cairo", 11, QFont.Weight.Bold))
        btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 25px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_save.clicked.connect(self.save_data)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)

    def save_data(self):
        try:
            name = self.name_e.text().strip()
            if not name:
                QMessageBox.warning(self, "خطأ", "يجب إدخال اسم البحار!")
                return
                
            rank = self.rank_combo.currentText()
            wage = float(self.wage_e.text() or 0)
            period_from = self.period_cal.date().toString("yyyy-MM-dd")
            contract_start = self.contract_start_cal.date().toString("yyyy-MM-dd")
            contract_end = self.contract_end_cal.date().toString("yyyy-MM-dd")
            previous = float(self.prev_e.text() or 0)
            
            conn = sqlite3.connect('arn_ship_payroll.db')
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO CrewWages (Name, Rank, MonthlyWage, PeriodFrom, PREVIOUS, contract_start, contract_end) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, rank, wage, period_from, previous, contract_start, contract_end))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # تسجيل في سجل التدقيق وفحص التنبيهات
            try:
                from audit_service import AuditService
                AuditService().log_create(1, "ADMIN", "CrewWages", new_id, f"إضافة بحار جديد: {name} ({rank}) براتب ${wage:,.2f}")
                from alert_service import AlertService
                AlertService().check_contract_expiry()
            except Exception:
                pass

            if hasattr(self.parent_window, 'load_data'):
                self.parent_window.load_data()
            elif hasattr(self.parent_window, 'refresh_data'):
                self.parent_window.refresh_data()
                
            QMessageBox.information(self, "نجاح", f"تم إضافة البحار {name} بنجاح!")
            self.close()

            
        except ValueError:
            QMessageBox.critical(self, "خطأ في الإدخال", "يرجى التأكد من إدخال أرقام صحيحة في حقول الراتب والرصيد.")