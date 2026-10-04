# tests/test_report_service.py
import pytest
from report_service import ReportService

@pytest.mark.unit
class TestReportService:
    def test_format_currency(self):
        assert ReportService._format_currency(0) == "0.00"
        assert ReportService._format_currency(1500) == "1,500.00"
        assert ReportService._format_currency(1234567.891) == "1,234,567.89"
        assert ReportService._format_currency(-500.5) == "-500.50"

    def test_normalize_crew_data_complete(self, sample_crew_data):
        norm = ReportService._normalize_crew_data(sample_crew_data)
        assert norm["name"] == "أحمد محمود"
        assert norm["rank"] == "CH.ENG"
        assert norm["month"] == 9
        assert norm["year"] == 2026
        assert norm["basic_wage"] == 3000.0
        assert norm["extra"] == 250.0
        assert norm["deduction"] == 100.0
        assert norm["payment_cash"] == 500.0
        assert norm["cigarette"] == 50.0
        assert norm["transfer"] == 1000.0
        assert norm["company_name"] == "ARN Maritime Co."
        assert norm["vessel_name"] == "ARN Pioneer"

    def test_normalize_crew_data_salary_math(self):
        # total_due = 1000, extra = 200, deduction = 50
        # period_wage = 1000 - 200 + 50 = 850
        # total_earnings = 850 + 200 = 1050
        input_data = {
            "total_due": 1000.0,
            "curr_extra": 200.0,
            "curr_ded": 50.0,
            "name": "سعيد علي"
        }
        norm = ReportService._normalize_crew_data(input_data)
        assert norm["total_due"] == 850.0
        assert norm["total_earnings"] == 1050.0
        assert norm["extra"] == 200.0
        assert norm["deduction"] == 50.0

    def test_normalize_crew_data_empty_input(self):
        # التحقق من أن إدخال كائن فارغ لا يسبب كراش ويملأ الحقول بالقيم الافتراضية
        norm = ReportService._normalize_crew_data({})
        assert norm["name"] == "غير محدد"
        assert norm["rank"] == "غير محدد"
        assert norm["basic_wage"] == 0.0
        assert norm["total_due"] == 0.0
        assert norm["total_earnings"] == 0.0
