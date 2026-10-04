# notification_service.py
import sys
import threading
from typing import Optional

class NotificationService:
    """
    خدمة الإشعارات الصوتية والمرئية للنظام
    تدعم تشغيل أصوات ويندوز وتحديث شارات التنبيهات وإظهار الرسائل المنبثقة
    """
    _global_sound_enabled = True
    _badge_listeners = []

    @classmethod
    def set_global_sound(cls, enabled: bool):
        cls._global_sound_enabled = enabled

    @classmethod
    def is_global_sound_enabled(cls) -> bool:
        return cls._global_sound_enabled

    @classmethod
    def register_badge_listener(cls, callback):
        if callback not in cls._badge_listeners:
            cls._badge_listeners.append(callback)

    @classmethod
    def unregister_badge_listener(cls, callback):
        if callback in cls._badge_listeners:
            cls._badge_listeners.remove(callback)

    @classmethod
    def update_badge(cls, unread_count: int = 0, has_critical: bool = False):
        """إخطار كافة الواجهات المسجلة بتحديث عداد التنبيهات"""
        for callback in cls._badge_listeners:
            try:
                callback(unread_count, has_critical)
            except Exception:
                pass

    @classmethod
    def play_sound(cls, severity: str = "WARNING", rule_sound_enabled: bool = True):
        """
        تشغيل نغمة ويندوز المناسبة بحسب خطورة التنبيه في خيط مستقل
        """
        if not cls._global_sound_enabled or not rule_sound_enabled:
            return

        def _play():
            try:
                if sys.platform == "win32":
                    import winsound
                    if severity.upper() == "CRITICAL":
                        winsound.MessageBeep(winsound.MB_ICONHAND)
                    elif severity.upper() == "WARNING":
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                    elif severity.upper() == "INFO":
                        winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        threading.Thread(target=_play, daemon=True).start()
