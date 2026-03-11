from flask import Blueprint, jsonify, current_app

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/api/status")
def status():
    shared = current_app.config["shared"]
    result = shared.get("latest_result")
    if result is None:
        return jsonify({"face_detected": False, "ear": 0, "mar": 0, "alarm_level": "none"})
    return jsonify({
        "face_detected": result.face_detected,
        "ear": round(result.ear, 4),
        "mar": round(result.mar, 4),
        "eye_state": result.eye_state,
        "yawn_count": result.yawn_count,
        "yawn_alarm": result.yawn_alarm,
        "alarm_level": result.alarm_level,
    })


@stats_bp.route("/api/sessions")
def sessions():
    repo = current_app.config["shared"]["repo"]
    return jsonify(repo.get_recent_sessions())


@stats_bp.route("/api/sessions/<int:session_id>/events")
def session_events(session_id):
    repo = current_app.config["shared"]["repo"]
    return jsonify(repo.get_session_events(session_id))


@stats_bp.route("/api/sessions/<int:session_id>/snapshots")
def session_snapshots(session_id):
    repo = current_app.config["shared"]["repo"]
    return jsonify(repo.get_session_snapshots(session_id))


@stats_bp.route("/api/stats/daily")
def daily_stats():
    repo = current_app.config["shared"]["repo"]
    return jsonify(repo.get_daily_stats())
