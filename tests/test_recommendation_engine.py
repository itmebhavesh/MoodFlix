
# unittest Python ka built-in testing module hai.
# Iske liye alag se koi package install nahi karna padega.
import unittest

# Hum apne recommendation engine ke functions import kar rahe hain.
from app.recommendation.recommendation_engine import (
    calculate_score,
    rank_movies,
    explain_recommendation,
)


# Ye class recommendation engine ke tests ko ek jagah rakhti hai.
class TestRecommendationEngine(unittest.TestCase):

    def setUp(self):
        # Har test se pehle ek sample movie banegi.
        # Isse humein baar-baar movie data likhne ki zarurat nahi hai.
        self.movie = {
            "title": "3 Idiots",
            "language": "hi",
            "industry": "Bollywood",
            "genres": "Comedy|Drama",
            "moods": "happy|inspiring",
            "runtime": 170,
            "rating": 8.4,
            "release_year": 2009,
        }

    def test_mood_match_increases_score(self):
        # Matching mood dene par score badhna chahiye.
        matching_score = calculate_score(
            self.movie, selected_mood="happy"
        )

        # Aisa mood dete hain jo movie ke moods mein nahi hai.
        non_matching_score = calculate_score(
            self.movie, selected_mood="sad"
        )

        self.assertGreater(matching_score, non_matching_score)

    def test_genre_match_increases_score(self):
        # Movie ka genre Comedy hai, isliye matching score zyada hona chahiye.
        matching_score = calculate_score(
            self.movie, selected_genre="Comedy"
        )

        # Thriller is movie ke genres mein nahi hai.
        non_matching_score = calculate_score(
            self.movie, selected_genre="Thriller"
        )

        self.assertGreater(matching_score, non_matching_score)

    def test_runtime_preference_affects_score(self):
        # 170-minute movie, 180-minute limit ke andar hai.
        matching_score = calculate_score(
            self.movie, max_runtime=180
        )

        # 170-minute movie, 100-minute limit ke andar nahi hai.
        non_matching_score = calculate_score(
            self.movie, max_runtime=100
        )

        self.assertGreater(matching_score, non_matching_score)

    def test_language_match_increases_score(self):
        # Movie ki language Hindi (hi) hai.
        matching_score = calculate_score(
            self.movie, selected_language="hi"
        )

        # English select karne par language-match points nahi milne chahiye.
        non_matching_score = calculate_score(
            self.movie, selected_language="en"
        )

        self.assertGreater(matching_score, non_matching_score)

    def test_rank_movies_returns_highest_score_first(self):
        # Ek doosri movie banate hain jisme mood aur genre match nahi karte.
        other_movie = {
            "title": "Example Movie",
            "language": "en",
            "industry": "Hollywood",
            "genres": "Thriller",
            "moods": "dark",
            "runtime": 120,
            "rating": 6.0,
            "release_year": 2010,
        }

        # Dono movies ko happy mood aur Comedy genre ke liye rank karte hain.
        ranked = rank_movies(
            [other_movie, self.movie],
            selected_mood="happy",
            selected_genre="Comedy",
        )

        # Check karte hain ki pehli movie ka score doosri se kam na ho.
        self.assertGreaterEqual(
            ranked[0]["score"], ranked[1]["score"]
        )

        # Matching movie sabse pehle aani chahiye.
        self.assertEqual(ranked[0]["movie"]["title"], "3 Idiots")

    def test_explanation_mentions_matching_mood(self):
        # Explanation function ko selected mood ke saath call karte hain.
        reasons = explain_recommendation(
            self.movie, selected_mood="happy"
        )

        # Check karte hain ki result mein mood match ka reason diya gaya hai.
        self.assertTrue(
            any("happy" in reason.lower() for reason in reasons)
        )


# Ye block tests ko tab run karta hai jab file directly execute hoti hai.
if __name__ == "__main__":
    unittest.main(verbosity=2)
