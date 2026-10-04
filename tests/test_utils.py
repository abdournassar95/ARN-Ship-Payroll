# tests/test_utils.py
import pytest
from utils import get_base_rank, get_rank_sort_key, calculate_days_30, RANK_HIERARCHY

@pytest.mark.unit
class TestRankUtilities:
    def test_get_base_rank_standard(self):
        assert get_base_rank("MASTER") == "MASTER"
        assert get_base_rank("CH.OFF") == "CH.OFF"
        assert get_base_rank("COOK") == "COOK"

    def test_get_base_rank_compound(self):
        assert get_base_rank("MASTER 1") == "MASTER"
        assert get_base_rank("CH.OFF (Relief)") == "CH.OFF"
        assert get_base_rank("a/b sailor") == "A/B"

    def test_get_base_rank_empty_or_none(self):
        assert get_base_rank(None) == "OTHER"
        assert get_base_rank("") == "OTHER"
        assert get_base_rank("   ") == "OTHER"

    def test_get_rank_sort_key_order(self):
        # MASTER أعلى رتبة (index 0)
        assert get_rank_sort_key("MASTER") == 0
        assert get_rank_sort_key("CH.OFF") == 1
        assert get_rank_sort_key("CADET") == len(RANK_HIERARCHY) - 1
        # رتبة مجهولة تأتي في نهاية الترتيب
        assert get_rank_sort_key("UNKNOWN_ROLE") == len(RANK_HIERARCHY)

@pytest.mark.unit
class TestMaritimeCalendar30:
    def test_full_30_day_month(self):
        # شهر سبتمبر 30 يوماً
        days = calculate_days_30("2026-09-01", "2026-09-30")
        assert days == 30

    def test_full_31_day_month_treated_as_30(self):
        # في القواعد البحرية: شهر 31 يوماً يحسب 30 يوماً
        days = calculate_days_30("2026-01-01", "2026-01-31")
        assert days == 30

    def test_full_february_treated_as_30(self):
        # شهر فبراير من اليوم الأول للأخير يحسب شهراً كاملاً (30 يوماً)
        days = calculate_days_30("2026-02-01", "2026-02-28")
        assert days == 30

    def test_partial_days_within_month(self):
        # من 10 إلى 20 مايو = 11 يوماً
        days = calculate_days_30("2026-05-10", "2026-05-20")
        assert days == 11

    def test_multi_month_calculation(self):
        # شهران كاملان (يناير وفبراير) = 60 يوماً
        days = calculate_days_30("2026-01-01", "2026-02-28")
        assert days == 60

    def test_invalid_and_empty_inputs(self):
        assert calculate_days_30(None, "2026-01-01") == 0
        assert calculate_days_30("2026-01-01", None) == 0
        assert calculate_days_30("-", "-") == 0
        assert calculate_days_30("invalid-date", "2026-01-01") == 0
        # تاريخ النهاية قبل البداية
        assert calculate_days_30("2026-05-20", "2026-05-10") == 0
