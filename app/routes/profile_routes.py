"""Profile, preferences, personal movie library, feedback, and history APIs."""
import json
from urllib.parse import urlparse
from flask import Blueprint, jsonify, request, session
from app.database import get_db
from app.routes.auth_routes import login_required
from app.services.preference_service import get_preferences, update_preferences
from app.services.user_history_service import add_user_movie, list_user_movies, list_recommendations

profile_bp = Blueprint("profile", __name__)
VALID_STATUSES = {"watched", "watchlist", "liked", "disliked", "hidden"}
def clean_movie(movie):
    """Return a safe, typed copy of a client-supplied movie dict, or None if invalid."""
    if not isinstance(movie, dict):
        return None
    title = movie.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    year = movie.get("year") or movie.get("release_year")
    try:
        year = int(year) if year not in (None, "") else None
    except (TypeError, ValueError):
        year = None
    if year is not None and not 1870 <= year <= 2100:
        year = None
    imdb_id = movie.get("imdb_id")
    cleaned = {
        "title": title.strip()[:200],
        "year": year,
        "release_year": year,
        "imdb_id": imdb_id.strip()[:20] if isinstance(imdb_id, str) else None,
    }
    for field in ("genres", "languages"):
        values = movie.get(field)
        cleaned[field] = [str(item)[:50] for item in values[:20]] if isinstance(values, list) else []
    return cleaned


def is_http_url(value):
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

@profile_bp.route("/profile", methods=["GET", "PUT"])
@login_required
def profile():
    """Read or update the signed-in user's profile and taste preferences."""
    user_id = session["user_id"]
    if request.method == "GET":
        with get_db() as db:
            row = db.execute("SELECT id,email,display_name,photo_url,created_at FROM users WHERE id=?", (user_id,)).fetchone()
        return jsonify({"profile": dict(row), "preferences": get_preferences(user_id)})
    data = request.get_json(silent=True) or {}
    display_name = data.get("display_name")
    photo_url = data.get("photo_url")
    if display_name is not None and (not isinstance(display_name, str) or not display_name.strip()):
        return jsonify({"error": "display_name must be a non-empty string."}), 400
    if photo_url is not None and not isinstance(photo_url, str):
        return jsonify({"error": "photo_url must be a string."}), 400
    with get_db() as db:
        if display_name is not None or photo_url is not None:
            db.execute("UPDATE users SET display_name=COALESCE(?,display_name),photo_url=COALESCE(?,photo_url) WHERE id=?",
                       (display_name.strip()[:80] if display_name else None, photo_url[:1000] if photo_url else None, user_id))
        if photo_url is not None and not isinstance(photo_url, str):
            return jsonify({"error": "photo_url must be a string."}), 400
    if photo_url is not None:
        photo_url = photo_url.strip()
        if photo_url and (len(photo_url) > 1000 or not is_http_url(photo_url)):
            return jsonify({"error": "photo_url must be a valid http(s) link."}), 400
    updates, params = [], []
    if display_name is not None:
        updates.append("display_name=?")
        params.append(display_name.strip()[:80])
    if photo_url is not None:
        updates.append("photo_url=?")
        params.append(photo_url or None)  # empty string clears the photo
    if updates:
        with get_db() as db:
            db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", (*params, user_id))
    preference_fields = {key: data[key] for key in ("languages", "genres", "favourite_movies", "favourite_actors", "settings") if key in data}
    try:
        preferences = update_preferences(user_id, preference_fields) if preference_fields else get_preferences(user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    with get_db() as db:
        row = db.execute("SELECT id,email,display_name,photo_url,created_at FROM users WHERE id=?", (user_id,)).fetchone()
    return jsonify({"profile": dict(row), "preferences": preferences})


@profile_bp.route("/library", methods=["GET", "POST"])
@login_required
def library():
    """List the user's movie states or add a movie to one distinct state."""
    user_id = session["user_id"]
    if request.method == "GET":
        status = request.args.get("status")
        if status and status not in VALID_STATUSES:
            return jsonify({"error": "Unknown movie status."}), 400
        return jsonify({"movies": list_user_movies(user_id, status)})
    data = request.get_json(silent=True) or {}
    movie = clean_movie(data.get("movie"))
    status = data.get("status")
    if movie is None:
        return jsonify({"error": "movie.title is required."}), 400
    if status not in VALID_STATUSES:
        return jsonify({"error": "status must be watched, watchlist, liked, disliked, or hidden."}), 400
    watched_at, note = data.get("watched_at"), data.get("note")
    if watched_at is not None and (not isinstance(watched_at, str) or len(watched_at) > 32):
        return jsonify({"error": "watched_at must be a short date string."}), 400
    if note is not None and (not isinstance(note, str) or len(note) > 2000):
        return jsonify({"error": "note must be a string up to 2000 characters."}), 400
    add_user_movie(user_id, movie, status, watched_at, note)
    return jsonify({"message": "Movie state saved.", "status": status}), 201


@profile_bp.post("/feedback")
@login_required
def feedback():
    """Save explicit like/dislike/not-interested feedback for a movie."""
    data = request.get_json(silent=True) or {}
    movie = clean_movie(data.get("movie"))
    feedback_value = data.get("feedback")
    if movie is None:
        return jsonify({"error": "movie.title is required."}), 400
    if feedback_value not in {"like", "dislike", "not_interested"}:
        return jsonify({"error": "feedback must be like, dislike, or not_interested."}), 400
    from app.services.user_history_service import movie_key
    key = movie_key(movie)
    with get_db() as db:
        user_id = session["user_id"]
        db.execute("INSERT INTO user_feedback(user_id,movie_key,feedback) VALUES(?,?,?) ON CONFLICT(user_id,movie_key) DO UPDATE SET feedback=excluded.feedback,created_at=CURRENT_TIMESTAMP",
                   (user_id, key, feedback_value))
        # Keep the profile's visible library in sync with the explicit feedback.
        db.execute("DELETE FROM user_movies WHERE user_id=? AND movie_key=? AND status IN ('liked','disliked','hidden')", (user_id, key))
        status = {"like": "liked", "dislike": "disliked", "not_interested": "hidden"}[feedback_value]
        learned_note = json.dumps({
                        "genres": movie["genres"],
                        "languages": movie["languages"],
        }) if feedback_value == "like" else None
        db.execute("INSERT INTO user_movies(user_id,movie_key,title,release_year,status,note) VALUES(?,?,?,?,?,?)",
                   (user_id, key, movie.get("title", "Untitled"), movie.get("year") or movie.get("release_year"), status, learned_note))
    return jsonify({"message": "Feedback saved.", "feedback": feedback_value}), 201


@profile_bp.get("/history/recommendations")
@login_required
def recommendation_history():
    """Return only the signed-in user's previously recommended movies."""
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)
    except ValueError:
        return jsonify({"error": "limit must be an integer."}), 400
    return jsonify({"history": list_recommendations(session["user_id"], limit)})


