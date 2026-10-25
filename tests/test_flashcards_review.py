import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api import flashcards


class FlashcardReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_flashcards.db"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE flashcards (
                    id TEXT PRIMARY KEY,
                    set_id TEXT,
                    user_id INTEGER NOT NULL,
                    document_id TEXT,
                    question TEXT,
                    answer TEXT,
                    topic TEXT,
                    difficulty TEXT,
                    status TEXT NOT NULL DEFAULT 'learning',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    next_review_at TEXT,
                    interval_days INTEGER NOT NULL DEFAULT 0,
                    ease_factor REAL NOT NULL DEFAULT 2.5,
                    repetitions INTEGER NOT NULL DEFAULT 0,
                    last_reviewed_at TEXT
                )
            """)
            conn.execute("""
                INSERT INTO flashcards
                    (id, set_id, user_id, question, answer,
                     status, interval_days, ease_factor, repetitions)
                VALUES ('card-1', 'set-1', 7, 'Question?', 'Answer',
                        'learning', 0, 2.5, 0)
            """)

        self.connection_patch = patch.object(
            flashcards, "get_connection", side_effect=self.connect
        )
        self.auth_patch = patch.object(
            flashcards, "get_current_user",
            return_value={"id": 7, "name": "Test Student", "role": "student"}
        )
        self.connection_patch.start()
        self.auth_patch.start()

        self.request = Request({
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/flashcards/card-1/review",
            "raw_path": b"/flashcards/card-1/review",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
        })

    def tearDown(self):
        self.auth_patch.stop()
        self.connection_patch.stop()
        self.temp_dir.cleanup()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def review(self, rating, card_id="card-1"):
        return flashcards.review_flashcard(
            card_id,
            flashcards.ReviewFlashcardRequest(rating=rating),
            self.request,
        )

    def get_card(self, card_id="card-1"):
        with self.connect() as conn:
            return dict(conn.execute(
                "SELECT * FROM flashcards WHERE id = ?", (card_id,)
            ).fetchone())

    def test_again_schedules_ten_minutes_and_resets_repetitions(self):
        result = self.review("again")
        card = self.get_card()

        self.assertEqual(result["interval_days"], 0)
        self.assertEqual(result["repetitions"], 0)
        self.assertEqual(result["card_status"], "learning")
        self.assertEqual(card["repetitions"], 0)
        self.assertEqual(card["ease_factor"], 2.3)

        due = datetime.fromisoformat(result["next_review_at"])
        now = datetime.now(timezone.utc)
        self.assertTrue(
            timedelta(minutes=9, seconds=50)
            <= due - now
            <= timedelta(minutes=10, seconds=10)
        )
        self.assertTrue(card["last_reviewed_at"])

    def test_hard_schedules_at_least_one_day(self):
        result = self.review("hard")
        self.assertEqual(result["interval_days"], 1)
        self.assertEqual(result["repetitions"], 1)
        self.assertEqual(result["card_status"], "learning")
        self.assertEqual(self.get_card()["ease_factor"], 2.35)

    def test_good_initially_schedules_one_day(self):
        result = self.review("good")
        self.assertEqual(result["interval_days"], 1)
        self.assertEqual(result["repetitions"], 1)
        self.assertEqual(result["card_status"], "review")

    def test_easy_initially_schedules_four_days(self):
        result = self.review("easy")
        card = self.get_card()
        self.assertEqual(result["interval_days"], 4)
        self.assertEqual(result["repetitions"], 1)
        self.assertEqual(result["card_status"], "review")
        self.assertEqual(card["ease_factor"], 2.65)

    def test_rating_is_normalized(self):
        result = self.review("  GOOD  ")
        self.assertEqual(result["rating"], "good")

    def test_invalid_rating_is_rejected_without_changing_card(self):
        before = self.get_card()

        with self.assertRaises(HTTPException) as caught:
            self.review("excellent")

        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(self.get_card(), before)

    def test_unknown_card_returns_404(self):
        with self.assertRaises(HTTPException) as caught:
            self.review("good", card_id="missing-card")

        self.assertEqual(caught.exception.status_code, 404)

    def test_cannot_review_another_users_card(self):
        with self.connect() as conn:
            conn.execute("""
                INSERT INTO flashcards
                    (id, set_id, user_id, question, answer)
                VALUES ('other-card', 'other-set', 99, 'Private?', 'Secret')
            """)

        with self.assertRaises(HTTPException) as caught:
            self.review("good", card_id="other-card")

        self.assertEqual(caught.exception.status_code, 404)

    def test_good_progression_advances_from_one_to_six_days(self):
        self.review("good")
        result = self.review("good")

        self.assertEqual(result["interval_days"], 6)
        self.assertEqual(result["repetitions"], 2)

    def test_review_timestamp_and_due_date_persist(self):
        result = self.review("easy")
        card = self.get_card()

        self.assertEqual(card["next_review_at"], result["next_review_at"])
        self.assertIsNotNone(card["last_reviewed_at"])
        self.assertEqual(card["interval_days"], 4)
        self.assertEqual(card["repetitions"], 1)


    def test_easy_reaches_mastered_after_three_reviews(self):
        self.review("easy")
        self.review("easy")
        result = self.review("easy")

        self.assertEqual(result["repetitions"], 3)
        self.assertEqual(result["card_status"], "mastered")
        self.assertGreaterEqual(result["interval_days"], 1)

    def test_ease_factor_never_falls_below_minimum(self):
        with self.connect() as conn:
            conn.execute(
                "UPDATE flashcards SET ease_factor = 1.35 WHERE id = ?",
                ("card-1",),
            )

        result = self.review("again")

        self.assertEqual(result["ease_factor"], 1.3)
        self.assertEqual(self.get_card()["ease_factor"], 1.3)

    def test_hard_interval_scales_for_existing_interval(self):
        with self.connect() as conn:
            conn.execute(
                """UPDATE flashcards
                   SET interval_days = 10, repetitions = 2
                   WHERE id = ?""",
                ("card-1",),
            )

        result = self.review("hard")

        self.assertEqual(result["interval_days"], 12)
        self.assertEqual(result["repetitions"], 3)
        self.assertEqual(result["card_status"], "learning")


if __name__ == "__main__":
    unittest.main(verbosity=2)
