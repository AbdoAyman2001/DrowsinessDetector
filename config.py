import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Config:
    # Camera
    camera_width: int = 1280
    camera_height: int = 720
    camera_format: str = "RGB888"
    camera_buffer_count: int = 4

    # Eye Aspect Ratio (EAR)
    ear_threshold: float = 0.21
    ear_consec_frames: int = 10        # ~1s at 10 processed fps -> DROWSY
    ear_microsleep_frames: int = 30   # ~3s at 10 processed fps -> MICROSLEEP
    ear_open_frames_reset: int = 3    # consecutive open frames to reset counter

    # Mouth Aspect Ratio (MAR)
    mar_threshold: float = 0.75
    yawn_min_frames: int = 10         # min frames mouth open to count as yawn
    yawn_count_threshold: int = 3     # yawns in window -> alarm
    yawn_window_seconds: int = 300    # 5 minutes

    # Face lost grace period
    face_lost_grace_frames: int = 30  # ~3s at 10 processed fps

    # Alarm
    alarm_cooldown_seconds: float = 5.0
    warning_freq_low: int = 800
    warning_freq_high: int = 1200
    critical_freq_low: int = 1000
    critical_freq_high: int = 1600
    alarm_volume: float = 1.0

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 5000

    # Database
    db_path: str = "drowsiness.db"

    # Snapshot interval (seconds)
    snapshot_interval: int = 30

    # GSM (future)
    gsm_enabled: bool = False
    gsm_port: str = "/dev/ttyUSB0"
    gsm_baud: int = 115200
    gsm_phone_number: str = ""

    _config_path: str = field(default="config.json", repr=False)

    def save(self):
        data = asdict(self)
        data.pop("_config_path", None)
        Path(self._config_path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str = "config.json") -> "Config":
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text())
            data.pop("_config_path", None)
            cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            cfg._config_path = path
            return cfg
        cfg = cls()
        cfg._config_path = path
        return cfg

    def update(self, updates: dict):
        for key, value in updates.items():
            if key.startswith("_"):
                continue
            if hasattr(self, key):
                expected_type = type(getattr(self, key))
                setattr(self, key, expected_type(value))
        self.save()
