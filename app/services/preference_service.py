"""Read and update a user's long-term movie preferences."""
import json
from app.database import get_db


def get_preferences(user_id):
    """Return normalized preference JSON for one user."""
    with get_db() as db:
        row = db.execute("SELECT * FROM user_preferences WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return {"languages": [], "genres": [], "favourite_movies": [], "favourite_actors": [], "settings": {}}
    return {
        "languages": json.loads(row["languages_json"]),
        "genres": json.loads(row["genres_json"]),
        "favourite_movies": json.loads(row["favourite_movies_json"]),
        "favourite_actors": json.loads(row["favourite_actors_json"]),
        "settings": json.loads(row["settings_json"]),
    }


def update_preferences(user_id, data):
    """Validate and persist the editable preference groups."""
    current = get_preferences(user_id)
    for field in ("languages", "genres", "favourite_movies", "favourite_actors"):
        if field in data:
            value = data[field]
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise ValueError(f"{field} must be a list of strings")
            current[field] = list(dict.fromkeys(item.strip() for item in value if item.strip()))
    if "settings" in data:
        if not isinstance(data["settings"], dict):
            raise ValueError("settings must be an object")
        current["settings"].update(data["settings"])
    with get_db() as db:
        db.execute(
            "INSERT INTO user_preferences(user_id,languages_json,genres_json,favourite_movies_json,favourite_actors_json,settings_json) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET languages_json=excluded.languages_json, "
            "genres_json=excluded.genres_json,favourite_movies_json=excluded.favourite_movies_json, "
            "favourite_actors_json=excluded.favourite_actors_json,settings_json=excluded.settings_json,updated_at=CURRENT_TIMESTAMP",
            (user_id, json.dumps(current["languages"]), json.dumps(current["genres"]),
             json.dumps(current["favourite_movies"]), json.dumps(current["favourite_actors"]), json.dumps(current["settings"])),
        )
    return current


def get_effective_preferences(user_id):
    """Combine profile choices with explicitly liked movies for light learning."""
    preferences = get_preferences(user_id)
    with get_db() as db:
        rows = db.execute("SELECT note FROM user_movies WHERE user_id=? AND status='liked' AND note IS NOT NULL", (user_id,)).fetchall()
    for row in rows:
        try:
            learned = json.loads(row["note"] or "{}")
        except (TypeError, ValueError):
            continue
        for field in ("genres", "languages"):
            for value in learned.get(field, []) if isinstance(learned.get(field, []), list) else []:
                if isinstance(value, str) and value.strip() and value not in preferences[field]:
                    preferences[field].append(value)
    return preferences
