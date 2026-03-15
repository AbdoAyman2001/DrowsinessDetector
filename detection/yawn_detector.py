import time
from collections import deque

import numpy as np
from config import Config

# dlib 68-point landmark indices for mouth
# Inner lip: top [61,62,63], bottom [67,66,65], corners [60,64]
UPPER_LIP = np.array([61, 62, 63])
LOWER_LIP = np.array([67, 66, 65])
MOUTH_INDICES = np.array([60, 61, 62, 63, 64, 65, 66, 67])


class YawnDetector:
    def __init__(self, config: Config):
        self._config = config
        self._mar = 0.0
        self._mouth_open_frames = 0
        self._in_yawn = False
        self._yawn_timestamps: deque[float] = deque()
        self._yawn_alarm = False

    @property
    def mar(self) -> float:
        return self._mar

    @property
    def yawn_count(self) -> int:
        return len(self._yawn_timestamps)

    @property
    def yawn_alarm(self) -> bool:
        return self._yawn_alarm

    def update(self, landmarks: np.ndarray) -> bool:
        self._mar = self._compute_mar(landmarks)

        if self._mar > self._config.mar_threshold:
            self._mouth_open_frames += 1
        else:
            if self._in_yawn and self._mouth_open_frames >= self._config.yawn_min_frames:
                self._yawn_timestamps.append(time.time())
            self._mouth_open_frames = 0
            self._in_yawn = False

        if self._mouth_open_frames >= self._config.yawn_min_frames:
            self._in_yawn = True

        self._prune_old_yawns()
        self._yawn_alarm = len(self._yawn_timestamps) >= self._config.yawn_count_threshold
        return self._yawn_alarm

    def reset(self):
        self._yawn_timestamps.clear()
        self._mouth_open_frames = 0
        self._in_yawn = False
        self._yawn_alarm = False

    def _prune_old_yawns(self):
        cutoff = time.time() - self._config.yawn_window_seconds
        while self._yawn_timestamps and self._yawn_timestamps[0] < cutoff:
            self._yawn_timestamps.popleft()

    @staticmethod
    def _compute_mar(landmarks: np.ndarray) -> float:
        pts = landmarks[MOUTH_INDICES].astype(np.float64)
        # pts layout: [60, 61, 62, 63, 64, 65, 66, 67] -> indices 0-7
        # upper: 61,62,63 -> pts[1],pts[2],pts[3]
        # lower: 67,66,65 -> pts[7],pts[6],pts[5]
        diff_vert = pts[np.array([1, 2, 3])] - pts[np.array([7, 6, 5])]
        vert_sum = np.sqrt((diff_vert ** 2).sum(axis=1)).sum()
        diff_horiz = pts[0] - pts[4]  # 60 - 64
        horiz = np.sqrt((diff_horiz ** 2).sum())
        if horiz < 1e-6:
            return 0.0
        return vert_sum / (2.0 * horiz)
