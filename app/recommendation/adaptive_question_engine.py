
"""
MoodFlix - Adaptive Question Engine V1

Yeh module:
1. Current candidate movies ke basis par question choose karta hai.
2. User ke answer ke basis par movies filter karta hai.
3. Already-asked questions ko repeat nahi karta.
4. Useful question na hone par None return karta hai.
"""


# Available movie fields aur unke question texts.
QUESTION_TEMPLATES = {
    "moods": "Which mood of movie do you want to watch?",
    "genres": "Which movie genre do you like?",
    "language": "In which language do you want to watch the movie?",
    "industry": "Which film industry's movie do you want to watch?",
}

# Is answer ka matlab hai ki user ki koi specific preference nahi hai.
ANY_VALUE = "__any__"


def normalize_values(value):
    """String, list ya tuple ko lowercase values ki list mein badlo."""

    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        raw_values = str(value).split("|")

    return [
        str(item).strip().lower()
        for item in raw_values
        if str(item).strip()
    ]


def get_movie_values(movie, field):
    """Movie ke field ki normalized values return karo."""
    return normalize_values(movie.get(field))


def get_question_options(candidates, field):
    """Current movies se unique options nikalo."""

    values = set()

    for movie in candidates:
        values.update(get_movie_values(movie, field))

    return sorted(values)


def calculate_question_score(candidates, field, options):
    """
    Balanced groups banane wale question ko preference do.
    Yeh simple heuristic hai; multi-value fields mein groups overlap kar sakte hain.
    """

    if len(candidates) < 2 or len(options) < 2:
        return -1

    counts = [
        sum(
            1
            for movie in candidates
            if option in get_movie_values(movie, field)
        )
        for option in options
    ]

    positive_counts = [count for count in counts if count > 0]

    if len(positive_counts) < 2:
        return -1

    return min(positive_counts) / max(positive_counts)


def get_next_question(candidates, asked_question_ids=None):
    """Best available question return karo, ya None."""

    asked_question_ids = set(asked_question_ids or [])

    if len(candidates) < 2:
        return None

    best_question = None
    best_score = -1

    for field, question_text in QUESTION_TEMPLATES.items():

        # Pehle poochha hua question dobara mat poochho.
        if field in asked_question_ids:
            continue

        options = get_question_options(candidates, field)

        if len(options) < 2:
            continue

        score = calculate_question_score(
            candidates,
            field,
            options,
        )

        if score > best_score:
            best_score = score
            best_question = {
                "id": field,
                "field": field,
                "text": question_text,
                "options": [
                    {
                        "label": option.title(),
                        "value": option,
                    }
                    for option in options
                ] + [
                    {
                        "label": "No preference",
                        "value": ANY_VALUE,
                    }
                ],
            }

    return best_question


def filter_candidates(candidates, question_id, answer):
    """Ek answer ke basis par candidate movies filter karo."""

    if question_id not in QUESTION_TEMPLATES:
        raise ValueError(f"Unknown question ID: {question_id}")

    # No preference select karne par current movies retain karo.
    if answer == ANY_VALUE:
        return list(candidates)

    normalized_answer = normalize_values(answer)

    if len(normalized_answer) != 1:
        raise ValueError("Answer must be one option value.")

    answer_value = normalized_answer[0]

    # Sirf current candidates ke valid options accept karo.
    valid_options = get_question_options(candidates, question_id)

    if answer_value not in valid_options:
        raise ValueError(
            f"Invalid answer '{answer_value}' for '{question_id}'."
        )

    return [
        movie
        for movie in candidates
        if answer_value in get_movie_values(movie, question_id)
    ]


def get_remaining_candidates(candidates, answers):
    """Answers ki list ko ek-ek karke apply karo."""

    remaining = list(candidates)

    for answer in answers:
        remaining = filter_candidates(
            remaining,
            answer.get("question_id"),
            answer.get("value"),
        )

    return remaining
