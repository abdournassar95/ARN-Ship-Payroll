# audit_service.py
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class AuditService:
    """
    خدمة تسجيل واسترجاع سجل التدقيق (Audit Trail)
    مصممة بطريقة غير معطّلة (Non-blocking): أي خطأ في السجل لا يوقف عمل النظام
    """
    def __init__(self, db_path: str = 'arn_ship_payroll.db'):
        self.db_path = db_path

    def log(
        self,
        user_id: int,
        username: str,
        action: str,
        table_name: Optional[str] = None,
        record_id: Optional[int] = None,
        description: str = ""
    ) -> bool:
        """
        تسجيل حدث تدقيق جديد بشكل آمن
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO audit_log (user_id, username, action, table_name, record_id, description, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id or 0,
                    username or "نظام",
                    action or "UNKNOWN",
                    table_name,
                    record_id,
                    description,
                    now_str
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"⚠️ تحذير غير معطل [AuditService.log]: {e}")
            return False

    def log_create(self, user_id: int, username: str, table_name: str, record_id: Optional[int], description: str) -> bool:
        return self.log(user_id, username, "CREATE", table_name, record_id, description)

    def log_update(self, user_id: int, username: str, table_name: str, record_id: Optional[int], description: str) -> bool:
        return self.log(user_id, username, "UPDATE", table_name, record_id, description)

    def log_delete(self, user_id: int, username: str, table_name: str, record_id: Optional[int], description: str) -> bool:
        return self.log(user_id, username, "DELETE", table_name, record_id, description)

    def log_auth(self, user_id: int, username: str, action: str, description: str) -> bool:
        return self.log(user_id, username, action, "users", user_id, description)

    def get_logs(
        self,
        user_filter: Optional[str] = None,
        action_filter: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: int = 500,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        جلب وتصفية سجلات التدقيق مع دعم الفلترة المتعددة
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = "SELECT * FROM audit_log WHERE 1=1"
                params: List[Any] = []

                if user_filter and user_filter != "الكل":
                    query += " AND username = ?"
                    params.append(user_filter)

                if action_filter and action_filter != "الكل":
                    query += " AND action = ?"
                    params.append(action_filter)

                if from_date:
                    query += " AND DATE(timestamp) >= DATE(?)"
                    params.append(from_date)

                if to_date:
                    query += " AND DATE(timestamp) <= DATE(?)"
                    params.append(to_date)

                if search_text:
                    query += " AND (description LIKE ? OR table_name LIKE ?)"
                    wildcard = f"%{search_text}%"
                    params.extend([wildcard, wildcard])

                query += " ORDER BY id DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"⚠️ خطأ أثناء جلب سجلات التدقيق: {e}")
            return []

    def get_distinct_users(self) -> List[str]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT username FROM audit_log ORDER BY username")
                return [r[0] for r in cursor.fetchall() if r[0]]
        except Exception:
            return []

    def get_distinct_actions(self) -> List[str]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT action FROM audit_log ORDER BY action")
                return [r[0] for r in cursor.fetchall() if r[0]]
        except Exception:
            return []

    def export_pdf(self, output_path: str, logs: List[Dict[str, Any]], vessel_name: str = "ARN Fleet") -> bool:
        """
        تصدير سجل التدقيق إلى ملف PDF رسمي بالعربية.

        يعتمد على محرك التقارير Qt نفسه (ReportService) المستخدم في كشوف الرواتب،
        لضمان ظهور العربية بشكل صحيح (RTL) وعدم الحاجة إلى خطوط لاتينية أو مكتبات خارجية.
        """
        try:
            from report_service import ReportService

            rows = []
            for idx, item in enumerate(logs, 1):
                rows.append([
                    idx,
                    str(item.get('timestamp', '')),
                    str(item.get('username', '')),
                    str(item.get('action', '')),
                    str(item.get('table_name') or '-'),
                    str(item.get('description', '')),
                ])

            ReportService.generate_table_report(
                title="ARN TECHNOLOGY — سجل التدقيق الرسمي",
                subtitle=f"السفينة: {vessel_name} | عدد السجلات: {len(logs)}",
                headers=["#", "التاريخ والوقت", "المستخدم", "العملية", "الجدول", "الوصف"],
                rows=rows,
                col_pct=[4, 15, 12, 11, 9, 49],
                output_path=output_path,
            )
            return True
        except Exception as e:
            print(f"⚠️ فشل تصدير PDF لسجل التدقيق: {e}")
            return False
