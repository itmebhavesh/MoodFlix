
# Flask API ko test karne ke liye unittest use karenge.
import unittest

# External API aur recommendation functions ko mock karne ke tools.
from unittest.mock import patch

# Flask application ka test client banane ke liye.
from flask import Flask

# Recommendation Blueprint import karo.
from app.routes.recommendation_routes import recommendation_bp


class TestRecommendationRoutes(unittest.TestCase):

    def setUp(self):
        # Har test ke liye ek fresh Flask application banegi.
        self.app = Flask(__name__)

        # Recommendation API ko application ke saath register karo.
        self.app.register_blueprint(
            recommendation_bp,
            url_prefix="/api"
        )

        # Test client HTTP requests bhejne mein help karta hai.
        self.client = self.app.test_client()
        
    def test_invalid_json_body_returns_400(self):
        # JSON object ki jagah list bhej rahe hain.
        response = self.client.post(
            "/api/recommend",
            json=["happy", "Comedy"]
        )

        # API ko invalid request reject karni chahiye.
        self.assertEqual(response.status_code, 400)

        # Response mein error message hona chahiye.
        data = response.get_json()
        self.assertIn("error", data)
        
    def test_invalid_min_rating_returns_400(self):
        # Rating 10 se zyada hai, isliye request invalid hai.
        response = self.client.post(
            "/api/recommend",
            json={"min_rating": 11}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_invalid_max_runtime_returns_400(self):
        # Runtime zero nahi ho sakta.
        response = self.client.post(
            "/api/recommend",
            json={"max_runtime": 0}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_invalid_preferred_year_returns_400(self):
        # Year 1888 se pehle ka hai.
        response = self.client.post(
            "/api/recommend",
            json={"preferred_year": 1800}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())
        
    @patch(
        "app.routes.recommendation_routes.load_movies",
        side_effect=OSError("Test catalog error")
    )
    def test_catalog_load_failure_returns_500(self, mock_load_movies):
        # Valid request bhejte hain, lekin catalog load fail karwate hain.
        response = self.client.post(
            "/api/recommend",
            json={"mood": "happy"}
        )

        # API ko server error return karna chahiye.
        self.assertEqual(response.status_code, 500)

        # Error response mein expected message verify karo.
        data = response.get_json()
        self.assertEqual(
            data["error"],
            "Movie catalog could not be loaded."
        )

        # Confirm karo ki catalog load karne ki koshish hui.
        mock_load_movies.assert_called_once_with()
        
    @patch(
        "app.routes.recommendation_routes.get_movie_metadata",
        return_value={
            "details": None,
            "ott_availability": [],
        },
    )
    @patch(
        "app.routes.recommendation_routes.get_recommendations",
        return_value=[
            {
                "movie": {
                    "title": "3 Idiots",
                    "language": "hi",
                    "industry": "Bollywood",
                    "genres": "Comedy|Drama",
                    "moods": "happy|inspiring",
                    "rating": 8.4,
                    "runtime": 170,
                    "release_year": 2009,
                },
                "score": 85,
            }
        ],
    )
    @patch(
        "app.routes.recommendation_routes.load_movies",
        return_value=[{"title": "3 Idiots"}],
    )
    def test_valid_request_returns_200(
        self,
        mock_load_movies,
        mock_get_recommendations,
        mock_get_movie_metadata,
    ):
        # Valid mood ke saath API request bhejo.
        response = self.client.post(
            "/api/recommend",
            json={"mood": "happy"},
        )

        # Successful request ka status 200 hona chahiye.
        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        # Response mein ek recommendation honi chahiye.
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["recommendations"][0]["title"],
            "3 Idiots",
        )

        # Response mein zaroori fields verify karo.
        movie = data["recommendations"][0]
        self.assertIn("reasons", movie)
        self.assertIn("ratings", movie)
        self.assertIn("ott_availability", movie)
        
    @patch(
        "app.routes.recommendation_routes.get_movie_metadata",
        return_value={
            "details": None,
            "ott_availability": [],
        },
    )
    @patch(
        "app.routes.recommendation_routes.get_recommendations",
        return_value=[],
    )
    @patch(
        "app.routes.recommendation_routes.load_movies",
        return_value=[],
    )
    def test_empty_results_returns_200_with_zero_count(
        self,
        mock_load_movies,
        mock_get_recommendations,
        mock_get_movie_metadata,
    ):
        # Jab koi movie recommend na ho, empty response verify karo.
        response = self.client.post(
            "/api/recommend",
            json={"mood": "unknown"},
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["recommendations"], [])

    @patch(
        "app.routes.recommendation_routes.get_movie_metadata",
        return_value={
            "details": None,
            "ott_availability": [],
        },
    )
    @patch("app.routes.recommendation_routes.get_recommendations")
    @patch("app.routes.recommendation_routes.load_movies", return_value=[])
    def test_response_contains_at_most_ten_recommendations(
        self,
        mock_load_movies,
        mock_get_recommendations,
        mock_get_movie_metadata,
    ):
        # Test ke liye 12 valid movie records banao.
        movies = [
            {
                "movie": {
                    "title": f"Movie {number}",
                    "language": "en",
                    "industry": "Hollywood",
                    "genres": "Drama",
                    "moods": "happy",
                    "rating": 7.0,
                    "runtime": 120,
                    "release_year": 2020,
                },
                "score": 80 - number,
            }
            for number in range(12)
        ]

        # Recommendation engine 12 results return karega.
        mock_get_recommendations.return_value = movies

        response = self.client.post(
            "/api/recommend",
            json={"mood": "happy"},
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        # API ko maximum 10 movies hi return karni chahiye.
        self.assertEqual(data["count"], 10)
        self.assertEqual(len(data["recommendations"]), 10)

        # Har returned movie mein title hona chahiye.
        for movie in data["recommendations"]:
            self.assertIn("title", movie)
