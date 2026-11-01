
from datetime import datetime


def _to_list(value):
    """Convert a single value or multiple values into a clean list."""
    if value is None:
        return []

    if isinstance(value, str):
        return [item.strip().lower() for item in value.split("|") if item.strip()]

    if isinstance(value, (list, tuple, set)):
        return [
            str(item).strip().lower()
            for item in value
            if str(item).strip()
        ]

    return []


def _movie_values(movie, field):
    """Read pipe-separated values from the movie dataset."""
    return _to_list(movie.get(field, ""))


def calculate_score(
    movie,
    selected_mood=None,
    selected_genre=None,
    selected_language=None,
    max_runtime=None,
    preferred_year=None,
):
    score = 0

    movie_moods = _movie_values(movie, "moods")
    movie_genres = _movie_values(movie, "genres")

    selected_moods = _to_list(selected_mood)
    selected_genres = _to_list(selected_genre)
    selected_languages = _to_list(selected_language)

    # 1. Mood match: maximum 30 points
    if selected_moods and set(selected_moods) & set(movie_moods):
        score += 30

    # 2. Genre match: maximum 25 points
    if selected_genres and set(selected_genres) & set(movie_genres):
        score += 25

    # 3. Language match: maximum 15 points
    movie_language = str(movie.get("language", "")).strip().lower()

    if selected_languages and movie_language in selected_languages:
        score += 15

    # 4. Movie rating: maximum 15 points
    try:
        rating = float(movie.get("rating", 0))
        if 0 <= rating <= 10:
            score += (rating / 10) * 15
    except (TypeError, ValueError):
        pass

    # 5. Runtime preference: maximum 10 points
    try:
        runtime = int(movie.get("runtime", 0))

        if max_runtime is not None and runtime > 0:
            if runtime <= int(max_runtime):
                score += 10
    except (TypeError, ValueError):
        pass

    # 6. Release-year preference: maximum 5 points
    try:
        release_year = int(movie.get("release_year", 0))

        if release_year > 0:
            if preferred_year is not None:
                difference = abs(release_year - int(preferred_year))
                score += max(0, 5 - difference / 10)
            else:
                age = max(datetime.now().year - release_year, 0)
                score += max(0, 5 - age / 10)
    except (TypeError, ValueError):
        pass

    return round(score, 2)


def rank_movies(
    movies,
    selected_mood=None,
    selected_genre=None,
    selected_language=None,
    max_runtime=None,
    preferred_year=None,
):
    ranked_movies = []

    for movie in movies:
        score = calculate_score(
            movie,
            selected_mood=selected_mood,
            selected_genre=selected_genre,
            selected_language=selected_language,
            max_runtime=max_runtime,
            preferred_year=preferred_year,
        )

        ranked_movies.append({
            "movie": movie,
            "score": score,
        })

    ranked_movies.sort(
        key=lambda item: (
            item["score"],
            float(item["movie"].get("rating", 0) or 0),
            item["movie"].get("title", "").lower(),
        ),
        reverse=True,
    )

    return ranked_movies


def explain_recommendation(
    movie,
    selected_mood=None,
    selected_genre=None,
    selected_language=None,
):
    reasons = []

    movie_moods = _movie_values(movie, "moods")
    movie_genres = _movie_values(movie, "genres")

    selected_moods = _to_list(selected_mood)
    selected_genres = _to_list(selected_genre)
    selected_languages = _to_list(selected_language)

    matched_moods = sorted(set(selected_moods) & set(movie_moods))
    matched_genres = sorted(set(selected_genres) & set(movie_genres))

    if matched_moods:
        reasons.append(
            "Matches your mood: " + ", ".join(matched_moods)
        )

    if matched_genres:
        reasons.append(
            "Matches your preferred genre: " + ", ".join(matched_genres)
        )

    movie_language = str(movie.get("language", "")).strip().lower()

    if selected_languages and movie_language in selected_languages:
        reasons.append(
            f"Matches your selected language ({movie_language})"
        )

    try:
        rating = float(movie.get("rating", 0))

        if rating >= 8:
            reasons.append(f"Highly rated with a score of {rating}/10")
    except (TypeError, ValueError):
        pass

    if not reasons:
        reasons.append("Recommended based on your available preferences")

    return reasons


