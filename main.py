import os
import signal
import sys
import threading
import time
import logging

import cv2
import numpy as np

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from camera.capture import Camera
from detection.detector_engine import DetectorEngine, AlarmLevel
from detection.eye_detector import EyeState
from alarm.alarm_manager import AlarmManager
from storage.database import init_db
from storage.repository import Repository
from api.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("main")


class Application:
    def __init__(self):
        self._running = False
        self._config = Config.load(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        )

        # Database
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self._config.db_path)
        self._db = init_db(db_path)
        self._repo = Repository(self._db)

        # Camera
        self._camera = Camera(self._config)

        # Detection
        self._engine = DetectorEngine(self._config)

        # Alarm
        self._alarm_manager = AlarmManager(self._config)

        # Shared state for API
        self._shared = {
            "config": self._config,
            "engine": self._engine,
            "alarm_manager": self._alarm_manager,
            "repo": self._repo,
            "latest_result": None,
            "raw_frame": None,
            "annotated_frame": None,
            "frame_ready": threading.Event(),
        }

        # Event tracking to avoid duplicate DB entries
        self._prev_eye_state = EyeState.AWAKE
        self._prev_yawn_count = 0

    def start(self):
        self._running = True

        # Start camera
        log.info("Starting camera...")
        self._camera.start()
        time.sleep(1)  # let camera warm up

        # Start API server in daemon thread
        self._start_api()

        # Create session
        session_id = self._repo.create_session()
        log.info(f"Session {session_id} started")

        capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        capture_thread.start()

        try:
            self._detection_loop(session_id)
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown(session_id)

    def _capture_loop(self):
        while self._running:
            frame = self._camera.get_frame()
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self._shared["raw_frame"] = bgr
            self._shared["frame_ready"].set()

    def _detection_loop(self, session_id: int):
        last_snapshot = time.time()
        frame_count = 0
        while self._running:
            frame = self._shared.get("raw_frame")
            if frame is None:
                time.sleep(0.01)
                continue

            result = self._engine.process_frame(frame)
            self._shared["latest_result"] = result

            annotated = self._annotate_frame(frame.copy(), result, self._read_cpu_temp())
            self._shared["annotated_frame"] = annotated

            self._alarm_manager.update(result.alarm_level)
            self._log_events(session_id, result)

            now = time.time()
            if now - last_snapshot >= self._config.snapshot_interval:
                self._repo.log_snapshot(
                    session_id, result.ear, result.mar,
                    result.eye_state, result.yawn_count,
                    result.alarm_level, result.face_detected,
                )
                last_snapshot = now

            frame_count += 1
            if frame_count % 300 == 0:
                log.info(
                    f"Frame {frame_count} | EAR={result.ear:.3f} MAR={result.mar:.3f} "
                    f"Eye={result.eye_state} Yawns={result.yawn_count} Alarm={result.alarm_level}"
                )

            time.sleep(0.033)  # cap at ~30 fps, prevent CPU spin on cached frames

    def _start_api(self):
        app = create_app(self._shared)

        def run_api():
            app.run(
                host=self._config.api_host,
                port=self._config.api_port,
                threaded=True,
                use_reloader=False,
            )

        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        log.info(f"API server started on {self._config.api_host}:{self._config.api_port}")

    def _log_events(self, session_id: int, result):
        # Drowsy/microsleep transition
        if result.eye_state != self._prev_eye_state:
            if result.eye_state == EyeState.DROWSY:
                log.warning("DROWSY detected!")
                self._repo.log_event(
                    session_id, "drowsy", result.ear, result.mar,
                    self._engine.eye_detector.closed_frames,
                )
            elif result.eye_state == EyeState.MICROSLEEP:
                log.critical("MICROSLEEP detected!")
                self._repo.log_event(
                    session_id, "microsleep", result.ear, result.mar,
                    self._engine.eye_detector.closed_frames,
                )
            self._prev_eye_state = result.eye_state

        # New yawn
        if result.yawn_count > self._prev_yawn_count:
            log.warning(f"Yawn detected! Count: {result.yawn_count}")
            self._repo.log_event(session_id, "yawn", result.ear, result.mar)
            self._prev_yawn_count = result.yawn_count
        elif result.yawn_count < self._prev_yawn_count:
            # Window pruned old yawns
            self._prev_yawn_count = result.yawn_count

    @staticmethod
    def _read_cpu_temp() -> float | None:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return int(f.read().strip()) / 1000.0
        except OSError:
            return None

    @staticmethod
    def _annotate_frame(frame: np.ndarray, result, cpu_temp: float | None = None) -> np.ndarray:
        """Accept and return a BGR frame."""
        h, w = frame.shape[:2]

        color = (0, 255, 0)  # green
        if result.alarm_level == AlarmLevel.WARNING:
            color = (0, 165, 255)  # orange
        elif result.alarm_level == AlarmLevel.CRITICAL:
            color = (0, 0, 255)  # red

        cv2.putText(frame, f"EAR: {result.ear:.3f}", (10, 30),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"MAR: {result.mar:.3f}", (10, 60),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Eye: {result.eye_state}", (10, 90),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Yawns: {result.yawn_count}", (10, 120),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if cpu_temp is not None:
            cv2.putText(frame, f"CPU: {cpu_temp:.1f}C", (10, 150),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if not result.face_detected:
            cv2.putText(frame, "NO FACE", (w // 2 - 80, h // 2),
                         cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        if result.alarm_level == AlarmLevel.CRITICAL:
            cv2.putText(frame, "!! WAKE UP !!", (w // 2 - 120, h - 30),
                         cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        elif result.alarm_level == AlarmLevel.WARNING:
            cv2.putText(frame, "! DROWSY !", (w // 2 - 100, h - 30),
                         cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2)

        return frame

    def _shutdown(self, session_id: int):
        log.info("Shutting down...")
        self._running = False
        self._alarm_manager.close()
        self._engine.close()
        self._camera.stop()
        self._repo.end_session(session_id)
        self._db.close()
        log.info("Shutdown complete.")


def main():
    app = Application()

    def handle_signal(signum, frame):
        app._running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    app.start()


if __name__ == "__main__":
    main()
