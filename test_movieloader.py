
# unittest Python ka built-in testing module hai.
import unittest

# Hum movie_loader.py ke functions import kar rahe hain.
from app.recommendation.movie_loader import (
    filter_by_mood,
    filter_by_mood_and_genre,
    filter_by_preferences,
    filter_by_rating_and_runtime,
    get_recommendations,
)


class TestMovieFilters(unittest.TestCase):

    def setUp(self):
        # Test ke liye sample movie data.
        # Values strings mein hain, jaise CSV se read hone par hoti hain.
        self.movies = [
            {
                "title": "3 Idiots",
                "language": "hi",
                "industry": "Bollywood",
                "genres": "Comedy|Drama",
                "moods": "happy|inspiring",
                "runtime": "170",
                "rating": "8.4",
                "release_year": "2009",
            },
            {
                "title": "The Dark Knight",
                "language": "en",
                "industry": "Hollywood",
                "genres": "Action|Crime",
                "moods": "intense|excited",
                "runtime": "152",
                "rating": "9.0",
                "release_year": "2008",
            },
        ]

    def test_filter_by_mood(self):
        # "HAPPY" dene par bhi 3 Idiots milni chahiye.
        # Isse case-insensitive matching check hoti hai.
        result = filter_by_mood(self.movies, "HAPPY")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "3 Idiots")

    def test_filter_by_mood_and_genre(self):
        # Mood aur genre dono match hone chahiye.
        result = filter_by_mood_and_genre(
            self.movies, "happy", "comedy"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "3 Idiots")

    def test_filter_by_language(self):
        # Hindi select karne par English movie nahi aani chahiye.
        result = filter_by_preferences(
            self.movies, selected_language="HI"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "3 Idiots")

    def test_filter_by_industry(self):
        # Hollywood select karne par sirf Hollywood movie mile.
        result = filter_by_preferences(
            self.movies, selected_industry="hollywood"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "The Dark Knight")

    def test_minimum_rating(self):
        # Minimum rating 8.5 hai.
        # 8.4 rating wali 3 Idiots remove honi chahiye.
        result = filter_by_rating_and_runtime(
            self.movies, min_rating=8.5
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "The Dark Knight")

    def test_maximum_runtime(self):
        # 160-minute limit mein 170-minute movie nahi aani chahiye.
        result = filter_by_rating_and_runtime(
            self.movies, max_runtime=160
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "The Dark Knight")

    def test_combined_strict_filters(self):
        # Mood, genre aur minimum rating teeno match hone chahiye.
        result = filter_by_preferences(
            self.movies,
            selected_mood="happy",
            selected_genre="comedy",
        )

        result = filter_by_rating_and_runtime(
            result, min_rating=8.0, max_runtime=180
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "3 Idiots")

    def test_no_match_returns_empty_list(self):
        # Dataset mein sad mood wali movie nahi hai.
        result = filter_by_mood(self.movies, "sad")

        self.assertEqual(result, [])

    def test_get_recommendations_returns_ranked_movies(self):
        # Main recommendation function filter aur ranking dono chalata hai.
        result = get_recommendations(
            self.movies,
            mood="happy",
            genre="Comedy",
            language="hi",
        )

        # Sirf matching movie rehni chahiye.
        self.assertEqual(len(result), 1)

        # Result mein movie aur uska score dono hone chahiye.
        self.assertIn("movie", result[0])
        self.assertIn("score", result[0])
        self.assertEqual(result[0]["movie"]["title"], "3 Idiots")
        
    def test_invalid_rating_is_skipped(self):
        # Galat rating wali movie ka sample banate hain.
        invalid_movie = self.movies[0].copy()
        invalid_movie["rating"] = "unknown"

        # Valid aur invalid movies ko ek saath filter karo.
        result = filter_by_rating_and_runtime(
            [self.movies[1], invalid_movie],
            min_rating=7.0,
        )

        # Invalid rating wali movie result mein nahi aani chahiye.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "The Dark Knight")

    def test_invalid_runtime_is_skipped(self):
        # Galat runtime wali movie ka sample banate hain.
        invalid_movie = self.movies[0].copy()
        invalid_movie["runtime"] = "unknown"

        # Invalid runtime wali movie skip honi chahiye.
        result = filter_by_rating_and_runtime(
            [self.movies[1], invalid_movie],
            max_runtime=180,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "The Dark Knight")


# File ko directly run karne par saare tests execute honge.
if __name__ == "__main__":
    unittest.main(verbosity=2)
