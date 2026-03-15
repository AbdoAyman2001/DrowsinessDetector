import cv2
import dlib
import numpy as np
import os

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shape_predictor_68_face_landmarks.dat")


class FaceMeshDetector:
    HOG_EVERY_N = 10             # full HOG every 10 frames
    TRACKER_CONFIDENCE = 7.0     # re-detect if tracker score drops below this

    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Shape predictor model not found at {MODEL_PATH}. "
                "Run install.sh or download from http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
            )
        self._detector = dlib.get_frontal_face_detector()
        self._predictor = dlib.shape_predictor(MODEL_PATH)
        self._tracker = dlib.correlation_tracker()
        self._tracking = False
        self._frame_count = 0

    def process(self, gray: np.ndarray):
        """Process a grayscale frame. Returns list of 68 (x,y) landmark points or None."""
        self._frame_count += 1
        need_detect = (
            not self._tracking
            or self._frame_count % self.HOG_EVERY_N == 0
        )

        if need_detect:
            faces = self._detector(gray, 0)
            if not faces:
                self._tracking = False
                return None
            self._tracker.start_track(gray, faces[0])
            self._tracking = True
            rect = faces[0]
        else:
            score = self._tracker.update(gray)
            if score < self.TRACKER_CONFIDENCE:
                # Tracker lost confidence, force re-detect
                faces = self._detector(gray, 0)
                if not faces:
                    self._tracking = False
                    return None
                self._tracker.start_track(gray, faces[0])
                rect = faces[0]
            else:
                pos = self._tracker.get_position()
                rect = dlib.rectangle(
                    int(pos.left()), int(pos.top()),
                    int(pos.right()), int(pos.bottom())
                )

        shape = self._predictor(gray, rect)
        landmarks = np.array([(shape.part(i).x, shape.part(i).y) for i in range(68)])
        return landmarks

    def close(self):
        pass
