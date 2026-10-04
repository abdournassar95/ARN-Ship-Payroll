# tests/test_notification_service.py
import pytest
from notification_service import NotificationService

@pytest.mark.unit
class TestNotificationService:
    def test_global_sound_toggle(self):
        NotificationService.set_global_sound(False)
        assert NotificationService.is_global_sound_enabled() is False

        NotificationService.set_global_sound(True)
        assert NotificationService.is_global_sound_enabled() is True

    def test_badge_listener_registration_and_update(self):
        received_data = []

        def dummy_listener(count, has_crit):
            received_data.append((count, has_crit))

        NotificationService.register_badge_listener(dummy_listener)
        NotificationService.update_badge(5, True)

        assert len(received_data) == 1
        assert received_data[0] == (5, True)

        NotificationService.unregister_badge_listener(dummy_listener)
        NotificationService.update_badge(0, False)
        assert len(received_data) == 1  # لم يُستدعَ بعد إلغاء التسجيل

    def test_play_sound_does_not_crash(self):
        # التأكد من أن استدعاء الأصوات لا يرمي أي استثناءات
        NotificationService.play_sound("CRITICAL", True)
        NotificationService.play_sound("WARNING", True)
        NotificationService.play_sound("INFO", False)
