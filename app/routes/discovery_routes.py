
"""Mode-based adaptive discovery and upcoming release APIs."""

import json
import uuid

from flask import Blueprint, jsonify, request, session

from app.database import get_db
from app.routes.auth_routes import login_required
from app.services.user_history_service import (
    get_user_movie_states,
    movie_key,
    save_recommendations,
)
from app.services.preference_service import get_effective_preferences


discovery_bp = Blueprint("discovery", __name__)


# Adaptive discovery question bank.
QUESTION_BANK = {
    "today_mood": [
        {
            "id": "mood",
            "text": "Aaj kis mood ki movie dekhni hai?",
            "options": [
                "happy", "fun", "sad", "thoughtful", "thrilled",
                "scared", "relaxed", "romantic", "inspired",
                "adventurous", "not_sure",
            ],
        },
        {
            "id": "languages",
            "text": "Aaj kaunsi language chalegi?",
            "options": [
                "Hindi", "English", "Malayalam", "Tamil", "Telugu",
                "Kannada", "All South Indian Languages",
                "All Languages", "not_sure",
            ],
        },
        {
            "id": "genres",
            "text": "Koi genre bhi include karna hai?",
            "options": [
                "action", "comedy", "drama", "thriller",
                "science_fiction", "romance", "animation",
                "horror", "any",
            ],
        },
        {
            "id": "runtime",
            "text": "Runtime preference?",
            "options": [
                "under_100", "100_to_140", "over_140", "any",
            ],
        },
        {
            "id": "quality",
            "text": "Aaj kis type ki discovery chahiye?",
            "options": ["high", "hidden_gem", "popular", "any"],
        },
    ],
    "surprise_me": [
        {
            "id": "experience",
            "text": "Kis type ka surprise chahiye?",
            "options": [
                "something_new", "mind_bending",
                "feel_good", "adventurous", "any",
            ],
        },
        {
            "id": "languages",
            "text": "Kaunsi languages explore kar sakte ho?",
            "options": [
                "Hindi", "English", "Malayalam", "Tamil", "Telugu",
                "Kannada", "All South Indian Languages",
                "All Languages", "not_sure",
            ],
        },
        {
            "id": "genres",
            "text": "Koi genre preference?",
            "options": [
                "action", "comedy", "drama", "thriller",
                "science_fiction", "romance", "animation",
                "documentary", "horror", "any",
            ],
        },
        {
            "id": "runtime",
            "text": "Runtime preference?",
            "options": [
                "under_100", "100_to_140", "over_140", "any",
            ],
        },
        {
            "id": "quality",
            "text": "Discovery style?",
            "options": ["high", "hidden_gem", "popular", "any"],
        },
    ],
}


LANGUAGE_MAP = {
    "hi": "hindi",
    "hindi": "hindi",
    "en": "english",
    "english": "english",
    "ta": "tamil",
    "tamil": "tamil",
    "te": "telugu",
    "telugu": "telugu",
    "ml": "malayalam",
    "malayalam": "malayalam",
    "kn": "kannada",
    "kannada": "kannada",
}


GENRE_MAP = {
    "science_fiction": ("sci-fi", "science fiction", "science_fiction"),
    "sci-fi": ("sci-fi", "science fiction", "science_fiction"),
}


def normalize_language(value):
    if not value:
        return ""

    value = str(value).strip().lower()
    return LANGUAGE_MAP.get(value, value)


def get_movie_languages(movie):
    """Read comma-separated OMDb language values."""
    language_value = movie.get("language", "")

    return {
        normalize_language(language)
        for language in str(language_value).split(",")
        if language.strip()
    }
    # ---- Fix 6: one shared vocabulary between the quiz options and the movie data ----
