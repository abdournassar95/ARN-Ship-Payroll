"""Payroll calculation independent of the Qt interface."""
import sqlite3
import json
import calendar
from datetime import datetime
from dateutil.relativedelta import relativedelta
from utils import calculate_days_30, get_base_rank, get_rank_sort_key
from money import amount, cents, daily_wage, ZERO

class PayrollEngine:
    """يتولى جميع عمليات الحساب وجلب البيانات من قاعدة البيانات"""

    def __init__(self, db_path='arn_ship_payroll.db'):
        self.db_path = db_path

    def get_system_info(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                data = conn.execute(
                    "SELECT company_name, vessel_name FROM system_settings WHERE id=1"
                ).fetchone()
            if data and len(data) == 2:
                return f"{data[1]} - {data[0]}"
            return "ARN Fleet - النظام المحاسبي"
        except sqlite3.Error:
            return "ARN Fleet - النظام المحاسبي"

    def load_crew_data(self, year, month, calc_mode):
        crew_data = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                crew_members = cursor.execute(
                    "SELECT * FROM CrewWages"
                ).fetchall()

                # 1. ترتيب البحارة بحسب الهيكل الوظيفي للرتب
                def rank_sort_key(m):
                    r_str = dict(m).get('Rank', '')
                    no_val = dict(m).get('No', 0)
                    return (get_rank_sort_key(r_str), no_val)

                crew_members = sorted(crew_members, key=rank_sort_key)

                # 2. إحصاء تكرار كل رتبة لترقيمها تلقائياً (مثال: MASTER 1, MASTER 2)
                from collections import Counter
                base_rank_counts = Counter(get_base_rank(dict(m).get('Rank', '')) for m in crew_members)
                base_rank_current_index = {}

                all_history = cursor.execute(
                    "SELECT * FROM payroll_history"
                ).fetchall()

                history_by_crew = {}
                for h in all_history:
                    cid = h['crew_id']
                    history_by_crew.setdefault(cid, []).append(dict(h))

                today = datetime.now()
                today_str = today.strftime("%Y-%m-%d")
                real_year, real_month = today.year, today.month

                selected_month_start = f"{year}-{month:02d}-01"
                last_day = calendar.monthrange(year, month)[1]
                selected_month_end = f"{year}-{month:02d}-{last_day:02d}"
                dt_selected_start = datetime.strptime(selected_month_start, "%Y-%m-%d")
                prev_month_end = (dt_selected_start - relativedelta(days=1)).strftime("%Y-%m-%d")

                if calc_mode == "today" and month == real_month and year == real_year:
                    cap_date = today_str
                else:
                    cap_date = selected_month_end

                for member in crew_members:
                    mem = dict(member)
                    crew_id = mem['No']
                    name = mem['Name']
                    raw_rank = mem['Rank'] or ''
                    base_rank = get_base_rank(raw_rank)

                    total_with_rank = base_rank_counts[base_rank]
                    if total_with_rank > 1:
                        base_rank_current_index[base_rank] = base_rank_current_index.get(base_rank, 0) + 1
                        rank_display = f"{base_rank} {base_rank_current_index[base_rank]}"
                    else:
                        rank_display = base_rank if base_rank != 'OTHER' else (raw_rank or 'OTHER')

                    # Employment starts on the later of assignment and contract start.
                    # Both start and contract end are payable calendar days.
                    period_from = max(filter(None, (mem.get('PeriodFrom'), mem.get('contract_start'))),
                                      default=selected_month_start)
                    contract_end = mem.get('contract_end') or None
                    last_payable_date = min(cap_date, contract_end) if contract_end else cap_date
                    last_past_date = min(prev_month_end, contract_end) if contract_end else prev_month_end
                    wage = amount(mem['MonthlyWage'])
                    prev_balance = amount(mem['PREVIOUS'])
                    paid_data = json.loads(mem.get('PaidMonthsData') or '{}')
                    wage_history = json.loads(mem.get('WageHistory') or '{}')

                    days_worked = calculate_days_30(period_from, last_payable_date)

                    paid_days_past = 0
                    paid_days_current = 0
                    if days_worked > 0:
                        for m_key in paid_data.keys():
                            try:
                                y_num, m_num = map(int, m_key.split('-'))
                                m_start = f"{y_num}-{m_num:02d}-01"
                                m_last = calendar.monthrange(y_num, m_num)[1]
                                m_end = f"{y_num}-{m_num:02d}-{m_last:02d}"
                                actual_start = max(period_from, m_start)
                                actual_end = min(last_payable_date, m_end)
                                if actual_start <= actual_end:
                                    days = calculate_days_30(actual_start, actual_end)
                                    if y_num < year or (y_num == year and m_num < month):
                                        paid_days_past += days
                                    elif y_num == year and m_num == month:
                                        paid_days_current += days
                            except:
                                continue

                    days_worked_past = calculate_days_30(period_from, last_past_date)
                    net_days_past = max(0, days_worked_past - paid_days_past)
                    days_worked_current = max(0, days_worked - days_worked_past)
                    net_days_current = max(0, days_worked_current - paid_days_current)
                    net_days_total = net_days_past + net_days_current

                    past_unpaid_basic = ZERO
                    if period_from <= last_past_date:
                        curr = datetime.strptime(period_from, "%Y-%m-%d").replace(day=1)
                        end = datetime.strptime(last_past_date, "%Y-%m-%d").replace(day=1)
                        while curr <= end:
                            m_key = curr.strftime("%Y-%m")
                            m_start = curr.strftime("%Y-%m-01")
                            m_last = calendar.monthrange(curr.year, curr.month)[1]
                            m_end = curr.strftime(f"%Y-%m-{m_last:02d}")
                            actual_start = max(period_from, m_start)
                            actual_end = min(last_past_date, m_end)
                            if actual_start <= actual_end:
                                days_in_month = calculate_days_30(actual_start, actual_end)
                                if m_key not in paid_data:
                                    w = amount(wage_history.get(m_key, wage))
                                    past_unpaid_basic += daily_wage(w, days_in_month)
                            curr += relativedelta(months=1)

                    wage_key = f"{year}-{month:02d}"
                    current_wage = amount(wage_history.get(wage_key, wage))
                    current_basic = daily_wage(current_wage, net_days_current) if net_days_current > 0 else ZERO

                    past_extra = past_ded = curr_extra = curr_ded = ZERO
                    cum_cash = cum_cig = cum_trans = ZERO

                    for h in history_by_crew.get(crew_id, []):
                        h_year, h_month = h['payroll_year'], h['payroll_month']
                        m_key_hist = f"{h_year}-{h_month:02d}"
                        if m_key_hist not in paid_data:
                            if h_year == year and h_month == month:
                                curr_extra += amount(h['extra'])
                                curr_ded += amount(h['deduction'])
                                cum_cash += amount(h['payment_cash'])
                                cum_cig += amount(h['cigarette'])
                                cum_trans += amount(h['transfer'])
                            elif h_year < year or (h_year == year and h_month < month):
                                past_extra += amount(h['extra'])
                                past_ded += amount(h['deduction'])
                                cum_cash += amount(h['payment_cash'])
                                cum_cig += amount(h['cigarette'])
                                cum_trans += amount(h['transfer'])

                    total_due = cents(current_basic + curr_extra + prev_balance + past_unpaid_basic + past_extra - curr_ded - past_ded)
                    total_received = cents(cum_cash + cum_cig + cum_trans)
                    final_balance = cents(total_due - total_received)


                    is_settled = wage_key in paid_data
                    days_display = "مسوى ✓" if is_settled else f"{net_days_total}"

                    crew_data.append({
                        'id': crew_id,
                        'index': len(crew_data) + 1,
                        'name': name,
                        'rank': rank_display,
                        'days_display': days_display,
                        'wage': float(cents(current_wage)),
                        'curr_extra': float(cents(curr_extra)),
                        'curr_ded': float(cents(curr_ded)),
                        'prev_balance': float(cents(prev_balance)),
                        'total_due': float(cents(total_due)),
                        'cum_cash': float(cents(cum_cash)),
                        'cum_cig': float(cents(cum_cig)),
                        'cum_trans': float(cents(cum_trans)),
                        'total_received': float(cents(total_received)),
                        'final_balance': float(cents(final_balance)),
                        'is_settled': is_settled,
                        'net_days': net_days_total
                    })

            return crew_data

        except sqlite3.Error as e:
            raise Exception(f"خطأ في قاعدة البيانات: {str(e)}")
