"""Starter scoring for MoodFlix's adaptive-style thriller discovery quiz.

This seed catalog is intentionally small. Replace/augment it with a global
local curated catalogue enriched only by the configured OMDb and Watchmode services.
"""

THRILLERS = [
    {"title":"Drishyam", "year":2013, "languages":["Malayalam"], "country":"India", "type":["murder mystery","crime investigation","mind-blowing twists"], "story":["intelligent screenplay","suspense until the end","satisfying climax"], "pace":"medium", "ending":["clever and logical","emotional and satisfying"], "complexity":"complex puzzle", "atmosphere":["realistic crime","tense and claustrophobic"], "comedy":"almost none", "style":["highly rated masterpieces","movies with insane twists"]},
    {"title":"Ratsasan", "year":2018, "languages":["Tamil"], "country":"India", "type":["murder mystery","psychological thriller","crime investigation"], "story":["suspense until the end","unpredictable story"], "pace":"fast", "ending":["completely unexpected","dark and disturbing"], "complexity":"some clues to solve", "atmosphere":["dark and gritty","realistic crime"], "comedy":"almost none", "style":["underrated thrillers","movies with insane twists"]},
    {"title":"Vikram Vedha", "year":2017, "languages":["Tamil"], "country":"India", "type":["crime investigation","psychological thriller"], "story":["intelligent screenplay","unpredictable story"], "pace":"fast", "ending":["clever and logical","ambiguous, open to interpretation"], "complexity":"complex puzzle", "atmosphere":["stylish and fun","realistic crime"], "comedy":"some humor", "style":["highly rated masterpieces","a mix of everything"]},
    {"title":"Maharaja", "year":2024, "languages":["Tamil"], "country":"India", "type":["mind-blowing twists","crime investigation"], "story":["unpredictable story","suspense until the end"], "pace":"medium", "ending":["completely unexpected","dark and disturbing"], "complexity":"complex puzzle", "atmosphere":["dark and gritty","realistic crime"], "comedy":"almost none", "style":["underrated thrillers","movies with insane twists"]},
    {"title":"Agent Sai Srinivasa Athreya", "year":2019, "languages":["Telugu"], "country":"India", "type":["murder mystery","crime investigation"], "story":["intelligent screenplay","unpredictable story"], "pace":"medium", "ending":["clever and logical","emotional and satisfying"], "complexity":"some clues to solve", "atmosphere":["stylish and fun","realistic crime"], "comedy":"some humor", "style":["hidden gems nobody talks about","underrated thrillers"]},
    {"title":"Drishyam 2", "year":2021, "languages":["Malayalam"], "country":"India", "type":["mind-blowing twists","murder mystery"], "story":["intelligent screenplay","suspense until the end"], "pace":"slow", "ending":["clever and logical","completely unexpected"], "complexity":"extremely complicated; i want to think hard", "atmosphere":["realistic crime","tense and claustrophobic"], "comedy":"almost none", "style":["highly rated masterpieces","movies with insane twists"]},
    {"title":"Anjaam Pathiraa", "year":2020, "languages":["Malayalam"], "country":"India", "type":["murder mystery","crime investigation"], "story":["suspense until the end","unpredictable story"], "pace":"fast", "ending":["dark and disturbing","completely unexpected"], "complexity":"some clues to solve", "atmosphere":["dark and gritty","realistic crime"], "comedy":"almost none", "style":["underrated thrillers","a mix of everything"]},
    {"title":"Memories", "year":2013, "languages":["Malayalam"], "country":"India", "type":["murder mystery","crime investigation"], "story":["suspense until the end","intelligent screenplay"], "pace":"medium", "ending":["emotional and satisfying","completely unexpected"], "complexity":"some clues to solve", "atmosphere":["dark and gritty","realistic crime"], "comedy":"almost none", "style":["hidden gems nobody talks about","underrated thrillers"]},
    {"title":"Ratsasan", "year":2018, "languages":["Tamil"], "country":"India", "type":["psychological thriller","murder mystery"], "story":["suspense until the end","unpredictable story"], "pace":"fast", "ending":["dark and disturbing","completely unexpected"], "complexity":"complex puzzle", "atmosphere":["dark and gritty","tense and claustrophobic"], "comedy":"almost none", "style":["movies with insane twists","highly rated masterpieces"]},
    {"title":"Andhadhun", "year":2018, "languages":["Hindi"], "country":"India", "type":["mind-blowing twists","murder mystery"], "story":["unpredictable story","intelligent screenplay"], "pace":"medium", "ending":["ambiguous, open to interpretation","completely unexpected"], "complexity":"complex puzzle", "atmosphere":["stylish and fun","unusual and surreal"], "comedy":"some humor", "style":["highly rated masterpieces","movies with insane twists"]},
    {"title":"Talaash", "year":2012, "languages":["Hindi"], "country":"India", "type":["psychological thriller","murder mystery"], "story":["intelligent screenplay","suspense until the end"], "pace":"slow", "ending":["emotional and satisfying","ambiguous, open to interpretation"], "complexity":"complex puzzle", "atmosphere":["tense and claustrophobic","unusual and surreal"], "comedy":"almost none", "style":["underrated thrillers","a mix of everything"]},
    {"title":"Kahaani", "year":2012, "languages":["Hindi"], "country":"India", "type":["mind-blowing twists","crime investigation"], "story":["unpredictable story","suspense until the end"], "pace":"medium", "ending":["completely unexpected","clever and logical"], "complexity":"some clues to solve", "atmosphere":["realistic crime","tense and claustrophobic"], "comedy":"almost none", "style":["highly rated masterpieces","underrated thrillers"]},
    {"title":"Gone Girl", "year":2014, "languages":["English"], "country":"United States", "type":["psychological thriller","mind-blowing twists"], "story":["unpredictable story","intelligent screenplay"], "pace":"slow", "ending":["dark and disturbing","ambiguous, open to interpretation"], "complexity":"complex puzzle", "atmosphere":["dark and gritty","tense and claustrophobic"], "comedy":"almost none", "style":["highly rated masterpieces","movies with insane twists"]},
    {"title":"Shutter Island", "year":2010, "languages":["English"], "country":"United States", "type":["psychological thriller","mind-blowing twists"], "story":["intelligent screenplay","unpredictable story"], "pace":"slow", "ending":["ambiguous, open to interpretation","completely unexpected"], "complexity":"extremely complicated; i want to think hard", "atmosphere":["dark and gritty","unusual and surreal"], "comedy":"almost none", "style":["highly rated masterpieces","movies with insane twists"]},
    {"title":"Prisoners", "year":2013, "languages":["English"], "country":"United States", "type":["crime investigation","psychological thriller"], "story":["suspense until the end","intelligent screenplay"], "pace":"slow", "ending":["dark and disturbing","ambiguous, open to interpretation"], "complexity":"complex puzzle", "atmosphere":["dark and gritty","tense and claustrophobic"], "comedy":"almost none", "style":["highly rated masterpieces","underrated thrillers"]},
    {"title":"Knives Out", "year":2019, "languages":["English"], "country":"United States", "type":["murder mystery","crime investigation"], "story":["intelligent screenplay","satisfying climax"], "pace":"medium", "ending":["clever and logical","emotional and satisfying"], "complexity":"some clues to solve", "atmosphere":["stylish and fun","realistic crime"], "comedy":"some humor", "style":["highly rated masterpieces","a mix of everything"]},
    {"title":"The Prestige", "year":2006, "languages":["English"], "country":"United Kingdom", "type":["mind-blowing twists","psychological thriller"], "story":["intelligent screenplay","unpredictable story"], "pace":"medium", "ending":["completely unexpected","clever and logical"], "complexity":"extremely complicated; i want to think hard", "atmosphere":["unusual and surreal","dark and gritty"], "comedy":"almost none", "style":["highly rated masterpieces","movies with insane twists"]},
]


