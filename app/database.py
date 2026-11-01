"""MoodFlix SQLite persistence layer.

All database access is intentionally kept in this small module so the app can
start with SQLite and later move to PostgreSQL behind the same service API.
"""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager


def database_path():
    """Return the configured database path, creating its parent directory."""
    configured = os.getenv("MOODFLIX_DATABASE", "instance/moodflix.sqlite3")
    path = Path(configured)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_db():
    """Yield a row-aware SQLite connection and always close it safely."""
    connection = sqlite3.connect(str(database_path()))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    """Create all application tables and indexes if they do not exist."""
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            photo_url TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            languages_json TEXT NOT NULL DEFAULT '[]',
            genres_json TEXT NOT NULL DEFAULT '[]',
            favourite_movies_json TEXT NOT NULL DEFAULT '[]',
            favourite_actors_json TEXT NOT NULL DEFAULT '[]',
            settings_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tmdb_id INTEGER UNIQUE,
            imdb_id TEXT,
            title TEXT NOT NULL,
            release_date TEXT,
            original_language TEXT,
            overview TEXT,
            poster_path TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            movie_key TEXT NOT NULL,
            title TEXT NOT NULL,
            release_year INTEGER,
            status TEXT NOT NULL CHECK(status IN ('watched','watchlist','liked','disliked','hidden')),
            watched_at TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, movie_key, status)
        );
        CREATE TABLE IF NOT EXISTS recommendation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            movie_key TEXT NOT NULL,
            title TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'my_taste',
            role TEXT,
            score REAL,
            reason TEXT,
            recommended_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS quiz_sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            mode TEXT NOT NULL,
            answers_json TEXT NOT NULL DEFAULT '{}',
            asked_json TEXT NOT NULL DEFAULT '[]',
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            movie_key TEXT NOT NULL,
            feedback TEXT NOT NULL CHECK(feedback IN ('like','dislike','not_interested')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, movie_key)
        );
        CREATE TABLE IF NOT EXISTS movie_audio_languages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_key TEXT NOT NULL,
            language_code TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('available','not_available','unknown')) DEFAULT 'unknown',
            source TEXT,
            checked_at TEXT,
            UNIQUE(movie_key, language_code)
        );
        CREATE TABLE IF NOT EXISTS ott_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_key TEXT NOT NULL,
            region TEXT NOT NULL DEFAULT 'IN',
            provider TEXT NOT NULL,
            access_type TEXT,
            source TEXT,
            checked_at TEXT,
            UNIQUE(movie_key, region, provider, access_type)
        );
        CREATE INDEX IF NOT EXISTS idx_user_movies_user_status ON user_movies(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_history_user_movie ON recommendation_history(user_id, movie_key);
        CREATE INDEX IF NOT EXISTS idx_history_user_date ON recommendation_history(user_id, recommended_at);
        """)
