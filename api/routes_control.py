from flask import Blueprint, jsonify, request, current_app
from detection.detector_engine import AlarmLevel

control_bp = Blueprint("control", __name__)


@control_bp.route("/api/control/alarm-test", methods=["POST"])
def alarm_test():
    alarm_mgr = current_app.config["shared"]["alarm_manager"]
    body = request.get_json(silent=True) or {}
    level = body.get("level", AlarmLevel.WARNING)
    duration = body.get("duration", 3.0)
    alarm_mgr.test_alarm(level=level, duration=float(duration))
    return jsonify({"status": "ok", "level": level, "duration": duration})


@control_bp.route("/api/control/reset-counters", methods=["POST"])
def reset_counters():
    engine = current_app.config["shared"]["engine"]
    engine.reset_counters()
    return jsonify({"status": "ok"})