def score_movies(answers):
    """Rank seed titles using user preferences; this is not a global catalog yet."""
    chosen_languages = [str(x).strip().casefold() for x in answers.get("languages", [])]
    if "all languages" in chosen_languages:
        chosen_languages = []
    if "all south indian languages" in chosen_languages:
        chosen_languages.extend(["malayalam", "tamil", "telugu", "kannada"])
    if not chosen_languages:
        chosen_languages = ["hindi", "english", "malayalam", "tamil", "telugu", "kannada"]

    impressed = str(answers.get("example_movie", "")).strip().casefold()
    output = []
    for movie in THRILLERS:
        lang = movie["languages"][0].casefold()
        if lang not in chosen_languages:
            continue
        score = 0
        for key, field in [("thriller_type", "type"), ("story_priority", "story"), ("ending", "ending"), ("atmosphere", "atmosphere"), ("recommendation_style", "style")]:
            answer = str(answers.get(key, "")).strip().casefold()
            if answer and answer in [x.casefold() for x in movie.get(field, [])]:
                score += 3
        pace = str(answers.get("pacing", "")).casefold()
        if pace and ((pace.startswith("love slow") and movie["pace"] == "slow") or (pace.startswith("okay") and movie["pace"] in ("slow", "medium")) or (pace.startswith("prefer medium") and movie["pace"] == "medium") or (pace.startswith("only fast") and movie["pace"] == "fast")):
            score += 2
        complexity = str(answers.get("complexity", "")).casefold()
        if complexity and complexity == movie["complexity"].casefold():
            score += 2
        comedy = str(answers.get("comedy", "")).casefold()
        if comedy and comedy == movie["comedy"].casefold():
            score += 1
        if impressed and impressed != "none of these / haven't watched them" and impressed == movie["title"].casefold():
            score += 2
        output.append({"title": movie["title"], "year": movie["year"], "languages": movie["languages"], "country": movie["country"], "score": score, "why": "Matched your thriller preferences"})
    output.sort(key=lambda item: (-item["score"], -item["year"], item["title"]))
    # Remove duplicate title/year entries.
    seen, unique = set(), []
    for item in output:
        key = (item["title"].casefold(), item["year"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:10]
