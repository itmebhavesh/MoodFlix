# MoodFlix frontend (integrated with the Flask backend)

Run: double-click START.bat  (or: python -m venv venv, venv\Scripts\activate, pip install -r requirements.txt, python run.py)
Open: http://127.0.0.1:5000   (put your own .env next to run.py; see .env.example)

## Files (frontend only)
app/templates/index.html            shell (header, search, nav)
app/templates/login|signup|profile.html   redirect old URLs to the SPA (#login, #signup, #profile)
app/static/css/moodflix.css
app/static/js/core.js               API client, session, library state, cards, detail, OTT, actions
app/static/js/browse.js             home (870 catalog), search, title page, library, profile, auth
app/static/js/discover.js           Today's Mood, Surprise Me, Thriller Quiz, Genie guess, My Taste
app/static/js/recommender.js        router + boot
(app/static/js/modes.js is the old backend demo script; it is no longer loaded.)

## Pages (hash routes)
#home  #discover  #mood  #surprise  #thriller  #genie  #taste  #library[-watchlist|-watched|-liked|-disliked|-hidden]  #profile  #login  #signup
Protected (login needed): #mood #surprise #taste #library #profile. Library/feedback buttons ask for login.

## Backend API used
GET  /api/movies/catalog                       home rows, browse, search (870 movies, client-side search)
POST /api/auth/signup|login|logout, GET /api/auth/me
GET|PUT /api/profile, POST /api/profile/preferences/reset
GET|POST /api/library, DELETE /api/library/<id>
POST /api/feedback                              like | dislike | not_interested
GET|DELETE /api/history/recommendations
POST /api/modes/start, /api/modes/answer        Today's Mood, Surprise Me
POST /api/thriller-quiz/recommend               10-question quiz
GET /api/recommend/questions, POST .../answer, .../finish   Quick Genie Guess (no login)
GET /api/movies/<key>/audio-languages           dubbing evidence (only sourced rows are shown, else "unknown")

## Backend issues found while integrating (for the backend owner)
1. Language mismatch in modes: data/movies.csv stores codes (hi, en) but /api/modes/answer compares
   with full names (hindi, english) -> choosing Hindi/English (or having profile languages) returns 0 results.
   Fix: map code->name (or compare both) in discovery_routes.py.
2. Modes use data/movies.csv (4 movies) and the thriller quiz uses a 17-title list. The 870-movie catalog
   (instance/movies_omdb_10000.csv) is used for browse/search only, not recommendations.
3. DELETE /api/library/<id> removes only user_movies. user_feedback keeps the row, so an "un-hidden" or
   "un-disliked" movie is still suppressed in recommendations. Also delete the matching user_feedback row.
4. No endpoint returns OTT for an arbitrary catalog movie; OTT appears only inside recommendation results
   (needs WATCHMODE_API_KEY). Suggest GET /api/movies/<key>/ott reading the ott_availability table.
5. PUT /api/profile cannot clear photo_url (COALESCE keeps the old value).
6. Set FLASK_SECRET_KEY in .env (sessions use a dev default otherwise).
