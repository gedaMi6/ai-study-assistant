import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

from app.api import progress


class StudentReleasedGradesTests(unittest.TestCase):
    STUDENT_ID = 2
    OTHER_STUDENT_ID = 4

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "grades.db"

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE teacher_tests (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                );

                CREATE TABLE teacher_test_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    submitted_at TEXT,
                    score_released INTEGER NOT NULL DEFAULT 0
                );

                INSERT INTO teacher_tests (id, title)
                VALUES ('exam-a', 'Test Exam');

                INSERT INTO teacher_test_attempts
                    (test_id, student_id, score, total_questions,
                     percentage, submitted_at, score_released)
                VALUES
                    ('exam-a', 2, 8, 10, 80.0, '2026-10-24 10:00:00', 1),
                    ('exam-a', 2, 9, 10, 90.0, '2026-10-24 11:00:00', 0),
                    ('exam-a', 4, 10, 10, 100.0, '2026-10-24 12:00:00', 1);
            """)

        self.connection_patch = patch.object(
            progress, "get_connection", side_effect=self.connect
        )
        self.user_patch = patch.object(
            progress,
            "get_current_user",
            return_value={
                "id": self.STUDENT_ID,
                "name": "Test Student",
                "role": "student",
            },
        )

        self.connection_patch.start()
        self.user_patch.start()
        self.addCleanup(self.connection_patch.stop)
        self.addCleanup(self.user_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

        self.request = Request({
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/progress/grades",
            "raw_path": b"/progress/grades",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
        })

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def test_grades_include_only_current_students_released_scores(self):
        response = progress.get_released_grades(self.request)

        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["grades"]), 1)

        grade = response["grades"][0]
        self.assertEqual(grade["exam_id"], "exam-a")
        self.assertEqual(grade["exam_title"], "Test Exam")
        self.assertEqual(grade["score"], 8)
        self.assertEqual(grade["total_questions"], 10)
        self.assertEqual(grade["percentage"], 80.0)

        # Unreleased grades and another student's grade must not appear.
        self.assertNotIn(
            9, [item["score"] for item in response["grades"]]
        )
        self.assertNotIn(
            10, [item["score"] for item in response["grades"]]
        )


if __name__ == "__main__":
    unittest.main()
