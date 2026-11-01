# MoodFlix backend upgrade

## Existing routes preserved

- `POST /api/thriller-quiz/recommend` — the existing 10-question My Taste result endpoint.
- `GET /api/recommend/questions`, `POST /api/recommend/answer`, `POST /api/recommend/finish` — existing adaptive API.
- `POST /api/recommend` — existing direct recommendation endpoint.

## New authentication routes

- `POST /api/auth/signup` — JSON: `email`, `password`, optional `display_name`.
- `POST /api/auth/login` — JSON: `email`, `password`.
- `POST /api/auth/logout`.
- `GET /api/auth/me` — requires login.

Authentication uses Flask's signed, HTTP-only session cookie. Set a strong `FLASK_SECRET_KEY` before deployment. Passwords are stored as Werkzeug password hashes, never plaintext.

## New profile and personal-library routes

- `GET /api/profile` — profile and taste preferences.
- `PUT /api/profile` — update `display_name`, `photo_url`, `languages`, `genres`, `favourite_movies`, `favourite_actors`, and/or `settings`.
- `POST /api/profile/preferences/reset` — reset taste preferences without deleting watch history.
- `GET /api/library?status=watched|watchlist|liked|disliked|hidden`.
- `POST /api/library` — JSON: `movie` object and a distinct `status`; `watched_at` and `note` optional.
- `DELETE /api/library/<record_id>`.
- `POST /api/feedback` — JSON: `movie` and `feedback` (`like`, `dislike`, `not_interested`).
- `GET /api/history/recommendations?limit=100`.
- `DELETE /api/history/recommendations`.

Watched, liked, and watchlist are separate states. A watched record does not automatically become liked.

## New adaptive discovery routes

- `POST /api/modes/start` — JSON `{"mode":"today_mood"}` or `{"mode":"surprise_me"}`. Requires login.
- `POST /api/modes/answer` — JSON `session_id`, `question_id`, `answer`. Requires login. Returns the next question or up to three diverse recommendations.
- My Taste remains on the existing 10-question thriller quiz endpoint.
- `GET /api/movies/upcoming?region=IN&limit=20` — TMDB upcoming release dates only; no city-level theatres or showtimes.
- `GET /api/movies/<movie_key>/audio-languages` — returns only sourced language rows; absent evidence is `unknown`.

## Movie database

SQLite is initialized automatically at `instance/moodflix.sqlite3` (or `MOODFLIX_DATABASE`). Tables include users, preferences, movies, user movie states, recommendation history, quiz sessions, feedback, audio-language evidence, and OTT availability.

To populate up to 10,000 TMDB records, configure `TMDB_API_KEY` and run:

```bash
python scripts/sync_tmdb_catalog.py --target 10000
```

This sync has not been run automatically; it requires the user's API key and network access. TMDB live discovery also remains available. OTT data is only populated when Watchmode is configured and can match a title. Dubbing is never inferred from original language; missing evidence remains unknown.

## Setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
python run.py
```

## Browser pages and discovery controls

- `/login`, `/signup`, `/profile` are included as lightweight browser pages.
- The home page keeps the original 10-question My Taste thriller quiz and adds Surprise Me / Today's Mood mode controls.
- The adaptive modes support 5 questions by default and a conditional sixth question when the earlier answer makes it useful.
- Recommendation cards let a signed-in user save a movie to Watchlist, mark it Watched, or send Like / Dislike / Not Interested feedback.

## Recommendation rules implemented

- The mode-based discovery scorer uses the agreed normalized weighting: `0.40M + 0.25T + 0.20D + 0.15Q`.
- Up to three recommendations are selected with genre novelty where metadata permits; results are not padded when fewer matches remain.
- Watched, disliked, hidden, and previously recommended titles are suppressed per user. Recommendation history can be cleared explicitly.
- Runtime bands are checked against TMDB runtime when the provider returns it. Unknown runtime is marked `unknown` rather than guessed.
- Audio-language status defaults to `unknown`. The persistence helper requires a provenance source before saving `available` or `not_available`.
- Watchmode India provider results are attached to recommendation results when configured and cached in the OTT table with region and access-type details.

## Validation

The bundled regression suite currently passes 43 tests. It includes the original recommendation and metadata tests plus signup/login, private per-user history, distinct watched/watchlist state, feedback, and adaptive-mode coverage. External TMDB / OMDb / Watchmode calls and the 10,000-record sync require the user's API keys and have not been run as part of the test suite.
- Upcoming release dates can be requested generally with `/api/movies/upcoming?region=IN` or for an exact date with `/api/movies/upcoming?region=IN&date=YYYY-MM-DD`.

## External setup and remaining production work

- The 10,000-record sync is a command, not a preloaded dataset. Run it with a valid TMDB key and network access; the uploaded seed CSV itself contains only a few starter rows.
- OMDb and Watchmode enrichment requires their respective API keys. Without them, those fields may be empty.
- No dubbing provider is configured in this project. Therefore, audio-language results remain `unknown` until a verified source is supplied through the evidence helper; original language is not treated as dubbing proof.
- Recommendation scoring is transparent weighted/heuristic ranking over provider metadata, not a trained machine-learning model. Explicit likes contribute genres/languages to the long-term taste signal; disliked and hidden items are suppressed.
- SQLite is the implemented persistence backend. PostgreSQL migration, email verification, password reset, rate limiting, CSRF-token enforcement, and production deployment hardening remain follow-up work.
- Profile photo is currently stored as a URL; image upload/storage is not configured.
