import numpy as np
from picamera2 import Picamera2
from config import Config


class Camera:
    def __init__(self, config: Config):
        self._config = config
        self._picam2 = Picamera2()
        self._latest_frame: np.ndarray | None = None

        cam_config = self._picam2.create_video_configuration(
            main={
                "size": (config.camera_width, config.camera_height),
                "format": config.camera_format,
            },
            buffer_count=config.camera_buffer_count,
        )
        self._picam2.configure(cam_config)

    def start(self):
        self._picam2.start()

    def stop(self):
        self._picam2.stop()
        self._picam2.close()

    def get_frame(self) -> np.ndarray:
        frame = self._picam2.capture_array()
        self._latest_frame = frame
        return frame

    @property
    def latest_frame(self) -> np.ndarray | None:
        return self._latest_frame
