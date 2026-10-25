import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api import teacher_exams


class TeacherExamDeleteIntegrityTests(unittest.TestCase):
    TEACHER_ID = 1
    OTHER_TEACHER_ID = 3
    STUDENT_ID = 2
    EXAM_ID = "delete-test-exam"
    OTHER_EXAM_ID = "keep-test-exam"
    QUESTION_ID = 101
    ATTEMPT_ID = 201

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "delete_test.db"
        self.create_schema()
        self.seed_data()

        self.connection_patch = patch.object(
            teacher_exams, "get_connection", side_effect=self.connect
        )
        self.teacher_patch = patch.object(
            teacher_exams,
            "require_teacher",
            return_value={
                "id": self.TEACHER_ID,
                "name": "Test Teacher",
                "role": "teacher",
            },
        )

        self.connection_patch.start()
        self.teacher_patch.start()

        self.addCleanup(self.connection_patch.stop)
        self.addCleanup(self.teacher_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

        self.request = Request({
            "type": "http",
            "http_version": "1.1",
            "method": "DELETE",
            "scheme": "http",
            "path": f"/api/teacher/exams/{self.EXAM_ID}",
            "raw_path": (
                f"/api/teacher/exams/{self.EXAM_ID}".encode()
            ),
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
        })

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                PRAGMA foreign_keys = ON;

                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL
                );

                CREATE TABLE teacher_tests (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    creator_id INTEGER NOT NULL,
                    FOREIGN KEY (creator_id) REFERENCES users(id)
                );

                CREATE TABLE teacher_test_assignments (
                    id INTEGER PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_questions (
                    id INTEGER PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_sessions (
                    id INTEGER PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_attempts (
                    id INTEGER PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_answers (
                    id INTEGER PRIMARY KEY,
                    attempt_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    FOREIGN KEY (attempt_id)
                        REFERENCES teacher_test_attempts(id) ON DELETE CASCADE,
                    FOREIGN KEY (question_id)
                        REFERENCES teacher_test_questions(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_password_attempts (
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_password_unlocks (
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_exam_monitoring_events (
                    id INTEGER PRIMARY KEY,
                    exam_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    FOREIGN KEY (exam_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    reference_type TEXT,
                    reference_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

    def seed_data(self):
        conn = self.connect()
        try:
            conn.executemany(
                "INSERT INTO users (id, name, role) VALUES (?, ?, ?)",
                [
                    (self.TEACHER_ID, "Test Teacher", "teacher"),
                    (self.STUDENT_ID, "Test Student", "student"),
                    (self.OTHER_TEACHER_ID, "Other Teacher", "teacher"),
                ],
            )

            conn.executemany(
                "INSERT INTO teacher_tests (id, title, creator_id) VALUES (?, ?, ?)",
                [
                    (self.EXAM_ID, "Exam to Delete", self.TEACHER_ID),
                    (self.OTHER_EXAM_ID, "Exam to Keep", self.TEACHER_ID),
                ],
            )

            conn.execute(
                "INSERT INTO teacher_test_assignments (id, test_id, student_id) "
                "VALUES (1, ?, ?)",
                (self.EXAM_ID, self.STUDENT_ID),
            )
            conn.execute(
                "INSERT INTO teacher_test_questions (id, test_id) VALUES (?, ?)",
                (self.QUESTION_ID, self.EXAM_ID),
            )
            conn.execute(
                "INSERT INTO teacher_test_sessions (id, test_id, student_id) "
                "VALUES (1, ?, ?)",
                (self.EXAM_ID, self.STUDENT_ID),
            )
            conn.execute(
                "INSERT INTO teacher_test_attempts (id, test_id, student_id) "
                "VALUES (?, ?, ?)",
                (self.ATTEMPT_ID, self.EXAM_ID, self.STUDENT_ID),
            )
            conn.execute(
                "INSERT INTO teacher_test_answers (id, attempt_id, question_id) "
                "VALUES (1, ?, ?)",
                (self.ATTEMPT_ID, self.QUESTION_ID),
            )
            conn.execute(
                "INSERT INTO teacher_test_password_attempts (test_id, student_id) "
                "VALUES (?, ?)",
                (self.EXAM_ID, self.STUDENT_ID),
            )
            conn.execute(
                "INSERT INTO teacher_test_password_unlocks (test_id, student_id) "
                "VALUES (?, ?)",
                (self.EXAM_ID, self.STUDENT_ID),
            )
            conn.execute(
                "INSERT INTO teacher_exam_monitoring_events "
                "(id, exam_id, student_id) VALUES (1, ?, ?)",
                (self.EXAM_ID, self.STUDENT_ID),
            )
            conn.executemany(
                "INSERT INTO notifications "
                "(id, user_id, type, reference_type, reference_id) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (1, self.TEACHER_ID, "exam_submitted",
                     "teacher_test", self.EXAM_ID),
                    (2, self.TEACHER_ID, "exam_submitted",
                     "teacher_test", self.OTHER_EXAM_ID),
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def test_deleting_exam_removes_dependents_and_preserves_other_exam(self):
        result = teacher_exams.delete_exam(self.EXAM_ID, self.request)

        self.assertTrue(result["success"])
        self.assertEqual(result["exam_id"], self.EXAM_ID)

        conn = self.connect()
        try:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM teacher_tests WHERE id = ?",
                    (self.EXAM_ID,),
                ).fetchone()[0],
                0,
            )

            for table in (
                "teacher_test_assignments",
                "teacher_test_questions",
                "teacher_test_sessions",
                "teacher_test_attempts",
                "teacher_test_answers",
                "teacher_test_password_attempts",
                "teacher_test_password_unlocks",
                "teacher_exam_monitoring_events",
            ):
                with self.subTest(table=table):
                    self.assertEqual(
                        conn.execute(
                            f"SELECT COUNT(*) FROM {table}"
                        ).fetchone()[0],
                        0,
                        f"{table} should have no rows for the deleted exam",
                    )

            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM notifications "
                    "WHERE reference_id = ?",
                    (self.EXAM_ID,),
                ).fetchone()[0],
                0,
            )

            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM teacher_tests WHERE id = ?",
                    (self.OTHER_EXAM_ID,),
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM notifications "
                    "WHERE reference_id = ?",
                    (self.OTHER_EXAM_ID,),
                ).fetchone()[0],
                1,
            )

            self.assertEqual(
                conn.execute("PRAGMA foreign_key_check").fetchall(),
                [],
            )
        finally:
            conn.close()

    def test_teacher_cannot_delete_another_teachers_exam(self):
        with patch.object(
            teacher_exams,
            "require_teacher",
            return_value={
                "id": self.OTHER_TEACHER_ID,
                "name": "Other Teacher",
                "role": "teacher",
            },
        ):
            with self.assertRaises(HTTPException) as raised:
                teacher_exams.delete_exam(self.EXAM_ID, self.request)

        self.assertEqual(raised.exception.status_code, 404)

        conn = self.connect()
        try:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM teacher_tests WHERE id = ?",
                    (self.EXAM_ID,),
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM teacher_test_answers"
                ).fetchone()[0],
                1,
            )
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
