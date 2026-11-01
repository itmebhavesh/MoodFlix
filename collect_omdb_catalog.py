"""
MoodFlix OMDb catalogue collector
---------------------------------
Collects real movie records from OMDb, resumes after interruption, deduplicates
by IMDb ID, and exports SQLite + CSV.

Setup:
    pip install requests python-dotenv
    Add OMDB_API_KEY=your_key to .env
Run:
    python collect_omdb_catalog.py --target 10000

Important:
- OMDb search is query-based; there is no universal "all movies" endpoint.
- Reaching 10,000 depends on API plan limits, query coverage, and OMDb results.
- The script never fabricates records. It saves progress after every movie.
"""

import argparse
import csv
import os
import random
import sqlite3
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.omdbapi.com/"
DB_PATH = Path("instance/moodflix_catalog.sqlite3")
CSV_PATH = Path("instance/movies_omdb_10000.csv")

# Broad search terms to discover distinct titles. These are search queries,
# not claims about a movie's genre or language.
SEARCH_TERMS = [
    "the", "love", "man", "life", "day", "night", "world", "king", "queen",
    "city", "home", "war", " family", "dream", "dark", "last", "new",
    "great", "little", "big", "blue", "red", "black", "white", "gold",
    "one", "two", "first", "secret", " mystery", " story", "road", "house",
    "heart", "time", " forever", "beautiful", "American", "Indian",
    "Hindi", "English", "Tamil", "Telugu", "Malayalam", "Kannada",
    "Japanese", "Korean", "French", "Spanish", "German", "Italian",
    "Chinese", "animation", "documentary", "comedy", "thriller", "horror",
    "action", "drama", "adventure", "science", "romance", "crime",
    "western", "musical", "history", "sport", "family", "fantasy",
]

