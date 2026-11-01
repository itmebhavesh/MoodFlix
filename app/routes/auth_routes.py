"""Authentication API: signup, login, logout, and current-user session."""
import re
from functools import wraps
from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import get_db
from app.security import rate_limit
auth_bp = Blueprint("auth", __name__)


def login_required(function):
    """Reject protected API calls unless a valid user session exists."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Authentication required."}), 401
        return function(*args, **kwargs)
    return wrapped


@auth_bp.post("/auth/signup")
# @auth_bp.post("/auth/signup")
@rate_limit(10, 3600)  # 10 sign-ups per hour per IP
def signup():
    """Create a new account with a Werkzeug password hash."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    display_name = str(data.get("display_name", "")).strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return jsonify({"error": "A valid email address is required."}), 400
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": "Password must contain at least 8 characters."}), 400
    if not display_name:
        display_name = email.split("@", 1)[0]
    try:
        with get_db() as db:
            cursor = db.execute(
                "INSERT INTO users(email,password_hash,display_name) VALUES(?,?,?)",
                (email, generate_password_hash(password), display_name[:80]),
            )
            user_id = cursor.lastrowid
            db.execute("INSERT INTO user_preferences(user_id) VALUES(?)", (user_id,))
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            return jsonify({"error": "An account with this email already exists."}), 409
        raise
    session.clear()
    session["user_id"] = user_id
    return jsonify({"user": {"id": user_id, "email": email, "display_name": display_name}}), 201

@auth_bp.post("/auth/login")
@rate_limit(10, 300)  # 10 login attempts per 5 minutes per IP
def login():
    """Verify credentials and establish a signed session cookie."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    with get_db() as db:
        user = db.execute("SELECT id,email,password_hash,display_name FROM users WHERE email=?", (email,)).fetchone()
    if not user or not isinstance(password, str) or len(password) > 128 or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401
    session.clear()
    session["user_id"] = user["id"]
    return jsonify({"user": {"id": user["id"], "email": user["email"], "display_name": user["display_name"]}}), 200


@auth_bp.post("/auth/logout")
def logout():
    """Clear the current browser session."""
    session.clear()
    return jsonify({"message": "Logged out successfully."}), 200


@auth_bp.get("/auth/me")
@login_required
def me():
    """Return only the currently authenticated account's public fields."""
    with get_db() as db:
        user = db.execute("SELECT id,email,display_name,photo_url,created_at FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not user:
        session.clear()
        return jsonify({"error": "Account not found."}), 404
    return jsonify({"user": dict(user)}), 200
