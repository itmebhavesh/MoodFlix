import csv
import copy
import csv
import gzip
import hashlib
import json
import os
import requests
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid
from datetime import datetime

from flask import Blueprint, Response, jsonify, request, session
from app.security import rate_limit

import os
import requests
import threading
from pathlib import Path
import uuid
from datetime import datetime
from functools import lru_cache

from flask import Blueprint, jsonify, request, session

from app.recommendation.adaptive_question_engine import (
    ANY_VALUE,
    get_next_question,
    filter_candidates,
)
from app.recommendation.movie_loader import load_movies, get_recommendations
from app.recommendation.recommendation_engine import explain_recommendation
from app.services.omdb_service import get_movie_details, normalize_movie_details
from app.services.watchmode_service import get_streaming_sources

recommendation_bp = Blueprint("recommendation", __name__)

@recommendation_bp.route("/movies/catalog", methods=["GET"])
def get_movie_catalog():
    """Return movies saved in the OMDb CSV catalogue."""

    project_root = Path(__file__).resolve().parents[2]
    csv_path = project_root / "instance" / "movies_omdb_10000.csv"

    if not csv_path.exists():
        return jsonify({
            "success": False,
            "error": "Movie CSV file not found."
        }), 404

    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
            movies = list(csv.DictReader(file))

        return jsonify({
            "success": True,
            "count": len(movies),
            "movies": movies
        }), 200

    except (OSError, csv.Error, UnicodeError) as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 500
# Development V1: active quiz sessions RAM mein store honge.
# Server restart hone par sessions reset ho jayenge.
_ADAPTIVE_SESSIONS = {}
_ADAPTIVE_LOCK = threading.Lock()
_SESSION_TTL = 30 * 60      # forget quiz sessions after 30 minutes without activity
_SESSION_MAX = 500          # hard cap so the dict cannot grow without limit


def _prune_sessions():
    """Drop expired sessions, then the oldest ones if still above the cap. Call with the lock held."""
    now = time.time()
    for sid in [sid for sid, item in _ADAPTIVE_SESSIONS.items() if now - item.get("touched", now) > _SESSION_TTL]:
        del _ADAPTIVE_SESSIONS[sid]
    while len(_ADAPTIVE_SESSIONS) >= _SESSION_MAX:
        oldest = min(_ADAPTIVE_SESSIONS, key=lambda sid: _ADAPTIVE_SESSIONS[sid].get("touched", 0))
        del _ADAPTIVE_SESSIONS[oldest]

def _fetch_movie_metadata(title, year):
    """Fetch metadata; returns (metadata, ok). ok=False means an API call failed."""
    metadata = {"details": None, "ott_availability": []}
    ok = True
    try:
        raw_details = get_movie_details(title=title, year=year)
        metadata["details"] = normalize_movie_details(raw_details)
        # pehla try/except (OMDb) ka except:
    except (requests.RequestException, RuntimeError, ValueError, TypeError):
        ok = False

    api_key = os.getenv("WATCHMODE_API_KEY")
    if not api_key:
        return metadata, ok

    api_key = os.getenv("WATCHMODE_API_KEY")
    if not api_key:
        return metadata

    try:
        response = requests.get(
            "https://api.watchmode.com/v1/search/",
            params={
                "apiKey": api_key,
                "search_field": "name",
                "search_value": title,
            },
            timeout=15,
        )
        response.raise_for_status()
        search_data = response.json()

        if isinstance(search_data, list):
            search_results = search_data
        elif isinstance(search_data, dict):
            search_results = (
                search_data.get("title_results")
                or search_data.get("search_results")
                or []
            )
        else:
            search_results = []

        if not isinstance(search_results, list):
            search_results = []

        expected_title = str(title).strip().casefold()
        expected_year = str(year).strip() if year else ""
        matching_result = None

        for result in search_results:
            if not isinstance(result, dict):
                continue
            result_title = str(
                result.get("name") or result.get("title") or ""
            ).strip().casefold()
            result_type = str(result.get("type") or "").strip().casefold()
            result_year = str(result.get("year") or "").strip()

            if result_title != expected_title:
                continue
            if result_type and result_type != "movie":
                continue
            if expected_year and result_year and result_year != expected_year:
                continue

            matching_result = result
            break

        if matching_result:
            watchmode_id = (
                matching_result.get("id")
                or matching_result.get("watchmode_id")
            )
            if watchmode_id is not None:
                metadata["ott_availability"] = get_streaming_sources(
                    watchmode_id, region="IN"
                )
                # Store the provider response with region and access-type provenance.
                if metadata["ott_availability"]:
                    from app.database import get_db
                    movie_key = f"title:{str(title).strip().casefold()}:{year or ''}"
                    with get_db() as db:
                        for source in metadata["ott_availability"]:
                            if not isinstance(source, dict):
                                continue
                            provider = source.get("platform") or source.get("name") or source.get("provider")
                            if not provider:
                                continue
                            access_type = source.get("availability") or source.get("type") or source.get("access_type") or "stream"
                            db.execute(
                                "INSERT INTO ott_availability(movie_key,region,provider,access_type,source,checked_at) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP) "
                                "ON CONFLICT(movie_key,region,provider,access_type) DO UPDATE SET source=excluded.source,checked_at=CURRENT_TIMESTAMP",
                                (movie_key, "IN", str(provider), str(access_type), "Watchmode"),
                            )

        # function ke aakhri except aur return ki jagah:
    except (requests.RequestException, RuntimeError, ValueError, TypeError, sqlite3.Error):
        ok = False

    return metadata, ok


