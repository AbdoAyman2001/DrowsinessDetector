import time
from collections import deque

import numpy as np
from config import Config

# dlib 68-point landmark indices for mouth
# Inner lip: top [61,62,63], bottom [67,66,65], corners [60,64]
UPPER_LIP = [61, 62, 63]
LOWER_LIP = [67, 66, 65]
MOUTH_CORNERS = [60, 64]


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
        pts = landmarks.astype(np.float64)

        # Sum of 3 vertical distances between upper and lower inner lip
        vert_sum = 0.0
        for upper_idx, lower_idx in zip(UPPER_LIP, LOWER_LIP):
            vert_sum += np.linalg.norm(pts[upper_idx] - pts[lower_idx])

        # Horizontal distance between mouth corners
        horiz = np.linalg.norm(pts[MOUTH_CORNERS[0]] - pts[MOUTH_CORNERS[1]])

        if horiz < 1e-6:
            return 0.0
        return vert_sum / (2.0 * horiz)
