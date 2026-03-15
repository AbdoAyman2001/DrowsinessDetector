import os
from flask import Blueprint, send_file

dashboard_bp = Blueprint("dashboard", __name__)

_DASHBOARD_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "dashboard.html")
)


@dashboard_bp.route("/")
def index():
    return send_file(_DASHBOARD_PATH, max_age=0)
