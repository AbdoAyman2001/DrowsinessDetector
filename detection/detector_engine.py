import numpy as np
from config import Config
from detection.face_mesh import FaceMeshDetector
from detection.eye_detector import EyeDetector, EyeState
from detection.yawn_detector import YawnDetector


class AlarmLevel:
    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"


class DetectionResult:
    def __init__(self):
        self.face_detected: bool = False
        self.ear: float = 0.0
        self.mar: float = 0.0
        self.eye_state: str = EyeState.AWAKE
        self.yawn_count: int = 0
        self.yawn_alarm: bool = False
        self.alarm_level: str = AlarmLevel.NONE


class DetectorEngine:
    def __init__(self, config: Config):
        self._config = config
        self.face_mesh = FaceMeshDetector()
        self.eye_detector = EyeDetector(config)
        self.yawn_detector = YawnDetector(config)

    def process_frame(self, bgr_frame: np.ndarray) -> DetectionResult:
        result = DetectionResult()

        landmarks = self.face_mesh.process(bgr_frame)
        if landmarks is None:
            return result

        result.face_detected = True

        eye_state = self.eye_detector.update(landmarks)
        result.ear = self.eye_detector.ear
        result.eye_state = eye_state

        yawn_alarm = self.yawn_detector.update(landmarks)
        result.mar = self.yawn_detector.mar
        result.yawn_count = self.yawn_detector.yawn_count
        result.yawn_alarm = yawn_alarm

        # Determine alarm level
        if eye_state == EyeState.MICROSLEEP:
            result.alarm_level = AlarmLevel.CRITICAL
        elif eye_state == EyeState.DROWSY or yawn_alarm:
            result.alarm_level = AlarmLevel.WARNING
        else:
            result.alarm_level = AlarmLevel.NONE

        return result

    def reset_counters(self):
        self.eye_detector.reset()
        self.yawn_detector.reset()

    def close(self):
        self.face_mesh.close()
