import os

import requests
from dotenv import load_dotenv

load_dotenv()

OMDB_BASE_URL = "https://www.omdbapi.com/"


def get_movie_details(title=None, imdb_id=None, year=None):
    """Fetch movie details from OMDb using a title or IMDb ID."""
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        raise RuntimeError("OMDb API key configure nahi hai.")

    if not title and not imdb_id:
        raise ValueError("Movie title ya IMDb ID dena zaroori hai.")

    params = {"apikey": api_key, "plot": "short"}
    if title:
        clean_title = str(title).strip()
        if not clean_title:
            raise ValueError("Movie title empty nahi ho sakta.")
        params["t"] = clean_title
    if imdb_id:
        params["i"] = str(imdb_id).strip()
    if year not in (None, ""):
        params["y"] = str(year).strip()

    response = requests.get(OMDB_BASE_URL, params=params, timeout=15)
    response.raise_for_status()

    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError("OMDb ne valid JSON response nahi diya.") from exc

    if not isinstance(data, dict):
        raise ValueError("OMDb response expected format mein nahi hai.")
    if data.get("Response") != "True":
        return None
    return data


def normalize_movie_details(data):
    """Normalize OMDb data; safely handle missing or malformed fields."""
    if not isinstance(data, dict) or data.get("Response") != "True":
        return None

    try:
        raw_rating = data.get("imdbRating")
        imdb_rating = (
            float(raw_rating)
            if raw_rating not in (None, "", "N/A")
            else None
        )
        if imdb_rating is not None and not 0 <= imdb_rating <= 10:
            imdb_rating = None
    except (TypeError, ValueError, OverflowError):
        imdb_rating = None

    rotten_tomatoes = None
    raw_ratings = data.get("Ratings", [])
    if isinstance(raw_ratings, list):
        for rating in raw_ratings:
            if not isinstance(rating, dict):
                continue
            if rating.get("Source") != "Rotten Tomatoes":
                continue
            value = rating.get("Value")
            if isinstance(value, str) and value.endswith("%"):
                try:
                    percentage = int(value[:-1].strip())
                    if 0 <= percentage <= 100:
                        rotten_tomatoes = f"{percentage}%"
                except (TypeError, ValueError):
                    pass
            break

    def split_names(value):
        if not isinstance(value, str) or value.strip() in ("", "N/A"):
            return []
        return [part.strip() for part in value.split(",") if part.strip()]

    def optional_text(value):
        if not isinstance(value, str) or value.strip() in ("", "N/A"):
            return None
        return value.strip()

    return {
        "title": optional_text(data.get("Title")),
        "year": optional_text(data.get("Year")),
        "plot": optional_text(data.get("Plot")),
        "poster": optional_text(data.get("Poster")),
        "genres": split_names(data.get("Genre", "")),
        "actors": split_names(data.get("Actors", "")),
        "director": optional_text(data.get("Director")),
        "runtime": optional_text(data.get("Runtime")),
        "language": split_names(data.get("Language", "")),
        "country": split_names(data.get("Country", "")),
        "imdb_rating": imdb_rating,
        "rotten_tomatoes": rotten_tomatoes,
        "imdb_id": optional_text(data.get("imdbID")),
    }
