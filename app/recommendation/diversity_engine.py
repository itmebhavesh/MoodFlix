"""Select up to three recommendations with deliberately different experiences."""


def select_diverse_recommendations(movies, limit=3):
    """Greedily prefer different primary genres while retaining ranking quality."""
    roles = ("Best Match", "Different Experience", "Surprise Discovery")
    remaining = list(movies or [])
    selected, used_genres, used_keys = [], set(), set()
    while remaining and len(selected) < min(limit, len(roles)):
        best_index, best_value = 0, None
        for index, movie in enumerate(remaining):
            genres = set(movie.get("genres") or [])
            if not genres and movie.get("genre_ids"):
                genres = {str(value) for value in movie["genre_ids"]}
            novelty = len(genres - used_genres)
            score = float(movie.get("score") or 0)
            # First slot prioritizes score; later slots balance score and novelty.
            value = score if not selected else score + novelty * 1.75
            if best_value is None or value > best_value:
                best_index, best_value = index, value
        movie = remaining.pop(best_index)
        key = (str(movie.get("imdb_id") or movie.get("title", "")).casefold(), movie.get("year"))
        if key in used_keys:
            continue
        used_keys.add(key)
        genres = set(movie.get("genres") or [])
        if not genres and movie.get("genre_ids"):
            genres = {str(value) for value in movie["genre_ids"]}
        used_genres.update(genres)
        movie["recommendation_role"] = roles[len(selected)]
        selected.append(movie)
    return selected
