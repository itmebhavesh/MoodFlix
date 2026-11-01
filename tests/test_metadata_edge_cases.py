import unittest
from unittest.mock import Mock, patch

from app.services.omdb_service import normalize_movie_details, get_movie_details
from app.services.watchmode_service import get_streaming_sources


class TestMetadataEdgeCases(unittest.TestCase):
    def test_omdb_normalizer_handles_non_list_ratings(self):
        data = {"Response": "True", "Ratings": "unexpected", "imdbRating": "8.1"}
        result = normalize_movie_details(data)
        self.assertEqual(result["imdb_rating"], 8.1)
        self.assertIsNone(result["rotten_tomatoes"])

    def test_omdb_normalizer_skips_invalid_rating_records(self):
        data = {
            "Response": "True",
            "Ratings": [None, "bad", {"Source": "Rotten Tomatoes", "Value": "101%"}],
        }
        result = normalize_movie_details(data)
        self.assertIsNone(result["rotten_tomatoes"])

    @patch.dict("os.environ", {"OMDB_API_KEY": "test-key"})
    @patch("app.services.omdb_service.requests.get")
    def test_omdb_passes_year(self, mock_get):
        response = Mock()
        response.json.return_value = {"Response": "False", "Error": "Movie not found!"}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        self.assertIsNone(get_movie_details(title="Example", year=2001))
        self.assertEqual(mock_get.call_args.kwargs["params"]["y"], "2001")

    @patch.dict("os.environ", {"WATCHMODE_API_KEY": "test-key"})
    @patch("app.services.watchmode_service.requests.get")
    def test_watchmode_skips_non_dict_sources(self, mock_get):
        response = Mock()
        response.json.return_value = [None, "invalid", {"name": "Prime Video", "type": "sub"}]
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        result = get_streaming_sources(123)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["platform"], "Prime Video")

    @patch.dict("os.environ", {"WATCHMODE_API_KEY": "test-key"})
    def test_watchmode_rejects_empty_title_id(self):
        with self.assertRaises(ValueError):
            get_streaming_sources("")
