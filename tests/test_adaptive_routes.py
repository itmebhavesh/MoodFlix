"""End-to-end tests for the adaptive recommendation API."""
import unittest
from unittest.mock import patch

from flask import Flask

from app.routes.recommendation_routes import (
    recommendation_bp,
    _ADAPTIVE_SESSIONS,
    _ADAPTIVE_LOCK,
)


class TestAdaptiveRecommendationRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(recommendation_bp, url_prefix="/api")
        self.client = self.app.test_client()
        with _ADAPTIVE_LOCK:
            _ADAPTIVE_SESSIONS.clear()

    def tearDown(self):
        with _ADAPTIVE_LOCK:
            _ADAPTIVE_SESSIONS.clear()

    def test_start_quiz_returns_question_and_session(self):
        response = self.client.get("/api/recommend/questions")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["session_id"])
        self.assertFalse(data["complete"])
        self.assertGreater(data["candidate_count"], 1)
        self.assertIsInstance(data["question"]["options"], list)

    def test_answer_flow_returns_next_question_then_final_movie(self):
        start = self.client.get("/api/recommend/questions")
        self.assertEqual(start.status_code, 200)
        session_id = start.get_json()["session_id"]
        first_question = start.get_json()["question"]

        # The current catalogue's language question includes the English option.
        if first_question["id"] == "language":
            first_answer = "en"
        else:
            first_answer = first_question["options"][0]["value"]

        with patch(
            "app.routes.recommendation_routes.get_movie_metadata",
            return_value={"details": None, "ott_availability": []},
        ):
            first_response = self.client.post(
                "/api/recommend/answer",
                json={
                    "session_id": session_id,
                    "question_id": first_question["id"],
                    "answer": first_answer,
                },
            )
            self.assertEqual(first_response.status_code, 200)
            first_data = first_response.get_json()

            # Keep answering valid options until the quiz finishes.
            for _ in range(5):
                if first_data["complete"]:
                    break
                question = first_data["question"]
                answer = next(
                    option["value"]
                    for option in question["options"]
                    if option["value"] != "__any__"
                )
                response = self.client.post(
                    "/api/recommend/answer",
                    json={
                        "session_id": session_id,
                        "question_id": question["id"],
                        "answer": answer,
                    },
                )
                self.assertEqual(response.status_code, 200)
                first_data = response.get_json()

            self.assertTrue(first_data["complete"])
            self.assertIsNone(first_data["question"])
            self.assertIsInstance(first_data["recommendations"], list)
            if first_data["recommendations"]:
                movie = first_data["recommendations"][0]
                self.assertIn("title", movie)
                self.assertIn("ratings", movie)
                self.assertIn("ott_availability", movie)

    def test_answer_rejects_unknown_session(self):
        response = self.client.post(
            "/api/recommend/answer",
            json={
                "session_id": "not-a-session",
                "question_id": "language",
                "answer": "en",
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.get_json())

    def test_answer_rejects_invalid_option(self):
        start = self.client.get("/api/recommend/questions")
        session_id = start.get_json()["session_id"]
        question = start.get_json()["question"]
        response = self.client.post(
            "/api/recommend/answer",
            json={
                "session_id": session_id,
                "question_id": question["id"],
                "answer": "not-a-valid-option",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_finish_returns_recommendation_payload(self):
        start = self.client.get("/api/recommend/questions")
        session_id = start.get_json()["session_id"]
        with patch(
            "app.routes.recommendation_routes.get_movie_metadata",
            return_value={"details": None, "ott_availability": []},
        ):
            response = self.client.post(
                "/api/recommend/finish", json={"session_id": session_id}
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["complete"])
        self.assertIsInstance(data["recommendations"], list)
        self.assertIn("candidate_count", data)


if __name__ == "__main__":
    unittest.main()
