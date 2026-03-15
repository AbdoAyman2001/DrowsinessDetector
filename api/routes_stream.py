import cv2
from flask import Blueprint, Response, current_app

stream_bp = Blueprint("stream", __name__)


def _generate_mjpeg(shared):
    frame_ready = shared["frame_ready"]
    while True:
        frame_ready.wait(timeout=0.1)
        frame_ready.clear()

        frame = shared.get("annotated_frame")
        if frame is None:
            frame = shared.get("raw_frame")
        if frame is None:
            continue

        small = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
        ret, jpeg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
        )


@stream_bp.route("/api/stream")
def stream():
    shared = current_app.config["shared"]
    return Response(
        _generate_mjpeg(shared),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