@profile_bp.post("/profile/preferences/reset")
@login_required
def reset_preferences():
    """Reset taste preferences without deleting watched or liked history."""
    with get_db() as db:
        db.execute("UPDATE user_preferences SET languages_json='[]',genres_json='[]',favourite_movies_json='[]',favourite_actors_json='[]',settings_json='{}',updated_at=CURRENT_TIMESTAMP WHERE user_id=?", (session["user_id"],))
    return jsonify({"message": "Preferences reset.", "preferences": get_preferences(session["user_id"])})


@profile_bp.delete("/history/recommendations")
@login_required
def clear_recommendation_history():
    """Clear this user's recommendation history only."""
    with get_db() as db:
        db.execute("DELETE FROM recommendation_history WHERE user_id=?", (session["user_id"],))
    return jsonify({"message": "Recommendation history cleared."})


@profile_bp.delete("/library/<int:record_id>")
@login_required
def remove_library_record(record_id):
    """Delete one library row and, for liked/disliked/hidden, its matching feedback row."""
    user_id = session["user_id"]
    with get_db() as db:
        row = db.execute("SELECT movie_key,status FROM user_movies WHERE id=? AND user_id=?", (record_id, user_id)).fetchone()
        if row is None:
            return jsonify({"error": "Movie record not found."}), 404
        db.execute("DELETE FROM user_movies WHERE id=? AND user_id=?", (record_id, user_id))
        if row["status"] in ("liked", "disliked", "hidden"):
            db.execute("DELETE FROM user_feedback WHERE user_id=? AND movie_key=?", (user_id, row["movie_key"]))
    return jsonify({"message": "Movie record removed."})