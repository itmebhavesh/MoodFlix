# MoodFlix Quiz — Phase 1

## What changed
- Replaced the filter form with a quiz-first interface.
- Added the 10 thriller-preference questions.
- Language question supports multiple selections.
- Movie-example options change based on selected languages.
- Added `POST /api/thriller-quiz/recommend` and a starter preference-ranking catalog.
- Existing `/api/recommend` endpoint is retained for compatibility, but it is no longer the homepage flow.

## Important scope note
The starter thriller catalog is a small seed list used to implement and test the quiz flow. It is NOT a complete global movie database. The next phase should connect a global provider (for example TMDB Discover/Search), cache results, and rank the provider-backed candidate pool with the same quiz answers. OMDb and Watchmode enrich data where API keys and coverage permit.

## Install / run
1. Extract the ZIP.
2. Open the `movie_recommender` folder in VS Code.
3. Activate your existing Windows virtual environment.
4. Install requirements if needed: `pip install -r requirements.txt`.
5. Keep your local `.env` file private; the ZIP intentionally excludes it. `.env.example` is provided as a template.
6. Run `python run.py` and open `http://127.0.0.1:5000`.

## Endpoint
`POST /api/thriller-quiz/recommend`

Example body:
```json
{
  "answers": {
    "thriller_type": "Mind-blowing twists",
    "story_priority": "Unpredictable story",
    "pacing": "Love slow-burn stories",
    "ending": "Completely unexpected",
    "complexity": "Complex puzzle",
    "atmosphere": "Dark and gritty",
    "comedy": "Almost none",
    "languages": ["Hindi", "Malayalam"],
    "example_movie": "Drishyam",
    "recommendation_style": "Movies with insane twists"
  }
}
```

## Phase 2: TMDB global discovery

The quiz recommendation endpoint now uses `app/services/tmdb_service.py` when `TMDB_API_KEY` is configured. It discovers a broad candidate pool from TMDB's movie discovery API, filters by selected original language(s), and ranks candidates using quiz preferences, genre metadata, popularity/votes, and ratings. Posters and synopsis are returned directly from TMDB metadata. Without a key, it clearly falls back to the small starter seed.

### Enable TMDB data
1. Create a TMDB account and request an API key from TMDB's account API settings.
2. Add `TMDB_API_KEY=your_actual_key` to your local `.env` file. Do not share the key or upload `.env` publicly.
3. Ensure `requests` is installed: `pip install -r requirements.txt`.
4. Restart Flask and submit the quiz again. The endpoint response should show `catalog_scope: "tmdb_global_discovery"` when live discovery is enabled.

This is live discovery, not a complete offline download of every movie. TMDB API terms, pagination, and available metadata apply. Endings, pacing, and comedy are not reliable structured TMDB fields, so those quiz answers currently have limited influence compared with genre, language, rating, and popularity. Streaming availability is still handled separately by Watchmode where available.