@lru_cache(maxsize=512)
def get_movie_metadata(title, year=None):
    """Return cached movie metadata in the dictionary format used by routes."""
    metadata, _ok = _fetch_movie_metadata(title, year)
    return metadata


def format_recommendations(results, mood=None, genre=None, language=None):
    """Convert ranked results into detailed API response objects."""
    recommendations = []
    current_year = datetime.now().year

    for item in results[:10]:
        if not isinstance(item, dict):
            continue

        movie = item.get("movie")
        if not isinstance(movie, dict):
            continue

        try:
            rating = float(movie["rating"])
            runtime = int(movie["runtime"])
            release_year = int(movie["release_year"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue

        if (
            not 0 <= rating <= 10
            or runtime <= 0
            or not 1888 <= release_year <= current_year
        ):
            continue

        title = str(movie.get("title") or "Unknown title")
        metadata = get_movie_metadata(title, release_year)
        details = metadata.get("details") or {}
        rotten_tomatoes = details.get("rotten_tomatoes")

        recommendations.append({
            "title": title,
            "language": movie.get("language", ""),
            "industry": movie.get("industry", ""),
            "genres": [
                value.strip()
                for value in str(movie.get("genres") or "").split("|")
                if value.strip()
            ],
            "moods": [
                value.strip()
                for value in str(movie.get("moods") or "").split("|")
                if value.strip()
            ],
            "rating": rating,
            "runtime": runtime,
            "release_year": release_year,
            "score": item.get("score", 0),
            "reasons": explain_recommendation(
                movie,
                selected_mood=mood,
                selected_genre=genre,
                selected_language=language,
            ),
            "plot": details.get("plot"),
            "poster": details.get("poster"),
            "imdb_id": details.get("imdb_id"),
            "cast": {
                "actors": details.get("actors", []),
                "hero": [],
                "heroine": [],
                "supporting_cast": [],
                "cameos": [],
            },
            "ratings": {
                "imdb": details.get("imdb_rating"),
                "rotten_tomatoes": {
                    "tomatometer": rotten_tomatoes,
                    "audience_score": None,
                },
            },
            "ott_availability": metadata.get("ott_availability", []),
        })

    return recommendations


@recommendation_bp.route("/recommend", methods=["POST"])
def recommend():
    """Existing non-adaptive recommendation endpoint."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    mood = data.get("mood")
    genre = data.get("genre")
    language = data.get("language")
    industry = data.get("industry")

    try:
        min_rating = (
            float(data["min_rating"])
            if data.get("min_rating") not in (None, "")
            else None
        )
        max_runtime = (
            int(data["max_runtime"])
            if data.get("max_runtime") not in (None, "")
            else None
        )
        preferred_year = (
            int(data["preferred_year"])
            if data.get("preferred_year") not in (None, "")
            else None
        )
    except (ValueError, TypeError, OverflowError):
        return jsonify({"error": "Invalid numeric preference."}), 400

    if min_rating is not None and not 0 <= min_rating <= 10:
        return jsonify({"error": "min_rating must be between 0 and 10."}), 400
    if max_runtime is not None and max_runtime <= 0:
        return jsonify({"error": "max_runtime must be greater than 0."}), 400

    current_year = datetime.now().year
    if preferred_year is not None and not 1888 <= preferred_year <= current_year:
        return jsonify({"error": "preferred_year is outside the supported range."}), 400

    try:
        movies = load_movies()
    except (OSError, csv.Error, UnicodeError):
        return jsonify({"error": "Movie catalog could not be loaded."}), 500

    try:
        results = get_recommendations(
            movies,
            mood=mood,
            genre=genre,
            language=language,
            industry=industry,
            min_rating=min_rating,
            max_runtime=max_runtime,
            preferred_year=preferred_year,
        )
    except (ValueError, TypeError, KeyError):
        return jsonify({"error": "Movie recommendations could not be generated."}), 500

    recommendations = format_recommendations(
        results, mood=mood, genre=genre, language=language
    )
    return jsonify({
        "count": len(recommendations),
        "recommendations": recommendations,
    }), 200


@recommendation_bp.route("/recommend/questions", methods=["GET"])
@rate_limit(30, 600)  # 30 new Genie sessions per 10 minutes per IP
def start_adaptive_quiz():
    """Start a quiz session and return the first adaptive question."""
    try:
        movies = load_movies()
    except (OSError, csv.Error, UnicodeError):
        return jsonify({"error": "Movie catalog could not be loaded."}), 500

    if not movies:
        return jsonify({"error": "No movies are available."}), 503

    session_id = str(uuid.uuid4())
    question = get_next_question(movies, [])

    session = {
        "candidates": movies,
        "asked_question_ids": [],
        "answers": [],
        "complete": question is None,
                "complete": question is None,
        "touched": time.time(),
    }
    with _ADAPTIVE_LOCK:
        _prune_sessions()
        _ADAPTIVE_SESSIONS[session_id] = session
        
    recommendations = []
    if question is None:
        try:
            recommendations = format_recommendations(get_recommendations(movies))
        except (ValueError, TypeError, KeyError, RuntimeError):
            return jsonify({"error": "Initial recommendations could not be generated."}), 500

    return jsonify({
        "session_id": session_id,
        "question": question,
        "candidate_count": len(movies),
        "complete": session["complete"],
        "recommendations": recommendations,
    }), 200


@recommendation_bp.route("/recommend/answer", methods=["POST"])
def answer_adaptive_question():
    """Apply an answer and return the next question or detailed recommendations."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

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

    with _ADAPTIVE_LOCK:
        session = _ADAPTIVE_SESSIONS.get(session_id)
        if session is None:
            return jsonify({"error": "Quiz session not found. Start a new quiz."}), 404
            session["touched"] = time.time()
        if session["complete"]:
            return jsonify({"error": "This quiz is already complete."}), 409
            session["touched"] = time.time()

        expected_question = get_next_question(
            session["candidates"], session["asked_question_ids"]
        )

        if expected_question is None:
            session["complete"] = True
        else:
            if question_id != expected_question["id"]:
                return jsonify({
                    "error": "Unexpected question. Answer the current question."
                }), 400

            valid_values = {option["value"] for option in expected_question["options"]}
            if answer not in valid_values:
                return jsonify({"error": "Invalid answer option."}), 400

            try:
                remaining = filter_candidates(session["candidates"], question_id, answer)
            except ValueError:
                return jsonify({"error": "The selected answer is not valid."}), 400

            session["candidates"] = remaining
            session["asked_question_ids"].append(question_id)
            session["answers"].append({"question_id": question_id, "value": answer})

            next_question = get_next_question(
                remaining, session["asked_question_ids"]
            )
            session["complete"] = len(remaining) <= 1 or next_question is None

        final_candidates = list(session["candidates"])
        saved_answers = list(session["answers"])
        complete = session["complete"]
        response = {
            "session_id": session_id,
            "complete": complete,
            "question": (
                None if complete else get_next_question(
                    session["candidates"], session["asked_question_ids"]
                )
            ),
            "candidate_count": len(final_candidates),
            "recommendations": [],
        }

    if not complete:
        return jsonify(response), 200

    preferences = {}
    for saved_answer in saved_answers:
        if saved_answer["value"] != ANY_VALUE:
            preferences[saved_answer["question_id"]] = saved_answer["value"]

    try:
        ranked_results = get_recommendations(
            final_candidates,
            mood=preferences.get("moods"),
            genre=preferences.get("genres"),
            language=preferences.get("language"),
            industry=preferences.get("industry"),
        )
        recommendations = format_recommendations(
            ranked_results,
            mood=preferences.get("moods"),
            genre=preferences.get("genres"),
            language=preferences.get("language"),
        )
    except (ValueError, TypeError, KeyError, RuntimeError):
        return jsonify({"error": "Final recommendations could not be generated."}), 500

    response["recommendations"] = recommendations
    response["candidate_count"] = len(recommendations)
    return jsonify(response), 200


@recommendation_bp.route("/recommend/finish", methods=["POST"])
def finish_adaptive_quiz():
    """Manually finish the quiz and return detailed recommendations."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        return jsonify({"error": "session_id is required."}), 400

    with _ADAPTIVE_LOCK:
        session = _ADAPTIVE_SESSIONS.get(session_id)
        if session is None:
            return jsonify({"error": "Quiz session not found. Start a new quiz."}), 404
        session["complete"] = True
        candidates = list(session["candidates"])
        saved_answers = list(session["answers"])

    preferences = {}
    for saved_answer in saved_answers:
        if saved_answer["value"] != ANY_VALUE:
            preferences[saved_answer["question_id"]] = saved_answer["value"]

    try:
        ranked_results = get_recommendations(
            candidates,
            mood=preferences.get("moods"),
            genre=preferences.get("genres"),
            language=preferences.get("language"),
            industry=preferences.get("industry"),
        )
        recommendations = format_recommendations(
            ranked_results,
            mood=preferences.get("moods"),
            genre=preferences.get("genres"),
            language=preferences.get("language"),
        )
    except (ValueError, TypeError, KeyError, RuntimeError):
        return jsonify({"error": "Final recommendations could not be generated."}), 500

    return jsonify({
        "session_id": session_id,
        "complete": True,
        "candidate_count": len(recommendations),
        "recommendations": recommendations,
    }), 200


@recommendation_bp.route("/thriller-quiz/recommend", methods=["POST"])
def thriller_quiz_recommend():
    """Return ranked starter-catalog matches for the 10-question thriller quiz."""
    from app.recommendation.thriller_quiz import score_movies

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    answers = data.get("answers", data)
    if not isinstance(answers, dict):
        return jsonify({"error": "Answers must be a JSON object."}), 400

    # Blend explicitly liked-movie signals into this account's long-term taste.
    user_id = session.get("user_id")
    if user_id:
        from app.services.preference_service import get_effective_preferences
        learned = get_effective_preferences(user_id)
        answers = dict(answers)
        answers["_profile_genres"] = learned.get("genres", [])
        answers["_profile_languages"] = learned.get("languages", [])

    # The curated local catalogue is the only recommendation discovery source.
    # OMDb and Watchmode enrich matches; neither API invents new catalogue entries.
    matches = score_movies(answers)
    recommendations = []
    for movie in matches:
        metadata = get_movie_metadata(movie["title"], movie.get("year"))
        details = metadata.get("details") or {}
        recommendations.append({
            **movie,
            "plot": details.get("plot") or "Information currently unavailable",
            "poster": details.get("poster"),
            "imdb_id": details.get("imdb_id"),
            "imdb_rating": details.get("imdb_rating"),
            "ott_availability": metadata.get("ott_availability", []),
            "dub_status": "unknown",
            "dubbed_languages": [],
        })
    catalog_scope = "local_curated_catalogue"
    notice = "Recommendations come from the local MoodFlix catalogue. OMDb and Watchmode enrich verified metadata and India OTT availability."

    # Reuse OMDb and Watchmode integrations for the final small result set.
    for movie in recommendations:
        metadata = get_movie_metadata(movie.get("title", ""), movie.get("year"))
        movie["ott_availability"] = metadata.get("ott_availability", [])
        details = metadata.get("details") or {}
        movie["imdb_id"] = movie.get("imdb_id") or details.get("imdb_id")
        movie["imdb_rating"] = movie.get("imdb_rating") or details.get("imdb_rating")
        if not movie.get("plot") or movie.get("plot") == "No synopsis available.":
            movie["plot"] = details.get("plot") or movie.get("plot")
        if not movie.get("poster"):
            movie["poster"] = details.get("poster")
        movie["dub_status"] = "unknown"
        movie["dubbed_languages"] = []

    # Apply per-account suppression only when the caller is authenticated.
    user_id = session.get("user_id")
    if user_id:
        from app.services.user_history_service import get_user_movie_states, movie_key, save_recommendations
        from app.database import get_db
        states = get_user_movie_states(user_id)
        with get_db() as db:
            prior_rows = db.execute(
                "SELECT movie_key FROM recommendation_history WHERE user_id=?", (user_id,)
            ).fetchall()
        prior = {row["movie_key"] for row in prior_rows}
        recommendations = [movie for movie in recommendations
            if movie_key(movie) not in states["watched"]
            and movie_key(movie) not in states["disliked"]
            and movie_key(movie) not in states["hidden"]
            and movie_key(movie) not in prior]
    from app.recommendation.diversity_engine import select_diverse_recommendations
    recommendations = select_diverse_recommendations(recommendations, limit=3)
    if user_id:
        save_recommendations(user_id, recommendations, mode="my_taste")

    return jsonify({
        "count": len(recommendations),
        "recommendations": recommendations,
        "catalog_scope": catalog_scope,
        "notice": notice,
    })
