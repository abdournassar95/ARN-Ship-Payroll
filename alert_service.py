# alert_service.py
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from audit_service import AuditService
from notification_service import NotificationService

class AlertService:
    """
    محرك التنبيهات الذكي لنظام ARN Ship Payroll
    يراقب 8 قواعد تلقائية للعمليات المالية والملاحية والإدارية
    """
    def __init__(self, db_path: str = 'arn_ship_payroll.db'):
        self.db_path = db_path
        self.audit = AuditService(db_path)

    def _get_rule(self, rule_code: str) -> Optional[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM alerts_rules WHERE rule_code = ?", (rule_code,))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    def is_in_cooldown(self, rule_code: str, target_type: Optional[str], target_id: Optional[int], cooldown_hours: int) -> bool:
        """
        فحص هل أُطلق نفس التنبيه لنفس الهدف خلال فترة التهدئة المحددة
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                query = """
                    SELECT triggered_at FROM alerts_history 
                    WHERE rule_code = ?
                """
                params: List[Any] = [rule_code]
                if target_type and target_id:
                    query += " AND target_type = ? AND target_id = ?"
                    params.extend([target_type, target_id])

                query += " ORDER BY id DESC LIMIT 1"
                c.execute(query, params)
                row = c.fetchone()
                if not row:
                    return False

                last_str = row[0]
                last_dt = datetime.strptime(last_str[:19], "%Y-%m-%d %H:%M:%S")
                diff = datetime.now() - last_dt
                return diff.total_seconds() < (cooldown_hours * 3600)
        except Exception as e:
            print(f"⚠️ خطأ في فحص Cooldown: {e}")
            return False

    def _fire_alert(
        self,
        rule: Dict[str, Any],
        message: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None
    ) -> bool:
        """
        تسجيل التنبيه وإشعار المستخدم إذا لم يكن في فترة التهدئة
        """
        rule_code = rule['rule_code']
        cooldown_hours = rule.get('cooldown_hours', 24)

        if self.is_in_cooldown(rule_code, target_type, target_id, cooldown_hours):
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("""
                    INSERT INTO alerts_history (
                        rule_id, rule_code, triggered_at, target_type, target_id, target_name, message, severity, is_read, is_resolved
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """, (
                    rule.get('id'),
                    rule_code,
                    now_str,
                    target_type,
                    target_id,
                    target_name,
                    message,
                    rule.get('severity', 'WARNING')
                ))
                conn.commit()

            # تسجيل الحدث في سجل التدقيق
            self.audit.log(0, "SYSTEM", "ALERT_FIRED", "alerts_history", None, f"[{rule.get('severity')}] {message}")

            # تشغيل الصوت وتحديث الـ Badge
            NotificationService.play_sound(rule.get('severity', 'WARNING'), bool(rule.get('sound_enabled', 1)))
            counts = self.get_alerts_counts()
            NotificationService.update_badge(counts['unread'], counts['critical'] > 0)
            return True
        except Exception as e:
            print(f"⚠️ فشل إطلاق التنبيه [{rule_code}]: {e}")
            return False

    # =========================================================================
    # 1. فحص القواعد الثمانية
    # =========================================================================

    def check_low_cash(self) -> bool:
        """1. LOW_CASH: رصيد الصندوق منخفض"""
        rule = self._get_rule("LOW_CASH")
        if not rule or not rule.get('is_enabled'):
            return False

        threshold = float(rule.get('threshold_value') or 500.0)
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT SUM(amount) FROM general_cash WHERE type='وارد'")
                t_in = c.fetchone()[0] or 0.0
                c.execute("SELECT SUM(amount) FROM general_cash WHERE type='صادر'")
                t_out = c.fetchone()[0] or 0.0
                c.execute("SELECT SUM(payment_cash) FROM payroll_history")
                t_crew = c.fetchone()[0] or 0.0
                c.execute("SELECT SUM(cleared_cash) FROM cash_reset_snapshot")
                t_cleared = c.fetchone()[0] or 0.0

            net_cash = round(t_in - t_out - (t_crew - t_cleared), 2)
            if net_cash < threshold:
                msg = f"تحذير حرج: رصيد صندوق القبطان الحالي (${net_cash:,.2f}) انخفض عن الحد الأدنى المسموح (${threshold:,.2f})!"
                return self._fire_alert(rule, msg, target_type="CASH", target_id=1, target_name="صندوق القبطان")
        except Exception as e:
            print(f"⚠️ خطأ فحص LOW_CASH: {e}")
        return False

    def check_high_advance(self, crew_id: Optional[int] = None, month: Optional[int] = None, year: Optional[int] = None) -> bool:
        """2. HIGH_ADVANCE: سلفة نقدية تتجاوز النسبة المحددة من الراتب"""
        rule = self._get_rule("HIGH_ADVANCE")
        if not rule or not rule.get('is_enabled'):
            return False

        pct_threshold = float(rule.get('threshold_value') or 50.0) / 100.0
        now = datetime.now()
        target_month = month or now.month
        target_year = year or now.year

        fired = False
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                if crew_id:
                    c.execute("""
                        SELECT c.No, c.Name, c.MonthlyWage, p.payment_cash 
                        FROM CrewWages c
                        JOIN payroll_history p ON c.No = p.crew_id
                        WHERE c.No = ? AND p.payroll_month = ? AND p.payroll_year = ?
                    """, (crew_id, target_month, target_year))
                else:
                    c.execute("""
                        SELECT c.No, c.Name, c.MonthlyWage, p.payment_cash 
                        FROM CrewWages c
                        JOIN payroll_history p ON c.No = p.crew_id
                        WHERE p.payroll_month = ? AND p.payroll_year = ?
                    """, (target_month, target_year))

                for row in c.fetchall():
                    wage = float(row['MonthlyWage'] or 0)
                    advance = float(row['payment_cash'] or 0)
                    if wage > 0 and advance > (wage * pct_threshold):
                        pct_actual = int((advance / wage) * 100)
                        msg = f"سلفة مرتفعة: استلم البحار {row['Name']} سلفة بقيمة ${advance:,.2f} تُمثّل {pct_actual}% من راتبه (${wage:,.2f})."
                        if self._fire_alert(rule, msg, target_type="CREW", target_id=row['No'], target_name=row['Name']):
                            fired = True
        except Exception as e:
            print(f"⚠️ خطأ فحص HIGH_ADVANCE: {e}")
        return fired

    def check_contract_expiry(self) -> bool:
        """3. CONTRACT_EXPIRY: اقتراب انتهاء عقد البحار خلال 30 يوماً"""
        rule = self._get_rule("CONTRACT_EXPIRY")
        if not rule or not rule.get('is_enabled'):
            return False

        days_threshold = int(rule.get('threshold_value') or 30)
        today = datetime.now().date()
        fired = False

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT No, Name, contract_end FROM CrewWages WHERE contract_end IS NOT NULL AND contract_end != ''")
                for row in c.fetchall():
                    try:
                        end_date = datetime.strptime(row['contract_end'].strip()[:10], "%Y-%m-%d").date()
                        remaining = (end_date - today).days
                        if 0 <= remaining <= days_threshold:
                            msg = f"اقتراب انتهاء عقد: ينتهي عقد البحار {row['Name']} خلال {remaining} يوماً (بتاريخ {end_date})."
                            if self._fire_alert(rule, msg, target_type="CREW", target_id=row['No'], target_name=row['Name']):
                                fired = True
                    except ValueError:
                        continue
        except Exception as e:
            print(f"⚠️ خطأ فحص CONTRACT_EXPIRY: {e}")
        return fired

    def check_unpaid_months(self) -> bool:
        """4. UNPAID_MONTHS: عدم صرف مستحقات لبحار لـ 3 أشهر متتالية"""
        rule = self._get_rule("UNPAID_MONTHS")
        if not rule or not rule.get('is_enabled'):
            return False

        months_threshold = int(rule.get('threshold_value') or 3)
        now = datetime.now()
        fired = False

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT No, Name, PeriodFrom FROM CrewWages")
                crew_list = c.fetchall()

                for crew in crew_list:
                    crew_id = crew['No']
                    name = crew['Name']
                    period_from = crew['PeriodFrom']
                    if not period_from:
                        continue

                    # فحص آخر N أشهر
                    unpaid_count = 0
                    for offset in range(months_threshold):
                        # حساب الشهر والسنة السابقة
                        check_dt = (now.replace(day=1) - timedelta(days=offset * 30)).replace(day=1)
                        y, m = check_dt.year, check_dt.month
                        c.execute("""
                            SELECT 1 FROM payroll_history 
                            WHERE crew_id = ? AND payroll_month = ? AND payroll_year = ? 
                            AND (payment_cash > 0 OR transfer > 0 OR extra > 0)
                        """, (crew_id, m, y))
                        if not c.fetchone():
                            unpaid_count += 1

                    if unpaid_count >= months_threshold:
                        msg = f"مستحقات معلقة: البحار {name} لم يتم تسجيل أي صرفيات أو معاملات مالية له خلال آخر {months_threshold} أشهر."
                        if self._fire_alert(rule, msg, target_type="CREW", target_id=crew_id, target_name=name):
                            fired = True
        except Exception as e:
            print(f"⚠️ خطأ فحص UNPAID_MONTHS: {e}")
        return fired

    def check_month_not_closed(self) -> bool:
        """5. MONTH_NOT_CLOSED: شهر مالي لم يُقفل بعد مرور 45 يوماً"""
        rule = self._get_rule("MONTH_NOT_CLOSED")
        if not rule or not rule.get('is_enabled'):
            return False

        days_threshold = int(rule.get('threshold_value') or 45)
        now = datetime.now()
        fired = False

        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                # نفحص الشهرين السابقين
                for months_back in [1, 2]:
                    target_dt = (now.replace(day=1) - timedelta(days=months_back * 31)).replace(day=1)
                    y, m = target_dt.year, target_dt.month
                    
                    # هل انتهى الشهر منذ أكثر من 45 يوماً؟
                    # أول يوم في الشهر الذي يليه:
                    next_month_start = (target_dt + timedelta(days=32)).replace(day=1)
                    days_passed = (now.date() - next_month_start.date()).days
                    
                    if days_passed >= (days_threshold - 30):
                        # فحص هل الشهر مقفل
                        c.execute("SELECT 1 FROM cash_closed_months WHERE month = ? AND year = ?", (m, y))
                        if not c.fetchone():
                            msg = f"تنبيه إداري: شهر ({m:02d}-{y}) المالي لم يُقفل بعد في صندوق القبطان رغم انقضاء الفترة المحددة."
                            if self._fire_alert(rule, msg, target_type="SYSTEM", target_id=y*100 + m, target_name=f"{m:02d}-{y}"):
                                fired = True
        except Exception as e:
            print(f"⚠️ خطأ فحص MONTH_NOT_CLOSED: {e}")
        return fired

    def check_cert_expiry(self) -> bool:
        """6. CERT_EXPIRY: اقتراب انتهاء صلاحية شهادة بحرية خلال 60 يوماً"""
        rule = self._get_rule("CERT_EXPIRY")
        if not rule or not rule.get('is_enabled'):
            return False

        days_threshold = int(rule.get('threshold_value') or 60)
        today = datetime.now().date()
        fired = False

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("""
                    SELECT d.id, d.crew_id, d.doc_type, d.expiry_date, c.Name 
                    FROM crew_documents d
                    JOIN CrewWages c ON d.crew_id = c.No
                    WHERE d.expiry_date IS NOT NULL AND d.expiry_date != ''
                """)
                for doc in c.fetchall():
                    try:
                        exp_date = datetime.strptime(doc['expiry_date'].strip()[:10], "%Y-%m-%d").date()
                        remaining = (exp_date - today).days
                        if 0 <= remaining <= days_threshold:
                            msg = f"شهادة ملاحية قاربت على الانتهاء: شهادة ({doc['doc_type']}) للبحار {doc['Name']} تنتهي خلال {remaining} يوماً (بتاريخ {exp_date})."
                            if self._fire_alert(rule, msg, target_type="CREW", target_id=doc['crew_id'], target_name=doc['Name']):
                                fired = True
                    except ValueError:
                        continue
        except Exception as e:
            print(f"⚠️ خطأ فحص CERT_EXPIRY: {e}")
        return fired

    def check_login_failed(self) -> bool:
        """7. LOGIN_FAILED: محاولات دخول فاشلة متكررة خلال 30 دقيقة"""
        rule = self._get_rule("LOGIN_FAILED")
        if not rule or not rule.get('is_enabled'):
            return False

        threshold = int(rule.get('threshold_value') or 2)
        since_str = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT COUNT(*) FROM audit_log 
                    WHERE action = 'LOGIN_FAILED' AND timestamp >= ?
                """, (since_str,))
                fail_count = c.fetchone()[0] or 0

            if fail_count >= threshold:
                msg = f"تنبيه أمني: تم رصد {fail_count} محاولات تسجيل دخول فاشلة للنظام خلال آخر 30 دقيقة!"
                return self._fire_alert(rule, msg, target_type="SYSTEM", target_id=1, target_name="أمان النظام")
        except Exception as e:
            print(f"⚠️ خطأ فحص LOGIN_FAILED: {e}")
        return False

    def check_unusual_deduction(self, crew_id: Optional[int] = None, month: Optional[int] = None, year: Optional[int] = None) -> bool:
        """8. UNUSUAL_DEDUCTION: خصم مالي يتجاوز 200% من متوسط آخر 3 شهور"""
        rule = self._get_rule("UNUSUAL_DEDUCTION")
        if not rule or not rule.get('is_enabled'):
            return False

        ratio_threshold = float(rule.get('threshold_value') or 200.0) / 100.0
        now = datetime.now()
        target_m = month or now.month
        target_y = year or now.year
        fired = False

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                
                target_ids = [crew_id] if crew_id else [r[0] for r in c.execute("SELECT No FROM CrewWages").fetchall()]

                for cid in target_ids:
                    # جلب خصم الشهر المستهدف
                    c.execute("""
                        SELECT deduction FROM payroll_history 
                        WHERE crew_id = ? AND payroll_month = ? AND payroll_year = ?
                    """, (cid, target_m, target_y))
                    curr_row = c.fetchone()
                    curr_ded = float(curr_row[0] or 0) if curr_row else 0.0

                    if curr_ded <= 0:
                        continue

                    # جلب متوسط الخصومات لآخر 3 أشهر سابقة
                    c.execute("""
                        SELECT deduction FROM payroll_history 
                        WHERE crew_id = ? AND (payroll_year < ? OR (payroll_year = ? AND payroll_month < ?))
                        ORDER BY payroll_year DESC, payroll_month DESC LIMIT 3
                    """, (cid, target_y, target_y, target_m))
                    past_rows = c.fetchall()
                    if len(past_rows) < 3:
                        continue  # بحار جديد لديه أقل من 3 أشهر

                    avg_past = sum(float(r[0] or 0) for r in past_rows) / len(past_rows)
                    if avg_past > 0 and curr_ded > (avg_past * ratio_threshold):
                        c.execute("SELECT Name FROM CrewWages WHERE No = ?", (cid,))
                        crew_name = c.fetchone()[0] or "بحار"
                        pct = int((curr_ded / avg_past) * 100)
                        msg = f"خصم مالي استثنائي: خُصم من البحار {crew_name} مبلغ ${curr_ded:,.2f} وهو ما يعادل {pct}% من متوسط خصوماته السابقة (${avg_past:,.2f})."
                        if self._fire_alert(rule, msg, target_type="CREW", target_id=cid, target_name=crew_name):
                            fired = True
        except Exception as e:
            print(f"⚠️ خطأ فحص UNUSUAL_DEDUCTION: {e}")
        return fired

    def check_all(self):
        """
        تشغيل الفحص الشامل لجميع القواعد (يستدعى عند بدء تشغيل البرنامج)
        """
        self.check_low_cash()
        self.check_high_advance()
        self.check_contract_expiry()
        self.check_unpaid_months()
        self.check_month_not_closed()
        self.check_cert_expiry()
        self.check_login_failed()
        self.check_unusual_deduction()

    # =========================================================================
    # 2. إدارة التنبيهات وإحصائياتها
    # =========================================================================

    def get_alerts_counts(self) -> Dict[str, int]:
        """إرجاع إحصائية التنبيهات المفتوحة والحرجة لتحديث الـ Badge"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM alerts_history WHERE is_resolved = 0 AND is_read = 0")
                unread = c.fetchone()[0] or 0

                c.execute("SELECT COUNT(*) FROM alerts_history WHERE is_resolved = 0 AND severity = 'CRITICAL'")
                critical = c.fetchone()[0] or 0

                c.execute("SELECT COUNT(*) FROM alerts_history WHERE is_resolved = 0 AND severity = 'WARNING'")
                warning = c.fetchone()[0] or 0

                c.execute("SELECT COUNT(*) FROM alerts_history WHERE is_resolved = 0 AND severity = 'INFO'")
                info = c.fetchone()[0] or 0

                c.execute("SELECT COUNT(*) FROM alerts_history WHERE is_resolved = 0")
                unresolved = c.fetchone()[0] or 0

                return {
                    'unread': unread,
                    'critical': critical,
                    'warning': warning,
                    'info': info,
                    'unresolved': unresolved
                }
        except Exception:
            return {'unread': 0, 'critical': 0, 'warning': 0, 'info': 0, 'unresolved': 0}

    def get_alerts(self, severity: Optional[str] = None, only_unresolved: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                query = "SELECT * FROM alerts_history WHERE 1=1"
                params: List[Any] = []
                if only_unresolved:
                    query += " AND is_resolved = 0"
                if severity and severity != "ALL":
                    query += " AND severity = ?"
                    params.append(severity)
                query += " ORDER BY id DESC LIMIT ?"
                params.append(limit)
                c.execute(query, params)
                return [dict(r) for r in c.fetchall()]
        except Exception as e:
            print(f"⚠️ خطأ جلب التنبيهات: {e}")
            return []

    def mark_as_read(self, alert_id: int) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE alerts_history SET is_read = 1 WHERE id = ?", (alert_id,))
                conn.commit()
            counts = self.get_alerts_counts()
            NotificationService.update_badge(counts['unread'], counts['critical'] > 0)
            return True
        except Exception:
            return False

    def mark_all_as_read(self) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE alerts_history SET is_read = 1 WHERE is_read = 0")
                conn.commit()
            counts = self.get_alerts_counts()
            NotificationService.update_badge(counts['unread'], counts['critical'] > 0)
            return True
        except Exception:
            return False

    def resolve_alert(self, alert_id: int, resolved_by_user_id: int = 1) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute("""
                    UPDATE alerts_history 
                    SET is_resolved = 1, is_read = 1, resolved_at = ?, resolved_by = ? 
                    WHERE id = ?
                """, (now_str, resolved_by_user_id, alert_id))
                conn.commit()
            counts = self.get_alerts_counts()
            NotificationService.update_badge(counts['unread'], counts['critical'] > 0)
            return True
        except Exception:
            return False

    def get_all_rules(self) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM alerts_rules ORDER BY id ASC")
                return [dict(r) for r in c.fetchall()]
        except Exception:
            return []

    def update_rule(
        self,
        rule_code: str,
        threshold_value: float,
        cooldown_hours: int,
        severity: str,
        is_enabled: bool,
        sound_enabled: bool
    ) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE alerts_rules 
                    SET threshold_value = ?, cooldown_hours = ?, severity = ?, is_enabled = ?, sound_enabled = ?
                    WHERE rule_code = ?
                """, (threshold_value, cooldown_hours, severity, int(is_enabled), int(sound_enabled), rule_code))
                conn.commit()
            return True
        except Exception as e:
            print(f"⚠️ خطأ تحديث قاعدة التنبيه {rule_code}: {e}")
            return False

    def export_pdf(self, output_path: str, alerts: List[Dict[str, Any]], vessel_name: str = "ARN Fleet") -> bool:
        """
        تصدير تقرير التنبيهات إلى ملف PDF رسمي بالعربية.

        يستخدم محرك التقارير Qt نفسه (ReportService) لضمان ظهور العربية (RTL)
        دون الاعتماد على reportlab وخطوطه اللاتينية.
        """
        try:
            from report_service import ReportService

            rows = []
            for idx, item in enumerate(alerts, 1):
                status = "معالَج" if item.get('is_resolved') else ("مقروء" if item.get('is_read') else "قائم")
                rows.append([
                    idx,
                    str(item.get('triggered_at', ''))[:16],
                    str(item.get('rule_code', '')),
                    str(item.get('severity', '')),
                    str(item.get('target_name') or '-'),
                    status,
                    str(item.get('message', '')),
                ])

            ReportService.generate_table_report(
                title="ARN TECHNOLOGY — تقرير التنبيهات الذكية",
                subtitle=f"السفينة: {vessel_name} | عدد التنبيهات: {len(alerts)}",
                headers=["#", "التاريخ", "القاعدة", "الخطورة", "الهدف", "الحالة", "الرسالة"],
                rows=rows,
                col_pct=[4, 12, 10, 8, 12, 8, 46],
                output_path=output_path,
            )
            return True
        except Exception as e:
            print(f"⚠️ فشل تصدير PDF للتنبيهات: {e}")
            return False
