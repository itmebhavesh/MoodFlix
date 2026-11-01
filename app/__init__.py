"""MoodFlix Flask application factory."""
import os
import secrets
from pathlib import Path
from flask import Flask, render_template
from app.database import init_db
from app.security import install_origin_check
from app.routes.recommendation_routes import recommendation_bp
from app.routes.auth_routes import auth_bp
from app.routes.profile_routes import profile_bp
from app.routes.discovery_routes import discovery_bp


PLACEHOLDER_SECRETS = {"", "change-this-to-a-long-random-string", "development-only-change-me"}


def _load_secret_key(is_production):
    """Use FLASK_SECRET_KEY; in development create one once and keep it in instance/."""
    configured = os.getenv("FLASK_SECRET_KEY", "").strip()
    if configured not in PLACEHOLDER_SECRETS:
        return configured
    if is_production:
        raise RuntimeError("Set a real FLASK_SECRET_KEY in .env before running in production.")
    key_file = Path(__file__).resolve().parents[1] / "instance" / ".secret_key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    key_file.write_text(key)
    return key


def create_app(test_config=None):
    """Build the Flask app, initialize persistence, and register API routes."""
    app = Flask(__name__)
    is_production = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "")).strip().lower() == "production"
    app.config.update(
        SECRET_KEY=_load_secret_key(is_production),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=is_production,
        MAX_CONTENT_LENGTH=1024 * 1024,  # reject request bodies over 1 MB
    )
    if test_config:
        app.config.update(test_config)

    init_db()
    install_origin_check(app)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/signup")
    def signup_page():
        return render_template("signup.html")

    @app.route("/profile")
    def profile_page():
        return render_template("profile.html")

    app.register_blueprint(recommendation_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(profile_bp, url_prefix="/api")
    app.register_blueprint(discovery_bp, url_prefix="/api")
    return app