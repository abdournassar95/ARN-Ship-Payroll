# ui_analytics.py

import db
import paths
import math
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QFrame, QWidget, QGridLayout
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QFont, QColor, QCursor, QPainter, QPen, QBrush, QPainterPath, QLinearGradient

# ============================================================
# 1. رسم بياني دائري عالي الجودة (Native PyQt6 Pie Chart)
# ============================================================
class PieChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = [] # [(label, value, QColor)]
        self.setMinimumSize(250, 220)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.data or sum(v for _, v, _ in self.data) == 0:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Cairo", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "لا توجد مسحوبات مسجلة لهذا الشهر")
            return

        total = sum(v for _, v, _ in self.data)
        margin = 15
        side = min(self.width() - 150, self.height() - 2 * margin)
        chart_rect = QRectF(margin, (self.height() - side) / 2, side, side)

        start_angle = 90 * 16
        for label, val, color in self.data:
            if val <= 0: continue
            span_angle = int(round((val / total) * 360 * 16))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawPie(chart_rect, start_angle, span_angle)
            start_angle += span_angle

        # رسم الملاحظات الإيضاحية (Legend)
        legend_x = side + margin + 20
        legend_y = (self.height() - (len(self.data) * 25)) / 2
        painter.setFont(QFont("Cairo", 10))

        for i, (label, val, color) in enumerate(self.data):
            pct = (val / total * 100) if total > 0 else 0
            y = legend_y + i * 28
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(legend_x, y + 4, 12, 12), 3, 3)

            painter.setPen(QColor("#f8fafc"))
            text = f"{label}: ${val:,.0f} ({pct:.1f}%)"
            painter.drawText(QPointF(legend_x + 20, y + 15), text)


# ============================================================
# 2. رسم بياني شريطي (Native PyQt6 Bar Chart)
# ============================================================
class BarChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = [] # [(label, value, QColor)]
        self.setMinimumSize(300, 220)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.data:
            return

        margin_left = 40
        margin_bottom = 35
        margin_top = 25
        margin_right = 20

        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        max_val = max((v for _, v, _ in self.data), default=1)
        if max_val == 0: max_val = 1

        num_bars = len(self.data)
        bar_width = min(45, (w / num_bars) * 0.5)
        gap = (w - (bar_width * num_bars)) / (num_bars + 1)

        # رسم المحاور
        painter.setPen(QPen(QColor("#475569"), 1))
        painter.drawLine(margin_left, margin_top + h, margin_left + w, margin_top + h)

        painter.setFont(QFont("Cairo", 9))
        for i, (label, val, color) in enumerate(self.data):
            x = margin_left + gap + i * (bar_width + gap)
            bar_h = (val / max_val) * (h - 20)
            y = margin_top + h - bar_h

            # رسم الشريط
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_h), 4, 4)

            # رسم القيمة فوق الشريط
            if val > 0:
                painter.setPen(QColor("#ffffff"))
                painter.drawText(QRectF(x - 15, y - 20, bar_width + 30, 20), Qt.AlignmentFlag.AlignCenter, f"${val:,.0f}")

            # رسم التسمية تحت المحور
            painter.setPen(QColor("#cbd5e1"))
            painter.drawText(QRectF(x - 20, margin_top + h + 5, bar_width + 40, 25), Qt.AlignmentFlag.AlignCenter, label)