GENRE_ALIASES = {
    "action": {"action"}, "comedy": {"comedy"}, "drama": {"drama"}, "thriller": {"thriller", "suspense"},
    "science_fiction": {"sci-fi", "sci fi", "science fiction", "scifi"},
    "romance": {"romance", "romantic"}, "animation": {"animation", "animated"},
    "documentary": {"documentary"}, "horror": {"horror"},
}
MOOD_TAGS = {  # words a movie's "moods" column may contain for each mood option
    "happy": {"happy", "fun", "feel-good", "uplifting", "inspiring"}, "fun": {"fun", "happy", "excited", "funny"},
    "sad": {"sad", "emotional", "melancholic"}, "thoughtful": {"thoughtful", "curious", "emotional", "thought-provoking"},
    "thrilled": {"thrilled", "intense", "excited", "suspense"}, "scared": {"scared", "scary", "dark", "intense", "spooky"},
    "relaxed": {"relaxed", "calm", "light", "feel-good"}, "romantic": {"romantic", "love", "emotional"},
    "inspired": {"inspired", "inspiring", "motivational"}, "adventurous": {"adventurous", "excited", "adventure"},
}
MOOD_GENRES = {  # fallback: genres that usually fit each mood (used when the data has no mood tags)
    "happy": {"comedy", "family", "animation", "musical"}, "fun": {"comedy", "adventure", "animation"},
    "sad": {"drama", "romance"}, "thoughtful": {"drama", "mystery", "sci-fi", "biography"},
    "thrilled": {"thriller", "crime", "mystery", "action"}, "scared": {"horror", "thriller"},
    "relaxed": {"comedy", "family", "animation", "romance"}, "romantic": {"romance"},
    "inspired": {"biography", "sport", "history", "drama"}, "adventurous": {"adventure", "action", "fantasy"},
}
LANGUAGE_CODES = {
    "hi": "hindi", "en": "english", "ml": "malayalam", "ta": "tamil", "te": "telugu", "kn": "kannada",
}


def _split_values(raw):
    """Split a '|' or ',' separated cell (or a list) into lowercase values."""
    if isinstance(raw, (list, tuple, set)):
        parts = [str(part) for part in raw]
    else:
        parts = str(raw or "").replace("|", ",").split(",")
    return [part.strip().casefold() for part in parts if part.strip()]


def _language_names(raw):
    """Turn 'hi' / 'Hindi' / 'Hindi, English' into {'hindi', 'english'}."""
    return {LANGUAGE_CODES.get(value, value) for value in _split_values(raw)}


def _number(value):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _next_question(mode, asked, answers):
    """Pick the next unanswered adaptive question."""
    questions = QUESTION_BANK[mode]

    for question in questions:
        if question["id"] not in asked:
            return question

    if (
        mode == "today_mood"
        and answers.get("mood") not in (None, "not_sure")
        and "mood_intensity" not in asked
    ):
        return {
            "id": "mood_intensity",
            "text": "Mood match kitna strong chahiye?",
            "options": ["exact", "balanced", "loose"],
        }

    if (
        mode == "surprise_me"
        and answers.get("experience") == "mind_bending"
        and "complexity" not in asked
    ):
        return {
            "id": "complexity",
            "text": "Kitna challenging experience chahiye?",
            "options": ["easy", "clever", "very_complex"],
        }

    if (
        mode == "surprise_me"
        and answers.get("experience") == "feel_good"
        and "comfort_level" not in asked
    ):
        return {
            "id": "comfort_level",
            "text": "Feel-good movie kitni light honi chahiye?",
            "options": ["light", "emotional", "uplifting_any"],
        }

    return None


