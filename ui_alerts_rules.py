# ui_alerts_rules.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from alert_service import AlertService

class AlertRulesDialog(QDialog):
    """
    نافذة إدارة وتعديل قواعد التنبيهات الذكية (الحدود، فترات التهدئة، الأصوات)
    """
    def __init__(self, db_path: str = 'arn_ship_payroll.db', parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.service = AlertService(db_path)

        self.setWindowTitle("إدارة قواعد التنبيهات الذكية ⚙️ | ARN Alerts Rules")
        self.resize(950, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.init_ui()
        self.load_rules()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # عنوان
        title_lbl = QLabel("⚙️ ضبط القواعد الحسابية للتنبيهات الذكية")
        title_lbl.setFont(QFont("Cairo", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel("يمكنك تخصيص القيم الحدية وفترات التهدئة ومستوى الخطورة لكل قاعدة من القواعد الـ 8:")
        desc_lbl.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        layout.addWidget(desc_lbl)

        # جدول القواعد
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "كود القاعدة", "الاسم والوصف", "التصنيف", "القيمة الحدية", "مستوى الخطورة", "التهدئة (ساعة)", "مفعلة؟", "صوت؟"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # أزرار الحفظ
        btn_bar = QHBoxLayout()
        btn_save = QPushButton("حفظ التعديلات 💾")
        btn_save.setObjectName("Success")
        btn_save.clicked.connect(self.save_rules)

        btn_close = QPushButton("إغلاق ❌")
        btn_close.setObjectName("Outline")
        btn_close.clicked.connect(self.close)

        btn_bar.addWidget(btn_save)
        btn_bar.addStretch()
        btn_bar.addWidget(btn_close)
        layout.addLayout(btn_bar)

    def load_rules(self):
        rules = self.service.get_all_rules()
        self.table.setRowCount(len(rules))
        self.row_widgets = []

        for i, r in enumerate(rules):
            # كود
            item_code = QTableWidgetItem(r['rule_code'])
            item_code.setFlags(item_code.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, item_code)

            # اسم ووصف
            name_desc = f"{r['rule_name']}\n{r.get('description', '')}"
            item_name = QTableWidgetItem(name_desc)
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, item_name)

            # تصنيف
            item_cat = QTableWidgetItem(r.get('category', ''))
            item_cat.setFlags(item_cat.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 2, item_cat)

            # القيمة الحدية
            spin_thresh = QDoubleSpinBox()
            spin_thresh.setRange(0.1, 100000.0)
            spin_thresh.setValue(float(r.get('threshold_value') or 0.0))

            self.table.setCellWidget(i, 3, spin_thresh)

            # الخطورة
            combo_sev = QComboBox()
            for s in ["CRITICAL", "WARNING", "INFO"]:
                combo_sev.addItem(s)
            combo_sev.setCurrentText(r.get('severity', 'WARNING'))

            self.table.setCellWidget(i, 4, combo_sev)

            # فترة التهدئة (ساعات)
            spin_cool = QSpinBox()
            spin_cool.setRange(1, 720)
            spin_cool.setValue(int(r.get('cooldown_hours') or 24))

            self.table.setCellWidget(i, 5, spin_cool)

            # تفعيل
            chk_en = QCheckBox()
            chk_en.setChecked(bool(r.get('is_enabled', 1)))
            chk_en.setStyleSheet("margin-left: 15px;")
            self.table.setCellWidget(i, 6, chk_en)

            # صوت
            chk_snd = QCheckBox()
            chk_snd.setChecked(bool(r.get('sound_enabled', 1)))
            chk_snd.setStyleSheet("margin-left: 15px;")
            self.table.setCellWidget(i, 7, chk_snd)

            self.row_widgets.append({
                'code': r['rule_code'],
                'thresh': spin_thresh,
                'sev': combo_sev,
                'cool': spin_cool,
                'en': chk_en,
                'snd': chk_snd
            })

    def save_rules(self):
        for rw in self.row_widgets:
            code = rw['code']
            th = rw['thresh'].value()
            sev = rw['sev'].currentText()
            co = rw['cool'].value()
            en = rw['en'].isChecked()
            snd = rw['snd'].isChecked()

            self.service.update_rule(
                rule_code=code,
                threshold_value=th,
                cooldown_hours=co,
                severity=sev,
                is_enabled=en,
                sound_enabled=snd
            )

        QMessageBox.information(self, "نجاح", "تم حفظ إعدادات قواعد التنبيهات بنجاح.")
        self.accept()
