from flask import Blueprint, jsonify, request, current_app
from dataclasses import asdict

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/api/settings", methods=["GET"])
def get_settings():
    config = current_app.config["shared"]["config"]
    data = asdict(config)
    data.pop("_config_path", None)
    return jsonify(data)


@settings_bp.route("/api/settings", methods=["PUT"])
def update_settings():
    config = current_app.config["shared"]["config"]
    updates = request.get_json()
    if not updates:
        return jsonify({"error": "No JSON body"}), 400
    config.update(updates)
    data = asdict(config)
    data.pop("_config_path", None)
    return jsonify(data)
