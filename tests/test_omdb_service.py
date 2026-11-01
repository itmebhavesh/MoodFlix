from app.services.omdb_service import normalize_movie_details
import unittest
from unittest.mock import Mock, patch

from app.services.omdb_service import get_movie_details


class TestOMDbService(unittest.TestCase):

    @patch("app.services.omdb_service.requests.get")
    @patch("app.services.omdb_service.os.getenv")
    def test_movie_details_success(self, mock_getenv, mock_get):
        # Real API key ki jagah fake key use karo.
        mock_getenv.return_value = "test-api-key"

        # Successful OMDb response simulate karo.
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "Response": "True",
            "Title": "Interstellar",
            "Year": "2014",
            "imdbRating": "8.7",
        }
        mock_get.return_value = fake_response

        result = get_movie_details(title="Interstellar")

        self.assertEqual(result["Title"], "Interstellar")
        self.assertEqual(result["Year"], "2014")
        self.assertEqual(result["imdbRating"], "8.7")

    @patch("app.services.omdb_service.os.getenv")
    def test_missing_api_key(self, mock_getenv):
        # API key missing hone par clear error aana chahiye.
        mock_getenv.return_value = None

        with self.assertRaises(RuntimeError):
            get_movie_details(title="Interstellar")

    @patch("app.services.omdb_service.os.getenv")
    def test_missing_search_input(self, mock_getenv):
        mock_getenv.return_value = "test-api-key"

        # Title aur IMDb ID dono missing hain.
        with self.assertRaises(ValueError):
            get_movie_details()

    @patch("app.services.omdb_service.requests.get")
    @patch("app.services.omdb_service.os.getenv")
    def test_movie_not_found(self, mock_getenv, mock_get):
        mock_getenv.return_value = "test-api-key"

        # OMDb movie-not-found response simulate karo.
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "Response": "False",
            "Error": "Movie not found!",
        }
        mock_get.return_value = fake_response

        result = get_movie_details(title="Unknown Movie XYZ")

        self.assertIsNone(result)
        
    def test_normalize_movie_details(self):
        raw_data = {
            "Response": "True",
            "Title": "Interstellar",
            "Year": "2014",
            "Plot": "A space exploration film.",
            "Poster": "https://example.com/poster.jpg",
            "Genre": "Adventure, Drama, Sci-Fi",
            "Actors": "Matthew McConaughey, Anne Hathaway",
            "imdbRating": "8.7",
            "imdbID": "tt0816692",
            "Ratings": [
                {
                    "Source": "Rotten Tomatoes",
                    "Value": "73%",
                }
            ],
        }

        result = normalize_movie_details(raw_data)

        self.assertEqual(result["title"], "Interstellar")
        self.assertEqual(result["imdb_rating"], 8.7)
        self.assertEqual(result["rotten_tomatoes"], "73%")
        self.assertEqual(result["genres"], ["Adventure", "Drama", "Sci-Fi"])
        self.assertEqual(
            result["actors"],
            ["Matthew McConaughey", "Anne Hathaway"],
        )

    def test_normalize_missing_ratings(self):
        raw_data = {
            "Response": "True",
            "Title": "Example Movie",
            "imdbRating": "N/A",
            "Ratings": [],
        }

        result = normalize_movie_details(raw_data)

        self.assertIsNone(result["imdb_rating"])
        self.assertIsNone(result["rotten_tomatoes"])


if __name__ == "__main__":
    unittest.main()
