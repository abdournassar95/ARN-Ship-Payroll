import sqlite3
from decimal import Decimal

import pytest

from money import amount, cents, daily_wage
from payroll_engine import PayrollEngine


def test_money_policy():
    assert cents('1.005') == Decimal('1.01')
    assert cents('-1.005') == Decimal('-1.01')
    assert daily_wage('100.05', 15) == Decimal('50.03')
    assert amount(0.1) + amount(0.2) == Decimal('0.3')
    with pytest.raises(ValueError):
        amount('NaN')


def test_partial_month_and_adjustments(temp_db_path):
    with sqlite3.connect(temp_db_path) as conn:
        conn.execute('''INSERT INTO CrewWages (Name, Rank, PeriodFrom, MonthlyWage, PREVIOUS)
                        VALUES (?, ?, ?, ?, ?)''', ('Sailor', 'MASTER', '2026-09-16', 100.05, 0.1))
        conn.execute('''INSERT INTO payroll_history
                        (crew_id, payroll_month, payroll_year, extra, deduction,
                         payment_cash, cigarette, transfer) VALUES (1, 9, 2026, ?, ?, ?, ?, ?)''',
                     (0.2, 0.01, 10.01, 0.02, 0.03))
    row = PayrollEngine(temp_db_path).load_crew_data(2026, 9, 'end')[0]
    assert row['net_days'] == 15
    assert row['total_due'] == 50.32  # 50.03 + 0.20 + 0.10 - 0.01
    assert row['total_received'] == 10.06
    assert row['final_balance'] == 40.26


def test_prior_month_wage_history_and_settlement(temp_db_path):
    with sqlite3.connect(temp_db_path) as conn:
        conn.execute('''INSERT INTO CrewWages
                        (Name, PeriodFrom, MonthlyWage, WageHistory, PaidMonthsData)
                        VALUES (?, ?, ?, ?, ?)''',
                     ('Sailor', '2026-08-01', 300, '{"2026-08": "120.05"}', '{}'))
    engine = PayrollEngine(temp_db_path)
    row = engine.load_crew_data(2026, 9, 'end')[0]
    assert row['total_due'] == 420.05
    with sqlite3.connect(temp_db_path) as conn:
        conn.execute("UPDATE CrewWages SET PaidMonthsData=? WHERE No=1", ('{"2026-08": true}',))
    assert engine.load_crew_data(2026, 9, 'end')[0]['total_due'] == 300.0


def test_contract_first_and_last_days_are_paid(temp_db_path):
    with sqlite3.connect(temp_db_path) as conn:
        conn.execute('''INSERT INTO CrewWages (Name, PeriodFrom, contract_start, contract_end, MonthlyWage)
                        VALUES ('Sailor', '2026-09-10', '2026-09-12', '2026-09-20', 300)''')
    engine = PayrollEngine(temp_db_path)
    row = engine.load_crew_data(2026, 9, 'full_month')[0]
    assert row['net_days'] == 9  # 12th through 20th, inclusive
    assert row['total_due'] == 90.0
    with sqlite3.connect(temp_db_path) as conn:
        conn.execute("UPDATE CrewWages SET contract_end='2026-09-12'")
    row = engine.load_crew_data(2026, 9, 'full_month')[0]
    assert row['net_days'] == 1
    assert row['total_due'] == 10.0


def test_contract_end_caps_current_and_previous_months(temp_db_path):
    with sqlite3.connect(temp_db_path) as conn:
        conn.execute('''INSERT INTO CrewWages (Name, PeriodFrom, contract_end, MonthlyWage)
                        VALUES ('Sailor', '2026-08-25', '2026-09-05', 300)''')
    engine = PayrollEngine(temp_db_path)
    september = engine.load_crew_data(2026, 9, 'full_month')[0]
    assert september['net_days'] == 11  # August 25-30 + September 1-5
    assert september['total_due'] == 110.0
    october = engine.load_crew_data(2026, 10, 'full_month')[0]
    assert october['total_due'] == 110.0  # outstanding wages, no October accrual
    assert october['net_days'] == 11
