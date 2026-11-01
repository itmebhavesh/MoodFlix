import csv
from pathlib import Path
from app.recommendation.recommendation_engine import rank_movies


# Ek value ya multiple values ko clean lowercase list mein convert karta hai.
def normalize_values(value):
    # Preference nahi di gayi ho, toh empty list return karo.
    if value is None:
        return []

    # String ko "|" ke basis par split karke list banao.
    if isinstance(value, str):
        return [
            item.strip().lower()
            for item in value.split("|")
            if item.strip()
        ]

    # Agar multiple values list, tuple ya set mein hon.
    if isinstance(value, (list, tuple, set)):
        return [
            str(item).strip().lower()
            for item in value
            if str(item).strip()
        ]

    # Unsupported input par empty list return karo.
    return []


def load_movies():
    project_root = Path(__file__).resolve().parents[2]

    # OMDb catalog CSV ka path
    csv_path = project_root / "instance" / "movies_omdb_10000.csv"

    movies = []
    print("CSV path:", csv_path)
    print("File exists:", csv_path.exists())
    with open(
        csv_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            # Runtime: "90 min" -> 90
            runtime_text = row.get("runtime", "")
            runtime_digits = "".join(
                char for char in runtime_text
                if char.isdigit()
            )

            runtime = int(runtime_digits) if runtime_digits else None

            # IMDb rating ko number mein convert karo
            try:
                rating = float(row["imdb_rating"])
            except (ValueError, TypeError, KeyError):
                rating = None

            # Genres: comma-separated -> pipe-separated
            genres = [
                item.strip().lower()
                for item in row.get("genre", "").split(",")
                if item.strip()
            ]

            # Languages ko preserve aur normalize karo
            languages = [
                item.strip().lower()
                for item in row.get("language", "").split(",")
                if item.strip()
            ]

            movie = {
                **row,

                "title": row.get("title", "").strip(),
                "year": row.get("year", ""),
                "release_year": row.get("year", ""),

                "runtime": runtime,

                "genre": row.get("genre", ""),
                "genres": "|".join(genres),

                "rating": rating,
                "imdb_rating": rating,

                "language": row.get("language", ""),
                "languages": languages,

                "imdb_id": row.get("imdb_id", ""),
                "poster": row.get("poster", ""),
                "plot": row.get("plot", ""),

                # OMDb CSV mein mood aur industry columns nahi hain
                "moods": "",
                "industry": "",
            }

            if movie["title"]:
                movies.append(movie)

    return movies
def filter_by_mood(movies,selected_mood):
    matching_movies = []

    for movie in movies:
        movie_moods = movie["moods"].split("|")

        if selected_mood.lower()in [
            mood.strip().lower() for mood in movie_moods
            ]:
            matching_movies.append(movie)
    return matching_movies

def filter_by_mood_and_genre(movies, selected_mood, selected_genre):
    matching_movies = []

    for movie in movies:
        movie_moods = [
            mood.strip().lower()
            for mood in movie["moods"].split("|")
        ]

        movie_genres = [
            genre.strip().lower()
            for genre in movie["genres"].split("|")
        ]

        if (
            selected_mood.lower() in movie_moods
            and selected_genre.lower() in movie_genres
        ):
            matching_movies.append(movie)

    return matching_movies



def filter_by_preferences(
    movies,
    selected_mood=None,
    selected_genre=None,
    selected_language=None,
    selected_industry=None,
):
    # User ki preferences ko clean lists mein convert karo.
    selected_moods = normalize_values(selected_mood)
    selected_genres = normalize_values(selected_genre)
    selected_languages = normalize_values(selected_language)
    selected_industries = normalize_values(selected_industry)

    matching_movies = []

    for movie in movies:
        # Movie ke moods aur genres ko bhi clean lists mein badlo.
        movie_moods = normalize_values(movie.get("moods", ""))
        movie_genres = normalize_values(movie.get("genres", ""))

        # Agar selected moods diye hain, toh kam se kam ek mood match hona chahiye.
        if selected_moods and not set(selected_moods).intersection(movie_moods):
            continue

        # Agar selected genres diye hain, toh kam se kam ek genre match hona chahiye.
        if selected_genres and not set(selected_genres).intersection(movie_genres):
            continue

        # Language ko case-insensitive tareeke se compare karo.
        movie_language = normalize_values(movie.get("language", ""))

        if selected_languages and not set(selected_languages).intersection(movie_language):
            continue

        # Industry ke liye bhi case-insensitive matching.
        movie_industry = normalize_values(movie.get("industry", ""))

        if selected_industries and not set(selected_industries).intersection(movie_industry):
            continue

        # Movie saare diye gaye filter groups pass kar gayi.
        matching_movies.append(movie)

    return matching_movies



def filter_by_rating_and_runtime(
    movies,
    min_rating=None,
    max_runtime=None,
):
    # Filter hone ke baad ki movies yahan store hongi.
    matching_movies = []

    for movie in movies:
        # Rating ya runtime missing/invalid hone par error se bachne ke liye
        # try-except ka use kar rahe hain.
        try:
            rating = float(movie.get("rating", ""))
            runtime = int(movie.get("runtime", ""))
        except (TypeError, ValueError):
            # Invalid data wali movie ko filhaal skip kar do.
            continue

        # Valid movie rating 0 se 10 ke beech honi chahiye.
        if not 0 <= rating <= 10:
            continue

        # Runtime positive hona chahiye.
        if runtime <= 0:
            continue

        # Minimum rating se neeche wali movie ko remove karo.
        if min_rating is not None and rating < min_rating:
            continue

        # Maximum runtime se lambi movie ko remove karo.
        if max_runtime is not None and runtime > max_runtime:
            continue

        # Movie sabhi checks pass kar gayi.
        matching_movies.append(movie)

    return matching_movies

def recommend_movies(
        movies,
        mood =None,
        genre =None,
        language =None,
        industry =None,
        min_rating =None,
        max_runtime =None,
):

    results =filter_by_preferences(
        movies,
        selected_mood=mood,
        selected_genre= genre,
        selected_language= language,
        selected_industry= industry,

    )

    results = filter_by_rating_and_runtime(
        results,
        min_rating=min_rating,
        max_runtime= max_runtime,
    )
    return results


def get_recommendations(
    movies,
    mood=None,
    genre=None,
    language=None,
    industry=None,
    min_rating=None,
    max_runtime=None,
    preferred_year=None,
):
    filtered_movies = recommend_movies(
        movies,
        mood=mood,
        genre=genre,
        language=language,
        industry=industry,
        min_rating=min_rating,
        max_runtime=max_runtime,
    )

    ranked_movies = rank_movies(
        filtered_movies,
        selected_mood=mood,
        selected_genre=genre,
        selected_language=language,
        max_runtime=max_runtime,
        preferred_year=preferred_year,
    )

    return ranked_movies