# ============================================================
# 3. رسم بياني خطي انسيابي (Native PyQt6 Line Chart)
# ============================================================
class LineChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.in_values = [0] * 12
        self.out_values = [0] * 12
        self.setMinimumSize(500, 230)

    def set_data(self, in_values, out_values):
        self.in_values = in_values
        self.out_values = out_values
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin_left = 50
        margin_bottom = 35
        margin_top = 25
        margin_right = 30

        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        max_val = max(max(self.in_values), max(self.out_values), 100)

        # رسم الشبكة والمحاور
        painter.setPen(QPen(QColor("#334155"), 1, Qt.PenStyle.DashLine))
        for i in range(4):
            y = margin_top + (h / 3) * i
            val = max_val * (1 - i / 3)
            painter.drawLine(margin_left, int(y), margin_left + w, int(y))
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Cairo", 8))
            painter.drawText(QRectF(0, y - 10, margin_left - 8, 20), Qt.AlignmentFlag.AlignRight, f"${val:,.0f}")
            painter.setPen(QPen(QColor("#334155"), 1, Qt.PenStyle.DashLine))

        step_x = w / 11
        months = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]

        for i, m_str in enumerate(months):
            x = margin_left + i * step_x
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(QRectF(x - 15, margin_top + h + 5, 30, 20), Qt.AlignmentFlag.AlignCenter, m_str)

        # رسم المنحنيات
        self._draw_curve(painter, self.in_values, max_val, margin_left, margin_top, w, h, step_x, QColor("#10b981"), "الوارد")
        self._draw_curve(painter, self.out_values, max_val, margin_left, margin_top, w, h, step_x, QColor("#ef4444"), "الصادر")

    def _draw_curve(self, painter, values, max_val, ml, mt, w, h, step_x, color, label):
        points = []
        for i, val in enumerate(values):
            x = ml + i * step_x
            y = mt + h - (val / max_val) * h
            points.append(QPointF(x, y))

        path = QPainterPath()
        path.moveTo(points[0])
        for i in range(1, len(points)):
            path.lineTo(points[i])

        painter.setPen(QPen(color, 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # رسم النقاط على المنحنى
        painter.setBrush(QBrush(color))
        for pt in points:
            painter.drawEllipse(pt, 4, 4)


# ============================================================
# 4. نافذة لوحة التحليلات المكتملة
# ============================================================
class AnalyticsWindow(QDialog):
    def __init__(self, parent=None, year=None, month=None):
        super().__init__(parent)
        # المسار من لوحة القيادة (المحرك) وإلا من paths (ثابت) — العيب F12
        engine = getattr(parent, 'engine', None)
        self.db_path = str(getattr(engine, 'db_path', '') or paths.db_path_str())
        self.setWindowTitle("لوحة التحليلات والرسوم البيانية - ARN Fleet Analytics 📊")
        self.resize(1150, 780)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        current_date = datetime.now()
        self.selected_year = year or current_date.year
        self.selected_month = month or current_date.month
        
        self.init_ui()
        self.load_analytics()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. شريط التحكم العلوي
        top_frame = QFrame()
        top_frame.setObjectName("Card")
        top_layout = QHBoxLayout(top_frame)
        
        title_lbl = QLabel("📊 التحليلات البيانية التفاعلية لأسطول ARN")
        title_lbl.setFont(QFont("Cairo", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38bdf8;")
        
        self.combo_year = QComboBox()
        self.combo_year.addItems([str(y) for y in range(2020, 2035)])
        self.combo_year.setCurrentText(str(self.selected_year))
        self.combo_year.setMinimumHeight(38)
        
        lbl_year = QLabel("السنة:")
        lbl_year.setFont(QFont("Cairo", 12))
        
        self.combo_month = QComboBox()
        self.combo_month.addItems([str(m) for m in range(1, 13)])
        self.combo_month.setCurrentText(str(self.selected_month))
        self.combo_month.setMinimumHeight(38)
        
        lbl_month = QLabel("الشهر:")
        lbl_month.setFont(QFont("Cairo", 12))
        
        btn_refresh = QPushButton("تحديث البيانات 🔄")
        btn_refresh.setObjectName("Primary")
        btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_refresh.clicked.connect(self.load_analytics)
        
        top_layout.addWidget(title_lbl)
        top_layout.addStretch()
        top_layout.addWidget(lbl_month)
        top_layout.addWidget(self.combo_month)
        top_layout.addWidget(lbl_year)
        top_layout.addWidget(self.combo_year)
        top_layout.addWidget(btn_refresh)
        
        main_layout.addWidget(top_frame)

        # 2. شبكة الرسوم البيانية المتطورة
        charts_layout = QGridLayout()
        charts_layout.setSpacing(15)

        # Chart 1: Pie Chart
        self.pie_widget = PieChartWidget()
        card_pie = self.create_chart_card("توزيع مسحوبات الطاقم للشهر المختار", self.pie_widget)
        charts_layout.addWidget(card_pie, 0, 0)

        # Chart 2: Bar Chart
        self.bar_widget = BarChartWidget()
        card_bar = self.create_chart_card("مقارنة المكافآت والخصومات والحوالات ($)", self.bar_widget)
        charts_layout.addWidget(card_bar, 0, 1)

        # Chart 3: Line Chart
        self.line_widget = LineChartWidget()
        card_line = self.create_chart_card("مسار التدفق المالي التراكمي لصندوق القبطان طوال السنة", self.line_widget)
        charts_layout.addWidget(card_line, 1, 0, 1, 2)

        main_layout.addLayout(charts_layout)

    def create_chart_card(self, title_text, chart_widget):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        
        lbl = QLabel(title_text)
        lbl.setFont(QFont("Cairo", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #f8fafc; background: transparent; padding-bottom: 5px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(lbl)
        layout.addWidget(chart_widget)
        return card

    def load_analytics(self):
        c_month = int(self.combo_month.currentText())
        c_year = int(self.combo_year.currentText())
        
        conn = db.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. جلب إحصائيات الرواتب
        cursor.execute("""
            SELECT 
                SUM(extra), SUM(deduction), SUM(payment_cash), SUM(cigarette), SUM(transfer)
            FROM payroll_history 
            WHERE payroll_month=? AND payroll_year=?
        """, (c_month, c_year))
        row = cursor.fetchone() or (0, 0, 0, 0, 0)
        extra = row[0] or 0
        deduction = row[1] or 0
        payment_cash = row[2] or 0
        cigarette = row[3] or 0
        transfer = row[4] or 0

        # تحديث Pie Chart
        self.pie_widget.set_data([
            ("سلف كاش", payment_cash, QColor("#ef4444")),
            ("كانتين/سجائر", cigarette, QColor("#f59e0b")),
            ("حوالات عائلية", transfer, QColor("#38bdf8"))
        ])

        # تحديث Bar Chart
        self.bar_widget.set_data([
            ("مكافآت (+)", extra, QColor("#10b981")),
            ("خصومات (-)", deduction, QColor("#ef4444")),
            ("سلف كاش", payment_cash, QColor("#f59e0b")),
            ("حوالات", transfer, QColor("#38bdf8"))
        ])

        # 2. جلب إحصائيات صندوق القبطان
        cursor.execute("""
            SELECT 
                CAST(strftime('%m', date) AS INTEGER) as m,
                SUM(CASE WHEN type='وارد' THEN amount ELSE 0 END) as in_amt,
                SUM(CASE WHEN type='صادر' THEN amount ELSE 0 END) as out_amt
            FROM general_cash 
            WHERE CAST(strftime('%Y', date) AS INTEGER)=?
            GROUP BY m ORDER BY m ASC
        """, (c_year,))
        monthly_cash = cursor.fetchall()
        conn.close()

        in_values = [0] * 12
        out_values = [0] * 12
        for m, in_amt, out_amt in monthly_cash:
            if 1 <= m <= 12:
                in_values[m-1] = in_amt
                out_values[m-1] = out_amt

        self.line_widget.set_data(in_values, out_values)