@discovery_bp.post("/modes/start")
@login_required
def start_mode():
    """Start Today's Mood or Surprise Me discovery."""
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")

    if mode not in QUESTION_BANK:
        return jsonify({
            "error": (
                "mode must be today_mood or surprise_me. "
                "My Taste uses the preserved 10-question thriller quiz."
            )
        }), 400

    session_id = str(uuid.uuid4())
    answers = {}
    asked = []

    question = _next_question(mode, asked, answers)

    with get_db() as db:
        db.execute(
            """
            INSERT INTO quiz_sessions
            (id, user_id, mode, answers_json, asked_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                session["user_id"],
                mode,
                json.dumps(answers),
                json.dumps(asked),
            ),
        )

    return jsonify({
        "session_id": session_id,
        "mode": mode,
        "question": question,
        "complete": False,
    }), 201


@discovery_bp.post("/modes/answer")
@login_required
def answer_mode():
    """Save an answer and return the next question or recommendations."""

    data = request.get_json(silent=True) or {}

    session_id = data.get("session_id")
    question_id = data.get("question_id")
    answer = data.get("answer")

    if not all(
        isinstance(value, str) and value.strip()
        for value in (session_id, question_id, answer)
    ):
        return jsonify({
            "error": "session_id, question_id and answer are required."
        }), 400

    with get_db() as db:
        row = db.execute(
            """
            SELECT *
            FROM quiz_sessions
            WHERE id = ? AND user_id = ?
            """,
            (session_id, session["user_id"]),
        ).fetchone()

        if not row:
            return jsonify({"error": "Quiz session not found."}), 404

        if row["completed"]:
            return jsonify({
                "error": "Quiz session is already complete."
            }), 409

        mode = row["mode"]

        if mode not in QUESTION_BANK:
            return jsonify({"error": "Invalid quiz mode."}), 400

        answers = json.loads(row["answers_json"])
        asked = json.loads(row["asked_json"])

        expected = _next_question(mode, asked, answers)

        if (
            not expected
            or expected["id"] != question_id
            or answer not in expected["options"]
        ):
            return jsonify({
                "error": "Answer does not match the current question options."
            }), 400

        answers[question_id] = answer
        asked.append(question_id)

        next_question = _next_question(mode, asked, answers)
        complete = next_question is None

        db.execute(
            """
            UPDATE quiz_sessions
            SET answers_json = ?, asked_json = ?, completed = ?
            WHERE id = ?
            """,
            (
                json.dumps(answers),
                json.dumps(asked),
                int(complete),
                session_id,
            ),
        )

    if not complete:
        return jsonify({
            "session_id": session_id,
            "mode": mode,
            "question": next_question,
            "complete": False,
        }), 200

    # Load the local OMDb catalogue.
    from app.recommendation.movie_loader import load_movies
    from app.recommendation.diversity_engine import (
        select_diverse_recommendations,
    )

    preferences = get_effective_preferences(session["user_id"])

    try:
        catalogue = load_movies()
    except (OSError, ValueError, TypeError):
        return jsonify({
            "error": "Local movie catalogue could not be loaded."
        }), 503

    # Language preferences.
    language_answer = answers.get("languages")
    if language_answer in (None, "not_sure", "All Languages"):
        wanted_languages = {str(value).casefold() for value in preferences.get("languages", [])}
    elif language_answer == "All South Indian Languages":
        wanted_languages = {"malayalam", "tamil", "telugu", "kannada"}
    else:
        wanted_languages = {str(language_answer).casefold()}
    genre_answer = str(answers.get("genres", "any")).casefold()
    wanted_genres = GENRE_ALIASES.get(genre_answer, {genre_answer.replace("_", " ")})
    runtime_band = answers.get("runtime", "any")
    mood_answer = str(answers.get("mood", "")).casefold()
    experience = str(answers.get("experience", "")).casefold()
    quality = answers.get("quality")
    intensity = answers.get("mood_intensity", "balanced")
    complexity = answers.get("complexity")
    comfort = answers.get("comfort_level")
    ranked = []
    for item in catalogue:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        try:
            runtime = int(_number(str(item.get("runtime") or "0").replace("min", "")))
            rating = _number(item.get("rating") or item.get("imdb_rating"))
            year = int(_number(item.get("release_year") or item.get("year")))
        except (TypeError, ValueError):
            continue
        votes = _number(item.get("votes") or item.get("imdb_votes"))
        languages = _language_names(item.get("language"))
        genres = _split_values(item.get("genres") or item.get("genre"))
        moods = _split_values(item.get("moods"))
        genre_text = " ".join(genres + moods)
        if wanted_languages and not (languages & wanted_languages):
            continue
        if genre_answer not in ("", "any") and not (set(genres) & wanted_genres):
            continue
        # A missing runtime (0) must not pass the runtime filters.
        if runtime_band == "under_100" and not 0 < runtime < 100: continue
        if runtime_band == "100_to_140" and not 100 <= runtime <= 140: continue
        if runtime_band == "over_140" and runtime <= 140: continue
        score = rating
        if mood_answer and mood_answer != "not_sure":
            tag_match = bool(set(moods) & MOOD_TAGS.get(mood_answer, {mood_answer}))
            genre_match = bool(set(genres) & MOOD_GENRES.get(mood_answer, set()))
            bonus = 3 if tag_match else 2 if genre_match else 0
            if intensity == "exact":
                score += bonus * 1.5 if bonus else -2
            elif intensity == "loose":
                score += bonus * 0.5
            else:
                score += bonus
        if experience == "mind_bending" and any(word in genre_text for word in ("sci-fi", "thriller", "mystery", "thoughtful")): score += 2
        if experience == "feel_good" and any(word in genre_text for word in ("happy", "fun", "inspiring", "comedy", "family")): score += 2
        if complexity == "easy" and 0 < runtime <= 115: score += 1
        if complexity == "clever" and any(word in genre_text for word in ("mystery", "thriller", "sci-fi")): score += 1
        if complexity == "very_complex" and (runtime >= 130 or any(word in genre_text for word in ("sci-fi", "mystery"))): score += 2
        if comfort == "light" and any(word in genre_text for word in ("comedy", "family", "animation", "fun")): score += 2
        if comfort == "emotional" and any(word in genre_text for word in ("drama", "romance", "emotional")): score += 2
        if quality == "high": score += rating / 10
        if quality == "hidden_gem" and rating >= 7 and 0 < votes < 50000: score += 2
        if quality == "popular" and votes >= 200000: score += 2
        ranked.append({
            "title": title, "year": year, "release_year": year, "runtime": runtime,
            "rating": rating, "language": item.get("language", ""),
            "languages": [item.get("language", "")] if item.get("language") else [],
            "industry": item.get("industry", ""), "genres": genres, "moods": moods,
            "score": score, "plot": "Information currently unavailable",
            "dub_status": "unknown", "dubbed_languages": [],
        })

        # Runtime and rating validation.
        try:
            runtime = int(item.get("runtime") or 0)
            rating = float(item.get("rating") or 0)
            year = int(
                item.get("release_year")
                or item.get("year")
                or 0
            )
        except (TypeError, ValueError):
            continue

        # Do not use missing runtime as a valid runtime.
        if runtime_band != "any" and runtime <= 0:
            continue

        # Language matching.
        movie_languages = get_movie_languages(item)

        if (
            normalized_wanted
            and not normalized_wanted.intersection(movie_languages)
        ):
            continue

        # Genre matching.
        genres = [
            part.strip().casefold()
            for part in str(
                item.get("genres") or item.get("genre") or ""
            ).replace(",", "|").split("|")
            if part.strip()
        ]

        if genre_answer not in ("", "any"):
            acceptable_genres = GENRE_MAP.get(
                genre_answer,
                (genre_answer.replace("_", " "), genre_answer),
            )

            if not any(
                genre in genres
                for genre in acceptable_genres
            ):
                continue

        # Runtime matching.
        if runtime_band == "under_100" and not 0 < runtime < 100:
            continue

        if runtime_band == "100_to_140" and not 100 <= runtime <= 140:
            continue

        if runtime_band == "over_140" and runtime <= 140:
            continue

        # OMDb catalogue does not contain verified mood tags.
        # Therefore no unsupported mood match is claimed.
        score = rating

        if experience == "mind_bending" and any(
            genre in genres
            for genre in ("sci-fi", "science fiction", "thriller", "mystery")
        ):
            score += 2

        if experience == "feel_good" and any(
            genre in genres
            for genre in ("comedy", "family", "musical")
        ):
            score += 2

        if quality == "high":
            score += rating / 10

        ranked.append({
            "title": title,
            "year": year,
            "release_year": year,
            "imdb_id": item.get("imdb_id", ""),
            "runtime": runtime,
            "rating": rating,
            "language": item.get("language", ""),
            "languages": [
                language.strip()
                for language in str(item.get("language", "")).split(",")
                if language.strip()
            ],
            "industry": item.get("industry", ""),
            "genres": genres,
            "moods": [],
            "score": score,
            "plot": item.get("plot") or "Information currently unavailable",
            "poster": item.get("poster", ""),
            "dub_status": "unknown",
            "dubbed_languages": [],
        })

    ranked.sort(
        key=lambda movie: movie["score"],
        reverse=True,
    )

    # Exclude watched, disliked, hidden and recently recommended movies.
    states = get_user_movie_states(session["user_id"])

    with get_db() as db:
        rows = db.execute(
            """
            SELECT movie_key
            FROM recommendation_history
            WHERE user_id = ?
            AND recommended_at >= datetime('now', '-30 days')
            """,
            (session["user_id"],),
        ).fetchall()

    prior = {
        row["movie_key"]
        for row in rows
    }

    filtered = [
        movie
        for movie in ranked
        if movie_key(movie) not in states["watched"]
        and movie_key(movie) not in states["disliked"]
        and movie_key(movie) not in states["hidden"]
        and movie_key(movie) not in prior
    ]

    recommendations = select_diverse_recommendations(
        filtered,
        limit=3,
    )

    # Enrich only selected recommendations with OMDb and Watchmode.
    from app.routes.recommendation_routes import get_movie_metadata

    for movie in recommendations:
        metadata = get_movie_metadata(
            movie.get("title", ""),
            movie.get("year"),
        )

        movie["ott_availability"] = metadata.get(
            "ott_availability", []
        )

        details = metadata.get("details") or {}

        # Preserve catalogue IMDb ID if metadata has no ID.
        movie["imdb_id"] = (
            details.get("imdb_id")
            or movie.get("imdb_id")
        )

        movie["imdb_rating"] = details.get("imdb_rating")

        if not movie.get("plot") or movie.get("plot") == "Information currently unavailable":
            movie["plot"] = (
                details.get("plot")
                or movie.get("plot")
            )

        if not movie.get("poster"):
            movie["poster"] = details.get("poster")

    save_recommendations(
        session["user_id"],
        recommendations,
        mode=mode,
    )

    return jsonify({
        "session_id": session_id,
        "mode": mode,
        "complete": True,
        "count": len(recommendations),
        "recommendations": recommendations,
        "notice": (
            "Recommendations are selected from the local MoodFlix catalogue. "
            "OMDb and Watchmode enrich verified details and India OTT availability; "
            "dubbing remains unknown unless sourced."
        ),
        "can_relax_constraints": len(recommendations) < 3,
        "relaxation_prompt": (
            "We found fewer than three strong matches. "
            "Would you like to relax a language or runtime constraint?"
            if len(recommendations) < 3
            else None
        ),
    }), 200


@discovery_bp.get("/movies/upcoming")
def upcoming_movies():
    """Upcoming-release discovery is unavailable under current API policy."""
    return jsonify({
        "error": (
            "Upcoming release discovery is not supported by the "
            "configured OMDb and Watchmode integrations."
        ),
        "movies": [],
        "count": 0,
    }), 501

@discovery_bp.get("/movies/<path:movie_key_value>/audio-languages")
def audio_languages(movie_key_value):
    """Expose only sourced audio-language statuses; unknown is the safe default."""
    with get_db() as db:
        rows = db.execute("SELECT language_code,status,source,checked_at FROM movie_audio_languages WHERE movie_key=?", (movie_key_value,)).fetchall()
    return jsonify({"movie_key": movie_key_value, "audio_languages": [dict(row) for row in rows],
                    "default_status": "unknown"}), 200


@discovery_bp.get("/movies/<path:movie_key_value>/ott")
def movie_ott(movie_key_value):
    """India OTT availability for any movie: stored rows first, then a live Watchmode lookup."""
    title = request.args.get("title", "").strip()
    year = request.args.get("year", "").strip()
    keys = [movie_key_value]
    if title:
        keys.append(f"title:{title.casefold()}:{year}")
    with get_db() as db:
        rows = []
        for key in keys:
            rows = db.execute("SELECT provider,access_type,source,checked_at FROM ott_availability "
                              "WHERE movie_key=? AND region='IN'", (key,)).fetchall()
            if rows:
                break
    if rows:
        sources = [{"platform": row["provider"], "availability": row["access_type"],
                    "availability_label": None, "url": None} for row in rows]
        return jsonify({"movie_key": movie_key_value, "ott_availability": sources, "source": "stored"}), 200
    if title:
        from app.routes.recommendation_routes import get_movie_metadata
        metadata = get_movie_metadata(title, year or None)
        return jsonify({"movie_key": movie_key_value, "ott_availability": metadata.get("ott_availability", []),
                        "source": "live"}), 200
    return jsonify({"movie_key": movie_key_value, "ott_availability": [], "source": "none"}), 200