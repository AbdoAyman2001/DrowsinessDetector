import threading

import numpy as np
import pygame


class AudioAlarm:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)
        self._playing = False
        self._lock = threading.Lock()
        self._channel: pygame.mixer.Channel | None = None

    def play_warning(self, freq_low: int, freq_high: int, volume: float):
        self._play_siren(freq_low, freq_high, sweep_duration=0.6, volume=volume)

    def play_critical(self, freq_low: int, freq_high: int, volume: float):
        self._play_siren(freq_low, freq_high, sweep_duration=0.3, volume=volume)

    def stop(self):
        with self._lock:
            self._playing = False
            if self._channel:
                self._channel.stop()
                self._channel = None

    @property
    def is_playing(self) -> bool:
        return self._playing

    def _play_siren(self, freq_low: int, freq_high: int, sweep_duration: float, volume: float):
        with self._lock:
            if self._playing:
                return
            self._playing = True

        sound = self._generate_siren(freq_low, freq_high, sweep_duration, volume)
        with self._lock:
            if not self._playing:
                return
            self._channel = pygame.mixer.Channel(0)
            self._channel.play(sound, loops=-1)

    @staticmethod
    def _generate_siren(freq_low: int, freq_high: int, sweep_duration: float, volume: float) -> pygame.mixer.Sound:
        sample_rate = 44100
        num_samples = int(sample_rate * sweep_duration * 2)  # up + down sweep
        t = np.linspace(0, sweep_duration * 2, num_samples, dtype=np.float64)

        # Frequency sweeps up then down using concatenation
        half = num_samples // 2
        freq = np.concatenate([
            np.linspace(freq_low, freq_high, half),
            np.linspace(freq_high, freq_low, num_samples - half),
        ])

        # Generate sine wave with varying frequency via cumulative phase
        phase = np.cumsum(2.0 * np.pi * freq / sample_rate)
        waveform = np.sin(phase)

        # Scale to 16-bit signed integer
        waveform = (waveform * volume * 32767).astype(np.int16)
        return pygame.mixer.Sound(buffer=waveform.tobytes())

    def close(self):
        self.stop()
        pygame.mixer.quit()
