# MoodFlix implementation update

## Applied
- Removed TMDB service usage from the recommendation and adaptive discovery routes.
- Thriller Quiz recommendations now originate from the local curated catalogue.
- Today's Mood and Surprise Me use the local CSV catalogue and the existing adaptive question flow.
- OMDb normalization now includes director, runtime, language, and country.
- User movie identity prefers IMDb ID, then normalized title/year.
- Adaptive mode cards show Watchmode India availability with provider links when present.
- Hindi dubbing remains unknown unless independently verified evidence is stored.
- Upcoming-release endpoint returns HTTP 501 because OMDb/Watchmode integration does not provide a supported upcoming-release feed in this project.
- `modes.js` is now loaded by the main page.

## Important limitations
- This update does not invent or pad catalogue records. The supplied `movies.csv` is a small seed catalogue; expand it only with real records you have verified.
- OMDb and Watchmode keys are optional at startup. Without keys, metadata/availability should remain unavailable rather than preventing local recommendations.
- Existing SQLite `tmdb_id` column is left in place as a harmless legacy schema column so existing databases are not destructively migrated. No updated application code uses it.
- Existing recommendation-history rows keyed by old TMDB IDs may not automatically match the new IMDb/title keys. New writes use the new key format.
- The 10-question Thriller Quiz flow and existing auth/profile routes were not intentionally redesigned.

## Run checks
`python -m compileall app`