COLUMNS = [
    "imdb_id", "title", "year", "rated", "released", "runtime", "genre",
    "director", "writer", "actors", "plot", "language", "country",
    "awards", "poster", "imdb_rating", "imdb_votes", "type",
]


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS omdb_movies (
            imdb_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            year TEXT,
            rated TEXT,
            released TEXT,
            runtime TEXT,
            genre TEXT,
            director TEXT,
            writer TEXT,
            actors TEXT,
            plot TEXT,
            language TEXT,
            country TEXT,
            awards TEXT,
            poster TEXT,
            imdb_rating TEXT,
            imdb_votes TEXT,
            type TEXT,
            collected_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS collector_state (
            state_key TEXT PRIMARY KEY,
            state_value TEXT
        )
    """)
    db.commit()
    return db


def api_get(session, params, timeout=25):
    response = session.get(BASE_URL, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("OMDb returned an unexpected response.")
    return data


def search_page(session, api_key, term, page):
    data = api_get(session, {
        "apikey": api_key,
        "s": term,
        "type": "movie",
        "page": page,
    })
    if data.get("Response") != "True":
        return []
    results = data.get("Search", [])
    return results if isinstance(results, list) else []


def get_details(session, api_key, imdb_id):
    data = api_get(session, {
        "apikey": api_key,
        "i": imdb_id,
        "plot": "full",
    })
    if data.get("Response") != "True":
        return None
    if data.get("Type", "").lower() != "movie":
        return None
    return data


def normalize(data):
    imdb_id = data.get("imdbID")
    title = data.get("Title")
    if not imdb_id or not title or title == "N/A":
        return None

    def clean(value):
        return None if value in (None, "", "N/A") else str(value).strip()

    return {
        "imdb_id": clean(imdb_id),
        "title": clean(title),
        "year": clean(data.get("Year")),
        "rated": clean(data.get("Rated")),
        "released": clean(data.get("Released")),
        "runtime": clean(data.get("Runtime")),
        "genre": clean(data.get("Genre")),
        "director": clean(data.get("Director")),
        "writer": clean(data.get("Writer")),
        "actors": clean(data.get("Actors")),
        "plot": clean(data.get("Plot")),
        "language": clean(data.get("Language")),
        "country": clean(data.get("Country")),
        "awards": clean(data.get("Awards")),
        "poster": clean(data.get("Poster")),
        "imdb_rating": clean(data.get("imdbRating")),
        "imdb_votes": clean(data.get("imdbVotes")),
        "type": "movie",
    }


def save_movie(db, movie):
    db.execute("""
        INSERT INTO omdb_movies (
            imdb_id,title,year,rated,released,runtime,genre,director,writer,
            actors,plot,language,country,awards,poster,imdb_rating,imdb_votes,type
        ) VALUES (
            :imdb_id,:title,:year,:rated,:released,:runtime,:genre,:director,
            :writer,:actors,:plot,:language,:country,:awards,:poster,
            :imdb_rating,:imdb_votes,:type
        )
        ON CONFLICT(imdb_id) DO UPDATE SET
            title=excluded.title, year=excluded.year, rated=excluded.rated,
            released=excluded.released, runtime=excluded.runtime,
            genre=excluded.genre, director=excluded.director,
            writer=excluded.writer, actors=excluded.actors, plot=excluded.plot,
            language=excluded.language, country=excluded.country,
            awards=excluded.awards, poster=excluded.poster,
            imdb_rating=excluded.imdb_rating, imdb_votes=excluded.imdb_votes,
            type=excluded.type
    """, movie)


def export_csv(db):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = db.execute(
        "SELECT " + ",".join(COLUMNS) + " FROM omdb_movies ORDER BY title"
    ).fetchall()
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows([dict(row) for row in rows])
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=10000)
    parser.add_argument("--delay", type=float, default=0.25,
                        help="Pause between API requests; increase if needed.")
    parser.add_argument("--max-pages-per-term", type=int, default=100)
    args = parser.parse_args()

    if args.target < 1:
        parser.error("--target must be positive")

    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        sys.exit("OMDB_API_KEY missing. Put it in your .env file; do not paste it here.")

    db = connect_db()
    session = requests.Session()
    session.headers.update({"User-Agent": "MoodFlix-OMDb-Catalogue-Collector/1.0"})

    existing = db.execute("SELECT COUNT(*) FROM omdb_movies").fetchone()[0]
    print(f"Already collected: {existing:,} unique movies; target: {args.target:,}")

    requests_made = 0
    discovered_ids = set()

    for term in SEARCH_TERMS:
        if existing >= args.target:
            break
        print(f"\nSearching OMDb for: {term!r}")

        for page in range(1, args.max_pages_per_term + 1):
            if existing >= args.target:
                break
            try:
                results = search_page(session, api_key, term, page)
                requests_made += 1
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                print(f"Search error for {term!r} page {page}: {exc}")
                time.sleep(min(30, 2 + page))
                continue

            if not results:
                break

            for item in results:
                imdb_id = item.get("imdbID")
                if not imdb_id or imdb_id in discovered_ids:
                    continue
                discovered_ids.add(imdb_id)

                already = db.execute(
                    "SELECT 1 FROM omdb_movies WHERE imdb_id=?", (imdb_id,)
                ).fetchone()
                if already:
                    continue

                try:
                    details = get_details(session, api_key, imdb_id)
                    requests_made += 1
                    movie = normalize(details) if details else None
                    if movie:
                        save_movie(db, movie)
                        db.commit()
                        existing += 1
                        print(f"[{existing:,}/{args.target:,}] {movie['title']} ({movie['year'] or 'year unknown'})")
                    time.sleep(max(0, args.delay))
                except (requests.RequestException, ValueError, RuntimeError) as exc:
                    print(f"Details error for {imdb_id}: {exc}")
                    time.sleep(2)

                if existing >= args.target:
                    break

            # OMDb returns at most 10 search results per page.
            if len(results) < 10:
                break
            time.sleep(max(0, args.delay))

    total = export_csv(db)
    print("\nCollection finished or available search terms exhausted.")
    print(f"Unique verified movie records: {total:,}")
    print(f"SQLite: {DB_PATH}")
    print(f"CSV:    {CSV_PATH}")
    print(f"Approximate API requests made this run: {requests_made:,}")
    if total < args.target:
        print(
            "Target not reached. The collector is resumable: add more search "
            "terms / use an OMDb plan with sufficient request quota, then run "
            "the same command again. No placeholder records were added."
        )
    db.close()


if __name__ == "__main__":
    main()
