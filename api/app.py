from flask import Flask
from flask_cors import CORS


def create_app(shared_state: dict) -> Flask:
    app = Flask(__name__)
    CORS(app)
    app.config["shared"] = shared_state

    from api.routes_stream import stream_bp
    from api.routes_stats import stats_bp
    from api.routes_settings import settings_bp
    from api.routes_control import control_bp
    from api.routes_dashboard import dashboard_bp

    app.register_blueprint(stream_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(control_bp)
    app.register_blueprint(dashboard_bp)

    return app
