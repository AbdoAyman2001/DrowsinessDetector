import time

from config import Config
from alarm.audio_alarm import AudioAlarm
from alarm.gpio_siren import GpioSiren
from alarm.gsm_alarm import GsmAlarm
from detection.detector_engine import AlarmLevel


class AlarmManager:
    def __init__(self, config: Config):
        self._config = config
        self._audio = AudioAlarm()
        self._siren = GpioSiren()
        self._gsm = None
        if config.gsm_enabled:
            self._gsm = GsmAlarm(
                config.gsm_port, config.gsm_baud,
                config.gsm_phone_number, config.driver_name,
            )
        self._current_level = AlarmLevel.NONE
        self._last_trigger_time = 0.0

    @property
    def current_level(self) -> str:
        return self._current_level

    def update(self, alarm_level: str):
        now = time.time()

        if alarm_level == AlarmLevel.NONE:
            # Don't stop alarm during cooldown (prevents flicker from jittery detection)
            if self._current_level != AlarmLevel.NONE:
                if (now - self._last_trigger_time) >= self._config.alarm_cooldown_seconds:
                    self._audio.stop()
                    self._siren.off()
                    self._current_level = AlarmLevel.NONE
            return

        # Cooldown check: don't re-trigger if same level within cooldown
        if (alarm_level == self._current_level
                and self._audio.is_playing
                and (now - self._last_trigger_time) < self._config.alarm_cooldown_seconds):
            return

        # Level changed or cooldown expired — trigger
        if alarm_level != self._current_level or not self._audio.is_playing:
            self._audio.stop()
            if alarm_level == AlarmLevel.WARNING:
                self._audio.play_warning(
                    self._config.warning_freq_low,
                    self._config.warning_freq_high,
                    self._config.alarm_volume,
                )
            elif alarm_level == AlarmLevel.CRITICAL:
                self._audio.play_critical(
                    self._config.critical_freq_low,
                    self._config.critical_freq_high,
                    self._config.alarm_volume,
                )
            self._siren.on()
            self._current_level = alarm_level
            self._last_trigger_time = now

    def test_alarm(self, level: str = AlarmLevel.WARNING, duration: float = 3.0):
        """Play alarm for testing, then stop after duration."""
        import threading

        self.update(level)

        def _stop():
            time.sleep(duration)
            self.update(AlarmLevel.NONE)

        threading.Thread(target=_stop, daemon=True).start()

    def send_gsm_alert(self, photo_path: str = ""):
        if self._gsm:
            self._gsm.send_alert(photo_path)

    def stop(self):
        self._audio.stop()
        self._siren.off()
        self._current_level = AlarmLevel.NONE

    def close(self):
        self._audio.close()
        self._siren.close()
        if self._gsm:
            self._gsm.close()