def score_discovery_candidates(movies, answers=None, profile=None, mode="today_mood"):
    """Apply MoodFlix's agreed weighted model to provider-backed movie candidates.

    Score = 0.40M + 0.25T + 0.20D + 0.15Q. Each component is normalized
    between 0 and 1; absent evidence contributes zero rather than being guessed.
    """
    answers = answers or {}
    profile = profile or {}
    mood_genres = {
        "happy": {35, 12, 10751}, "fun": {35, 12},
        "sad": {18, 10749}, "thoughtful": {18, 9648},
        "thrilled": {53, 9648, 80}, "scared": {27, 53},
        "relaxed": {16, 10751, 35}, "romantic": {10749, 18},
        "inspired": {18, 36, 99}, "adventurous": {12, 14, 28},
    }
    preferred_genres = {str(value).casefold() for value in profile.get("genres", [])}
    if answers.get("genres") not in (None, "", "any"):
        preferred_genres.add(str(answers["genres"]).replace("_", " ").casefold())
    preferred_languages = {str(value).casefold() for value in profile.get("languages", [])}
    language_code_map = {
        "hindi": "hi", "english": "en", "malayalam": "ml", "tamil": "ta",
        "telugu": "te", "kannada": "kn", "japanese": "ja", "korean": "ko",
        "spanish": "es", "french": "fr", "german": "de", "italian": "it",
        "chinese": "zh", "portuguese": "pt", "thai": "th", "turkish": "tr",
    }
    selected_languages = answers.get("languages")
    if isinstance(selected_languages, str) and selected_languages.casefold() not in ("not_sure", "all languages"):
        preferred_languages.add(selected_languages.casefold())
    mood = str(answers.get("mood", "")).casefold()
    target_genres = mood_genres.get(mood, set())
    scored = []
    for movie in movies:
        genre_ids = set(movie.get("genre_ids") or [])
        movie_genres = {str(value).casefold() for value in movie.get("genres", [])}
        language_code = str(movie.get("language_code") or "").casefold()
        # Current mood dominates Today's Mood; other modes use experience cues.
        mood_match = (len(genre_ids & target_genres) / max(1, len(target_genres))) if target_genres else 0.0
        if mode == "surprise_me":
            experience_genres = {
                "mind_bending": {9648, 878, 53},
                "feel_good": {35, 10749, 10751},
                "adventurous": {12, 14, 28},
            }
            experience = answers.get("experience")
            if experience in experience_genres:
                target = experience_genres[experience]
                mood_match = len(genre_ids & target) / len(target)
            elif experience == "something_new":
                mood_match = 1.0 if int(movie.get("vote_count") or 0) < 1200 else 0.0
        taste_match = 0.0
        if preferred_genres:
            taste_match += 0.7 * (len(preferred_genres & movie_genres) / len(preferred_genres))
        if preferred_languages:
            mapped_languages = {language_code_map.get(value, value) for value in preferred_languages}
            taste_match += 0.3 if language_code in mapped_languages else 0.0
        discovery = 1.0 if int(movie.get("vote_count") or 0) < 1200 else 0.45
        quality = max(0.0, min(1.0, float(movie.get("rating") or movie.get("imdb_rating") or 0) / 10.0))
        final = 0.40 * mood_match + 0.25 * taste_match + 0.20 * discovery + 0.15 * quality
        movie["score_components"] = {"mood_match": round(mood_match, 3), "long_term_taste": round(taste_match, 3), "discovery": round(discovery, 3), "quality": round(quality, 3)}
        movie["score"] = round(final * 100, 2)
        reasons = []
        if mood_match > 0:
            reasons.append("Matches the experience or mood you selected")
        if taste_match > 0:
            reasons.append("Aligns with your saved movie taste")
        if discovery >= 0.8:
            reasons.append("A discovery pick with a smaller vote footprint")
        if quality >= 0.8:
            reasons.append("Has a strong verified movie rating")
        movie["why"] = "; ".join(reasons) if reasons else "Selected from your discovery preferences and available movie data"
        scored.append(movie)
    scored.sort(key=lambda item: (-item["score"], -(item.get("rating") or item.get("imdb_rating") or 0), item.get("title", "").casefold()))
    return scored
