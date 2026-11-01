"""Regression tests for authentication, private history, and mode discovery APIs."""
import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app


class TestUserFeatures(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "MOODFLIX_DATABASE": os.path.join(self.temp_dir.name, "test.sqlite3"),
            "FLASK_SECRET_KEY": "test-secret-key",
        })
        self.env.start()
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    def signup(self, email):
        return self.client.post("/api/auth/signup", json={
            "email": email, "password": "strong-password", "display_name": "Tester"
        })

    def test_signup_login_and_profile_preferences(self):
        response = self.signup("one@example.com")
        self.assertEqual(response.status_code, 201)
        profile = self.client.get("/api/profile")
        self.assertEqual(profile.status_code, 200)
        updated = self.client.put("/api/profile", json={"languages": ["Hindi"], "genres": ["Thriller"]})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["preferences"]["languages"], ["Hindi"])
        self.client.post("/api/auth/logout")
        login = self.client.post("/api/auth/login", json={"email": "one@example.com", "password": "strong-password"})
        self.assertEqual(login.status_code, 200)

    def test_watched_and_watchlist_are_distinct_and_private(self):
        self.signup("one@example.com")
        movie = {"title": "Example Film", "year": 2025, "tmdb_id": 99}
        self.client.post("/api/library", json={"movie": movie, "status": "watched"})
        self.client.post("/api/library", json={"movie": movie, "status": "watchlist"})
        watched = self.client.get("/api/library?status=watched").get_json()["movies"]
        watchlist = self.client.get("/api/library?status=watchlist").get_json()["movies"]
        self.assertEqual(len(watched), 1)
        self.assertEqual(len(watchlist), 1)
        self.client.post("/api/auth/logout")
        self.signup("two@example.com")
        other_user_movies = self.client.get("/api/library").get_json()["movies"]
        self.assertEqual(other_user_movies, [])


    def test_today_mood_branch_adds_sixth_question_when_mood_is_known(self):
        self.signup("mood@example.com")
        data = self.client.post("/api/modes/start", json={"mode": "today_mood"}).get_json()
        session_id = data["session_id"]
        question = data["question"]
        with patch("app.services.tmdb_service.discover_movies", return_value=[]):
            for _ in range(5):
                answer = "happy" if question["id"] == "mood" else next(
                    value for value in question["options"] if value not in ("not_sure", "any")
                )
                response = self.client.post("/api/modes/answer", json={
                    "session_id": session_id, "question_id": question["id"], "answer": answer
                })
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                question = data.get("question")
            self.assertFalse(data["complete"])
            self.assertEqual(question["id"], "mood_intensity")

    def test_feedback_is_reflected_in_liked_library(self):
        self.signup("feedback@example.com")
        response = self.client.post("/api/feedback", json={
            "movie": {"title": "Liked Film", "year": 2024, "tmdb_id": 404},
            "feedback": "like",
        })
        self.assertEqual(response.status_code, 201)
        liked = self.client.get("/api/library?status=liked").get_json()["movies"]
        self.assertEqual([item["title"] for item in liked], ["Liked Film"])

    def test_surprise_mode_adaptive_questions_and_results(self):
        self.signup("mode@example.com")
        start = self.client.post("/api/modes/start", json={"mode": "surprise_me"})
        self.assertEqual(start.status_code, 201)
        data = start.get_json()
        session_id = data["session_id"]
        with patch("app.services.tmdb_service.discover_movies", return_value=[
            {"title": "One", "year": 2024, "tmdb_id": 1, "score": 90, "genres": ["Drama"]},
            {"title": "Two", "year": 2023, "tmdb_id": 2, "score": 80, "genres": ["Comedy"]},
            {"title": "Three", "year": 2022, "tmdb_id": 3, "score": 70, "genres": ["Action"]},
        ]), patch("app.routes.recommendation_routes.get_movie_metadata", return_value={"details": None, "ott_availability": []}):
            while not data.get("complete"):
                question = data["question"]
                answer = next(value for value in question["options"] if value != "not_sure")
                response = self.client.post("/api/modes/answer", json={
                    "session_id": session_id, "question_id": question["id"], "answer": answer
                })
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
            self.assertEqual(data["count"], 3)
            self.assertEqual([m["recommendation_role"] for m in data["recommendations"]],
                             ["Best Match", "Different Experience", "Surprise Discovery"])


if __name__ == "__main__":
    unittest.main()
