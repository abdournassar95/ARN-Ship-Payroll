# tests/conftest.py
import pytest
import sqlite3
from database import init_db
from auth_service import AuthService

@pytest.fixture
def temp_db_path(tmp_path):
    """
    إنشاء قاعدة بيانات اختبارية مؤقتة ومعزولة تماماً في مجلد مؤقت لكل اختبار
    """
    db_file = tmp_path / "test_payroll.db"
    db_path_str = str(db_file)
    init_db(db_path_str)
    return db_path_str

@pytest.fixture
def auth_service(temp_db_path):
    """
    خدمة مصادقة تعمل على قاعدة البيانات الاختبارية المعزولة
    """
    return AuthService(db_path=temp_db_path)

@pytest.fixture
def sample_crew_data():
    """
    بيانات تجريبية لفرد من طاقم السفينة لاختبار الحسابات والتقارير
    """
    return {
        "company_name": "ARN Maritime Co.",
        "vessel_name": "ARN Pioneer",
        "name": "أحمد محمود",
        "rank": "CH.ENG",
        "month": 9,
        "year": 2026,
        "basic_wage": 3000.0,
        "worked_days": 30.0,
        "total_due": 3000.0,
        "curr_extra": 250.0,
        "curr_ded": 100.0,
        "payment_cash": 500.0,
        "cigarette": 50.0,
        "transfer": 1000.0,
        "total_received": 1550.0,
        "final_balance": 1600.0
    }
