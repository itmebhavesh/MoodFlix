
import unittest
from unittest.mock import Mock, patch

from app.services.watchmode_service import get_streaming_sources


class TestWatchmodeService(unittest.TestCase):

    @patch("app.services.watchmode_service.requests.get")
    @patch("app.services.watchmode_service.os.getenv")
    def test_duplicate_sources_are_removed(self, mock_getenv, mock_get):
        # Fake API key set karo; real key ki zaroorat nahi.
        mock_getenv.return_value = "test-api-key"

        # API se do identical records milne ka simulation.
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = [
            {
                "name": "Hotstar",
                "type": "sub",
                "web_url": "https://example.com/movie",
            },
            {
                "name": "Hotstar",
                "type": "sub",
                "web_url": "https://example.com/movie",
            },
        ]
        mock_get.return_value = fake_response

        # Service ko call karo.
        result = get_streaming_sources(123, region="IN")

        # Sirf ek unique record bachna chahiye.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["platform"], "Hotstar")
        self.assertEqual(result[0]["availability_label"], "Subscription")

    @patch("app.services.watchmode_service.requests.get")
    @patch("app.services.watchmode_service.os.getenv")
    def test_rent_and_buy_are_kept_separate(self, mock_getenv, mock_get):
        mock_getenv.return_value = "test-api-key"

        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = [
            {
                "name": "AppleTV",
                "type": "rent",
                "web_url": "https://example.com/movie",
            },
            {
                "name": "AppleTV",
                "type": "buy",
                "web_url": "https://example.com/movie",
            },
        ]
        mock_get.return_value = fake_response

        result = get_streaming_sources(123)

        # Same platform aur URL hone par bhi Rent aur Buy alag hain.
        self.assertEqual(len(result), 2)
        self.assertEqual(
            {item["availability_label"] for item in result},
            {"Rent", "Buy"},
        )


if __name__ == "__main__":
    unittest.main()
