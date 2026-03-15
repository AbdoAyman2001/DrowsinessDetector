import cv2
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
        self._face_lost_frames = 0
        self._prev_alarm_level = AlarmLevel.NONE
        self._prev_eye_state = EyeState.AWAKE
        self._prev_ear = 0.0
        self._prev_mar = 0.0

    def process_frame(self, bgr_frame: np.ndarray) -> DetectionResult:
        result = DetectionResult()

        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        landmarks = self.face_mesh.process(gray)
        if landmarks is None:
            if (self._prev_alarm_level != AlarmLevel.NONE
                    and self._face_lost_frames < self._config.face_lost_grace_frames):
                self._face_lost_frames += 1
                result.alarm_level = self._prev_alarm_level
                result.eye_state = self._prev_eye_state
                result.ear = self._prev_ear
                result.mar = self._prev_mar
            else:
                # Grace expired or no prior alarm — reset to prevent re-latching
                self._prev_alarm_level = AlarmLevel.NONE
            return result

        self._face_lost_frames = 0
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

        self._prev_alarm_level = result.alarm_level
        self._prev_eye_state = result.eye_state
        self._prev_ear = result.ear
        self._prev_mar = result.mar

        return result

    def reset_counters(self):
        self.eye_detector.reset()
        self.yawn_detector.reset()

    def close(self):
        self.face_mesh.close()
