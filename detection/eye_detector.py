import numpy as np
from config import Config

# dlib 68-point landmark indices for eyes
RIGHT_EYE = [36, 37, 38, 39, 40, 41]  # P1-P6
LEFT_EYE = [42, 43, 44, 45, 46, 47]


class EyeState:
    AWAKE = "awake"
    DROWSY = "drowsy"
    MICROSLEEP = "microsleep"


class EyeDetector:
    def __init__(self, config: Config):
        self._config = config
        self._closed_frames = 0
        self._ear = 0.0
        self._state = EyeState.AWAKE

    @property
    def ear(self) -> float:
        return self._ear

    @property
    def state(self) -> str:
        return self._state

    @property
    def closed_frames(self) -> int:
        return self._closed_frames

    def update(self, landmarks: np.ndarray) -> str:
        self._ear = self._compute_avg_ear(landmarks)

        if self._ear < self._config.ear_threshold:
            self._closed_frames += 1
        else:
            self._closed_frames = 0

        if self._closed_frames >= self._config.ear_microsleep_frames:
            self._state = EyeState.MICROSLEEP
        elif self._closed_frames >= self._config.ear_consec_frames:
            self._state = EyeState.DROWSY
        else:
            self._state = EyeState.AWAKE

        return self._state

    def reset(self):
        self._closed_frames = 0
        self._state = EyeState.AWAKE

    def _compute_avg_ear(self, landmarks: np.ndarray) -> float:
        right_ear = self._compute_ear(landmarks, RIGHT_EYE)
        left_ear = self._compute_ear(landmarks, LEFT_EYE)
        return (right_ear + left_ear) / 2.0

    @staticmethod
    def _compute_ear(landmarks: np.ndarray, indices: list) -> float:
        pts = landmarks[indices].astype(np.float64)
        # EAR = (||P2-P6|| + ||P3-P5||) / (2 * ||P1-P4||)
        p1, p2, p3, p4, p5, p6 = pts
        vertical1 = np.linalg.norm(p2 - p6)
        vertical2 = np.linalg.norm(p3 - p5)
        horizontal = np.linalg.norm(p1 - p4)

        if horizontal < 1e-6:
            return 0.0
        return (vertical1 + vertical2) / (2.0 * horizontal)
