import unittest

from app.recommendation.adaptive_question_engine import (
    ANY_VALUE,
    filter_candidates,
    get_next_question,
    normalize_values,
)


class TestAdaptiveQuestionEngine(unittest.TestCase):
    def setUp(self):
        self.movies = [
            {"title": "A", "language": "hi", "industry": "Bollywood",
             "genres": "Comedy|Drama", "moods": "happy|inspiring"},
            {"title": "B", "language": "en", "industry": "Hollywood",
             "genres": "Sci-Fi|Drama", "moods": "curious|emotional"},
            {"title": "C", "language": "en", "industry": "Hollywood",
             "genres": "Action", "moods": "intense|excited"},
        ]

    def test_normalize_pipe_values_and_lists(self):
        self.assertEqual(normalize_values(" Happy | Inspiring "), ["happy", "inspiring"])
        self.assertEqual(normalize_values([" EN ", "hi"]), ["en", "hi"])
        self.assertEqual(normalize_values(None), [])

    def test_question_exists_when_candidates_differ(self):
        question = get_next_question(self.movies)
        self.assertIsNotNone(question)
        self.assertIn(question["id"], {"moods", "genres", "language", "industry"})
        self.assertIn(ANY_VALUE, [option["value"] for option in question["options"]])

    def test_filter_candidates_by_language(self):
        result = filter_candidates(self.movies, "language", "en")
        self.assertEqual([movie["title"] for movie in result], ["B", "C"])

    def test_no_preference_keeps_candidates(self):
        result = filter_candidates(self.movies, "language", ANY_VALUE)
        self.assertEqual(result, self.movies)

    def test_invalid_answer_is_rejected(self):
        with self.assertRaises(ValueError):
            filter_candidates(self.movies, "language", "fr")

    def test_single_candidate_has_no_next_question(self):
        self.assertIsNone(get_next_question([self.movies[0]]))


if __name__ == "__main__":
    unittest.main()
