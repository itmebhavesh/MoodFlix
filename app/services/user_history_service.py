"""Per-user watched, watchlist, feedback, and recommendation history helpers."""
from app.database import get_db


def movie_key(movie):
    """Prefer stable provider IDs; fall back to a normalized title/year key."""
    imdb_id = str(movie.get("imdb_id") or "").strip().casefold()
    if imdb_id.startswith("tt"):
        return f"imdb:{imdb_id}"
    title = str(movie.get("title", "")).strip().casefold()
    year = movie.get("year") or movie.get("release_year") or ""
    return f"title:{title}:{year}"


FEEDBACK_STATUS = {"liked": "like", "disliked": "dislike", "hidden": "not_interested"}


def add_user_movie(user_id, movie, status, watched_at=None, note=None):
    """Create or update one movie state, keeping related states consistent.

    - liked / disliked / hidden are mutually exclusive and mirrored in user_feedback.
    - marking a movie watched removes it from the watchlist.
    """
    key = movie_key(movie)
    year = movie.get("year") or movie.get("release_year")
    with get_db() as db:
        if status in FEEDBACK_STATUS:
            db.execute(
                "DELETE FROM user_movies WHERE user_id=? AND movie_key=? "
                "AND status IN ('liked','disliked','hidden') AND status<>?",
                (user_id, key, status),
            )
            db.execute(
                "INSERT INTO user_feedback(user_id,movie_key,feedback) VALUES(?,?,?) "
                "ON CONFLICT(user_id,movie_key) DO UPDATE SET feedback=excluded.feedback,created_at=CURRENT_TIMESTAMP",
                (user_id, key, FEEDBACK_STATUS[status]),
            )
        elif status == "watched":
            db.execute("DELETE FROM user_movies WHERE user_id=? AND movie_key=? AND status='watchlist'", (user_id, key))
        db.execute(
            "INSERT INTO user_movies(user_id,movie_key,title,release_year,status,watched_at,note) "
            "VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,movie_key,status) DO UPDATE SET "
            "watched_at=excluded.watched_at,note=excluded.note",
            (user_id, key, movie.get("title", "Untitled"), year, status, watched_at, note),
        )
    return key
def get_user_movie_states(user_id):
    """Return status-specific sets used by recommendation filtering."""
    states = {name: set() for name in ("watched", "watchlist", "liked", "disliked", "hidden")}
    with get_db() as db:
        rows = db.execute("SELECT movie_key,status FROM user_movies WHERE user_id=?", (user_id,)).fetchall()
        feedback = db.execute("SELECT movie_key,feedback FROM user_feedback WHERE user_id=?", (user_id,)).fetchall()
    for row in rows:
        states[row["status"]].add(row["movie_key"])
    for row in feedback:
        if row["feedback"] == "like":
            states["liked"].add(row["movie_key"])
        elif row["feedback"] in ("dislike", "not_interested"):
            states["disliked"].add(row["movie_key"])
    return states


def save_recommendations(user_id, recommendations, mode="my_taste"):
    """Persist only this user's recommendation history."""
    with get_db() as db:
        for index, movie in enumerate(recommendations):
            key = movie_key(movie)
            db.execute(
                "INSERT INTO recommendation_history(user_id,movie_key,title,mode,role,score,reason) VALUES(?,?,?,?,?,?,?)",
                (user_id, key, movie.get("title", "Untitled"), mode,
                 ("Best Match", "Different Experience", "Surprise Discovery")[index] if index < 3 else None,
                 movie.get("score"), movie.get("why") or movie.get("reason")),
            )


def list_user_movies(user_id, status=None):
    """Return a user's movie records; never query another user's rows."""
    with get_db() as db:
        if status:
            rows = db.execute("SELECT * FROM user_movies WHERE user_id=? AND status=? ORDER BY created_at DESC", (user_id, status)).fetchall()
        else:
            rows = db.execute("SELECT * FROM user_movies WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [dict(row) for row in rows]


def list_recommendations(user_id, limit=100):
    """Return recommendation history scoped to the authenticated user."""
    with get_db() as db:
        rows = db.execute("SELECT * FROM recommendation_history WHERE user_id=? ORDER BY recommended_at DESC LIMIT ?", (user_id, limit)).fetchall()
    return [dict(row) for row in rows]


def save_audio_language_evidence(key, language_code, status, source=None):
    """Persist dubbing evidence; positive/negative claims require provenance."""
    if status not in {"available", "not_available", "unknown"}:
        raise ValueError("status must be available, not_available, or unknown")
    if status != "unknown" and not str(source or "").strip():
        raise ValueError("A source is required for verified audio-language status")
    with get_db() as db:
        db.execute(
            "INSERT INTO movie_audio_languages(movie_key,language_code,status,source,checked_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP) "
            "ON CONFLICT(movie_key,language_code) DO UPDATE SET status=excluded.status,source=excluded.source,checked_at=CURRENT_TIMESTAMP",
            (key, str(language_code).strip().lower(), status, source),
        )


def save_ott_evidence(key, region, provider, access_type, source=None):
    """Persist provider availability with region and access type provenance."""
    with get_db() as db:
        db.execute(
            "INSERT INTO ott_availability(movie_key,region,provider,access_type,source,checked_at) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP) "
            "ON CONFLICT(movie_key,region,provider,access_type) DO UPDATE SET source=excluded.source,checked_at=CURRENT_TIMESTAMP",
            (key, str(region or "IN").upper(), str(provider), str(access_type or "stream"), source),
        )


def get_audio_language_evidence(key):
    """Return only explicitly sourced audio-language evidence."""
    with get_db() as db:
        rows = db.execute(
            "SELECT language_code,status,source,checked_at FROM movie_audio_languages WHERE movie_key=?",
            (key,),
        ).fetchall()
    return [dict(row) for row in rows]
