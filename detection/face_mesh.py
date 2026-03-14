import cv2
import dlib
import numpy as np
import os

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shape_predictor_68_face_landmarks.dat")


class FaceMeshDetector:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Shape predictor model not found at {MODEL_PATH}. "
                "Run install.sh or download from http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
            )
        self._detector = dlib.get_frontal_face_detector()
        self._predictor = dlib.shape_predictor(MODEL_PATH)
        self._frame_count = 0
        self._cached_landmarks = None

    def process(self, bgr_frame: np.ndarray):
        """Process a BGR frame. Returns list of 68 (x,y) landmark points or None."""
        self._frame_count += 1

        # Process every 3rd frame, return cached result otherwise
        if self._frame_count % 5 != 1:
            return self._cached_landmarks

        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        faces = self._detector(gray, 0)          # full-res, no downsample
        if not faces:
            self._cached_landmarks = None
            return None

        shape = self._predictor(gray, faces[0])
        landmarks = np.array([(shape.part(i).x, shape.part(i).y) for i in range(68)])
        self._cached_landmarks = landmarks
        return landmarks

    def close(self):
        pass
