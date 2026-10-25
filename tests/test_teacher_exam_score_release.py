import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api import teacher_exams


class TeacherExamScoreReleaseTests(unittest.TestCase):
    OWNER_ID = 1
    STUDENT_ID = 2
    OTHER_TEACHER_ID = 3
    EXAM_ID = "score-release-test"
    ATTEMPT_ID = 1

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "score_release.db"

        self.create_schema()
        self.seed_data()

        self.connection_patch = patch.object(
            teacher_exams,
            "get_connection",
            side_effect=self.connect,
        )
        self.teacher_patch = patch.object(
            teacher_exams,
            "require_teacher",
            side_effect=lambda request: self.current_teacher,
        )

        self.current_teacher = {
            "id": self.OWNER_ID,
            "name": "Exam Owner",
            "role": "teacher",
        }

        self.connection_patch.start()
        self.teacher_patch.start()

        self.addCleanup(self.connection_patch.stop)
        self.addCleanup(self.teacher_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

        self.request = Request({
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": (
                f"/api/teacher/exams/submissions/"
                f"{self.ATTEMPT_ID}/release"
            ),
            "raw_path": (
                f"/api/teacher/exams/submissions/"
                f"{self.ATTEMPT_ID}/release"
            ).encode(),
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
        })

    def connect(self):
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_schema(self):
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript("""
                PRAGMA foreign_keys = ON;

                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                );

                CREATE TABLE teacher_tests (
                    id TEXT PRIMARY KEY,
                    creator_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    FOREIGN KEY (creator_id) REFERENCES users(id)
                );

                CREATE TABLE teacher_test_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    score_released INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(test_id, student_id),
                    FOREIGN KEY (test_id) REFERENCES teacher_tests(id),
                    FOREIGN KEY (student_id) REFERENCES users(id)
                );

                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    reference_type TEXT,
                    reference_id TEXT,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE UNIQUE INDEX
                    uq_exam_result_notification_per_student
                ON notifications(user_id, reference_id)
                WHERE type = 'exam_result_released'
                  AND reference_type = 'teacher_test';
            """)

    def seed_data(self):
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO users
                    (id, name, email, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        self.OWNER_ID, "Exam Owner",
                        "owner@example.test", "test-hash", "teacher",
                    ),
                    (
                        self.STUDENT_ID, "Test Student",
                        "student@example.test", "test-hash", "student",
                    ),
                    (
                        self.OTHER_TEACHER_ID, "Other Teacher",
                        "other@example.test", "test-hash", "teacher",
                    ),
                ],
            )

            connection.execute(
                """
                INSERT INTO teacher_tests (id, creator_id, title)
                VALUES (?, ?, ?)
                """,
                (self.EXAM_ID, self.OWNER_ID, "Integrity Exam"),
            )

            connection.execute(
                """
                INSERT INTO teacher_test_attempts (
                    id, test_id, student_id, score,
                    total_questions, percentage, score_released
                )
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    self.ATTEMPT_ID, self.EXAM_ID,
                    self.STUDENT_ID, 8, 10, 80.0,
                ),
            )

    def release(self):
        return teacher_exams.release_score(
            self.ATTEMPT_ID,
            self.request,
        )

    def get_attempt(self):
        with self.connect() as connection:
            return dict(connection.execute(
                """
                SELECT * FROM teacher_test_attempts WHERE id = ?
                """,
                (self.ATTEMPT_ID,),
            ).fetchone())

    def notification_count(self):
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT COUNT(*) FROM notifications
                WHERE user_id = ?
                  AND type = 'exam_result_released'
                  AND reference_type = 'teacher_test'
                  AND reference_id = ?
                """,
                (self.STUDENT_ID, self.EXAM_ID),
            ).fetchone()[0]

    def add_result_notification(self):
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO notifications (
                    user_id, type, title, message,
                    reference_type, reference_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.STUDENT_ID,
                    "exam_result_released",
                    "Exam Result Released",
                    "Your result is available.",
                    "teacher_test",
                    self.EXAM_ID,
                ),
            )

    def test_exam_owner_can_release_score_and_notify_student(self):
        result = self.release()

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["already_released"])
        self.assertTrue(result["student_notified"])
        self.assertEqual(self.get_attempt()["score_released"], 1)
        self.assertEqual(self.notification_count(), 1)

    def test_other_teacher_cannot_release_or_notify(self):
        self.current_teacher = {
            "id": self.OTHER_TEACHER_ID,
            "name": "Other Teacher",
            "role": "teacher",
        }

        with self.assertRaises(HTTPException) as caught:
            self.release()

        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(self.get_attempt()["score_released"], 0)
        self.assertEqual(self.notification_count(), 0)

    def test_releasing_twice_does_not_duplicate_notification(self):
        first = self.release()
        second = self.release()

        self.assertFalse(first["already_released"])
        self.assertTrue(second["already_released"])
        self.assertEqual(self.get_attempt()["score_released"], 1)
        self.assertEqual(self.notification_count(), 1)

    def test_existing_notification_is_not_duplicated(self):
        self.add_result_notification()

        result = self.release()

        self.assertEqual(result["status"], "success")
        self.assertEqual(self.get_attempt()["score_released"], 1)
        self.assertEqual(self.notification_count(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
