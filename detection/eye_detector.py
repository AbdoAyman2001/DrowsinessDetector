import numpy as np
from config import Config

# dlib 68-point landmark indices for eyes
RIGHT_EYE = np.array([36, 37, 38, 39, 40, 41])
LEFT_EYE = np.array([42, 43, 44, 45, 46, 47])


class EyeState:
    AWAKE = "awake"
    DROWSY = "drowsy"
    MICROSLEEP = "microsleep"


class EyeDetector:
    def __init__(self, config: Config):
        self._config = config
        self._closed_frames = 0
        self._open_frames = 0
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
            self._open_frames = 0
        else:
            self._open_frames += 1
            if self._open_frames >= self._config.ear_open_frames_reset:
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
        self._open_frames = 0
        self._state = EyeState.AWAKE

    def _compute_avg_ear(self, landmarks: np.ndarray) -> float:
        right_ear = self._compute_ear(landmarks[RIGHT_EYE].astype(np.float64))
        left_ear = self._compute_ear(landmarks[LEFT_EYE].astype(np.float64))
        return (right_ear + left_ear) / 2.0

    @staticmethod
    def _compute_ear(pts: np.ndarray) -> float:
        # EAR = (||P2-P6|| + ||P3-P5||) / (2 * ||P1-P4||)
        vert = pts[np.array([1, 2])] - pts[np.array([5, 4])]
        vert_dists = np.sqrt((vert ** 2).sum(axis=1))
        horiz = np.sqrt(((pts[0] - pts[3]) ** 2).sum())
        if horiz < 1e-6:
            return 0.0
        return vert_dists.sum() / (2.0 * horiz)
