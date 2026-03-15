import cv2
import dlib
import numpy as np
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(_DIR, "..", "shape_predictor_68_face_landmarks.dat")


class FaceMeshDetector:
    HOG_EVERY_N = 8  # run HOG every 8 frames (~1/sec at 8 FPS)

    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Shape predictor model not found at {MODEL_PATH}. "
                "Run install.sh or download from http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
            )
        self._detector = dlib.get_frontal_face_detector()
        self._predictor = dlib.shape_predictor(MODEL_PATH)
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self._landmarks_buf = np.empty((68, 2), dtype=np.int64)
        self._frame_count = 0
        self._last_rect = None  # cached face rect (full-frame coords)
        self._miss_count = 0    # consecutive HOG misses

    def _detect_hog(self, gray: np.ndarray):
        """Run HOG on quarter-res for speed. Returns dlib.rectangle or None."""
        h, w = gray.shape[:2]
        # Quarter-res: 1080p -> 480x270, face ~30px — tight but HOG minimum
        scale = 4
        small = cv2.resize(gray, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
        small = self._clahe.apply(small)
        faces = self._detector(small, 0)
        if not faces:
            return None
        r = faces[0]
        return dlib.rectangle(
            r.left() * scale, r.top() * scale,
            r.right() * scale, r.bottom() * scale
        )

    def process(self, bgr_frame: np.ndarray):
        """Process a BGR frame. Returns 68x2 landmark array or None."""
        h, w = bgr_frame.shape[:2]
        self._frame_count += 1

        need_detect = (
            self._last_rect is None
            or self._frame_count % self.HOG_EVERY_N == 0
        )

        if need_detect:
            gray_full = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
            rect = self._detect_hog(gray_full)
            if rect is None:
                self._miss_count += 1
                if self._miss_count > 2:
                    self._last_rect = None
                # Keep using cached rect for up to 2 misses
                if self._last_rect is None:
                    return None
            else:
                self._last_rect = rect
                self._miss_count = 0
        elif self._last_rect is None:
            return None

        rect = self._last_rect

        # Crop face with padding for shape predictor
        pad_x = int((rect.right() - rect.left()) * 0.3)
        pad_y = int((rect.bottom() - rect.top()) * 0.3)
        cx1 = max(0, rect.left() - pad_x)
        cy1 = max(0, rect.top() - pad_y)
        cx2 = min(w, rect.right() + pad_x)
        cy2 = min(h, rect.bottom() + pad_y)

        # Grayscale + CLAHE on cropped face only
        face_gray = cv2.cvtColor(bgr_frame[cy1:cy2, cx1:cx2], cv2.COLOR_BGR2GRAY)
        face_gray = self._clahe.apply(face_gray)

        crop_rect = dlib.rectangle(
            rect.left() - cx1, rect.top() - cy1,
            rect.right() - cx1, rect.bottom() - cy1
        )
        shape = self._predictor(face_gray, crop_rect)

        for i in range(68):
            p = shape.part(i)
            self._landmarks_buf[i, 0] = p.x + cx1
            self._landmarks_buf[i, 1] = p.y + cy1
        return self._landmarks_buf

    def close(self):
        pass
