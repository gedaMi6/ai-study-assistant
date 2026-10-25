import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api import student_exams


class StudentExamIntegrityTests(unittest.TestCase):
    STUDENT_ID = 2
    TEACHER_ID = 1
    EXAM_ID = "exam-test-1"
    QUESTION_ID = 11

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_exams.db"
        self.create_schema()
        self.seed_exam()

        self.connection_patch = patch.object(
            student_exams, "get_connection", side_effect=self.connect
        )
        self.student_patch = patch.object(
            student_exams,
            "require_student",
            return_value={
                "id": self.STUDENT_ID,
                "name": "Test Student",
                "role": "student",
            },
        )

        self.connection_patch.start()
        self.student_patch.start()
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(self.connection_patch.stop)
        self.addCleanup(self.student_patch.stop)

        self.request = Request({
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": f"/api/student/exams/{self.EXAM_ID}/submit",
            "raw_path": (
                f"/api/student/exams/{self.EXAM_ID}/submit".encode()
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
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                );

                CREATE TABLE teacher_tests (
                    id TEXT PRIMARY KEY,
                    creator_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    published_at TEXT,
                    duration_minutes INTEGER NOT NULL DEFAULT 60,
                    deadline_at TEXT,
                    password_hash TEXT,
                    FOREIGN KEY (creator_id) REFERENCES users(id)
                );

                CREATE TABLE teacher_test_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(test_id, student_id),
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    question_index INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    options TEXT NOT NULL DEFAULT '[]',
                    correct_answer INTEGER NOT NULL,
                    explanation TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    question_type TEXT NOT NULL
                        DEFAULT 'multiple_choice',
                    correct_answer_text TEXT,
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE
                );


                CREATE TABLE teacher_test_password_unlocks (
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    unlocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (test_id, student_id),
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_password_attempts (
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (test_id, student_id),
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    student_id INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    answers_json TEXT NOT NULL DEFAULT '{}',
                    submitted_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(test_id, student_id),
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
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
                    FOREIGN KEY (test_id)
                        REFERENCES teacher_tests(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE teacher_test_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    selected_answer INTEGER,
                    correct_answer INTEGER NOT NULL,
                    is_correct INTEGER NOT NULL,
                    selected_answer_text TEXT,
                    correct_answer_text TEXT,
                    FOREIGN KEY (attempt_id)
                        REFERENCES teacher_test_attempts(id) ON DELETE CASCADE,
                    FOREIGN KEY (question_id)
                        REFERENCES teacher_test_questions(id) ON DELETE CASCADE
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
                    FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );
            """)

    def seed_exam(self):
        now = student_exams._now_exam_time()
        self.future_expiry = (now + timedelta(minutes=30)).isoformat()
        self.past_expiry = (now - timedelta(minutes=5)).isoformat()

        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO users (id, name, email, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (self.TEACHER_ID, "Test Teacher",
                     "teacher@example.test", "test-hash", "teacher"),
                    (self.STUDENT_ID, "Test Student",
                     "student@example.test", "test-hash", "student"),
                ],
            )

            conn.execute(
                """
                INSERT INTO teacher_tests
                    (id, creator_id, title, status, duration_minutes)
                VALUES (?, ?, ?, 'published', 60)
                """,
                (self.EXAM_ID, self.TEACHER_ID, "Integrity Test"),
            )

            conn.execute(
                """
                INSERT INTO teacher_test_assignments (test_id, student_id)
                VALUES (?, ?)
                """,
                (self.EXAM_ID, self.STUDENT_ID),
            )

            conn.execute(
                """
                INSERT INTO teacher_test_questions
                    (id, test_id, question_index, question, options,
                     correct_answer, question_type)
                VALUES (?, ?, 1, ?, ?, 1, 'multiple_choice')
                """,
                (
                    self.QUESTION_ID,
                    self.EXAM_ID,
                    "Which option is correct?",
                    json.dumps(["Wrong", "Correct", "Also wrong"]),
                ),
            )

            conn.execute(
                """
                INSERT INTO teacher_test_sessions
                    (test_id, student_id, started_at, expires_at, answers_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self.EXAM_ID,
                    self.STUDENT_ID,
                    now.isoformat(),
                    self.future_expiry,
                    json.dumps({str(self.QUESTION_ID): 0}),
                ),
            )

    def submit(self, answers=None, auto_submit=False):
        return student_exams.submit_exam(
            self.EXAM_ID,
            student_exams.ExamSubmit(
                answers=answers or {},
                auto_submit=auto_submit,
            ),
            self.request,
        )

    def counts(self):
        with self.connect() as conn:
            return {
                table: conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                for table in (
                    "teacher_test_attempts",
                    "teacher_test_answers",
                    "notifications",
                )
            }

    def attempt(self):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM teacher_test_attempts
                WHERE test_id = ? AND student_id = ?
                """,
                (self.EXAM_ID, self.STUDENT_ID),
            ).fetchone()
            return dict(row) if row else None

    def answer(self):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM teacher_test_answers LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def session(self):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM teacher_test_sessions
                WHERE test_id = ? AND student_id = ?
                """,
                (self.EXAM_ID, self.STUDENT_ID),
            ).fetchone()
            return dict(row)

    def test_manual_submission_uses_latest_payload_answers(self):
        result = self.submit(answers={str(self.QUESTION_ID): 1})

        self.assertEqual(result["status"], "success")

        # The submission response must never reveal an unreleased score.
        public_result = result["result"]
        self.assertFalse(public_result["score_released"])
        self.assertIsNone(public_result["score"])
        self.assertIsNone(public_result["percentage"])

        # Fetching the submitted exam must continue to hide the score.
        exam_response = student_exams.get_exam(
            self.EXAM_ID, self.request
        )
        public_exam = exam_response["exam"]
        self.assertTrue(public_exam["completed"])
        self.assertFalse(public_exam["score_released"])
        self.assertIsNone(public_exam["score"])
        self.assertIsNone(public_exam["percentage"])

        # The private database still stores the correct result.
        self.assertEqual(self.attempt()["score"], 1)
        self.assertEqual(self.attempt()["total_questions"], 1)
        self.assertEqual(self.attempt()["percentage"], 100.0)
        self.assertEqual(self.answer()["selected_answer"], 1)
        self.assertEqual(self.answer()["is_correct"], 1)
        self.assertIsNotNone(self.session()["submitted_at"])

    def test_expired_submission_uses_saved_answers_not_payload(self):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE teacher_test_sessions
                SET expires_at = ?
                WHERE test_id = ? AND student_id = ?
                """,
                (self.past_expiry, self.EXAM_ID, self.STUDENT_ID),
            )

        with patch.object(
            student_exams,
            "_now_exam_time",
            return_value=student_exams._parse_exam_time(self.past_expiry),
        ):
            result = self.submit(
                answers={str(self.QUESTION_ID): 1},
                auto_submit=True,
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(self.attempt()["score"], 0)
        self.assertEqual(self.answer()["selected_answer"], 0)
        self.assertEqual(self.answer()["is_correct"], 0)

    def test_expired_manual_submission_is_rejected(self):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE teacher_test_sessions
                SET expires_at = ?
                WHERE test_id = ? AND student_id = ?
                """,
                (self.past_expiry, self.EXAM_ID, self.STUDENT_ID),
            )

        before = self.counts()

        with patch.object(
            student_exams,
            "_now_exam_time",
            return_value=student_exams._parse_exam_time(self.past_expiry),
        ):
            with self.assertRaises(HTTPException) as caught:
                self.submit(answers={str(self.QUESTION_ID): 1})

        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.counts(), before)

    def test_duplicate_submission_does_not_create_second_attempt(self):
        self.submit(answers={str(self.QUESTION_ID): 1})
        before = self.counts()

        with self.assertRaises(HTTPException) as caught:
            self.submit(answers={str(self.QUESTION_ID): 0})

        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.attempt()["score"], 1)

    def test_failed_notification_insert_rolls_back_entire_submission(self):
        with self.connect() as conn:
            conn.execute("""
                CREATE TRIGGER fail_exam_notification
                BEFORE INSERT ON notifications
                BEGIN
                    SELECT RAISE(ABORT, 'forced test failure');
                END;
            """)

        with self.assertRaises(sqlite3.IntegrityError):
            self.submit(answers={str(self.QUESTION_ID): 1})

        self.assertEqual(
            self.counts(),
            {
                "teacher_test_attempts": 0,
                "teacher_test_answers": 0,
                "notifications": 0,
            },
        )
        self.assertIsNone(self.session()["submitted_at"])

    def test_expiry_worker_finalizes_session_only_once(self):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE teacher_test_sessions
                SET expires_at = ?, answers_json = ?
                WHERE test_id = ? AND student_id = ?
                """,
                (
                    self.past_expiry,
                    json.dumps({str(self.QUESTION_ID): 1}),
                    self.EXAM_ID,
                    self.STUDENT_ID,
                ),
            )

        with patch.object(
            student_exams,
            "_now_exam_time",
            return_value=student_exams._parse_exam_time(self.past_expiry),
        ):
            first = student_exams.process_expired_exam_sessions()
            second = student_exams.process_expired_exam_sessions()

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        self.assertEqual(self.attempt()["score"], 1)
        self.assertEqual(self.counts()["teacher_test_attempts"], 1)
        self.assertEqual(self.counts()["teacher_test_answers"], 1)
        self.assertIsNotNone(self.session()["submitted_at"])


    def test_unassigned_student_cannot_retrieve_exam(self):
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO users
                   (id, name, email, password_hash, role)
                   VALUES (3, 'Unassigned Student',
                           'unassigned@example.test', 'test-hash', 'student')"""
            )

        with patch.object(
            student_exams,
            "require_student",
            return_value={"id": 3, "name": "Unassigned Student",
                          "role": "student"},
        ):
            with self.assertRaises(HTTPException) as caught:
                student_exams.get_exam(self.EXAM_ID, self.request)

        self.assertEqual(caught.exception.status_code, 404)

    def test_unpublished_exam_cannot_be_retrieved(self):
        with self.connect() as conn:
            conn.execute(
                "UPDATE teacher_tests SET status = 'draft' WHERE id = ?",
                (self.EXAM_ID,),
            )

        with self.assertRaises(HTTPException) as caught:
            student_exams.get_exam(self.EXAM_ID, self.request)

        self.assertEqual(caught.exception.status_code, 404)

    def test_password_protected_exam_hides_questions_before_unlock(self):
        with self.connect() as conn:
            conn.execute(
                "UPDATE teacher_tests SET password_hash = ? WHERE id = ?",
                ("test-password-hash", self.EXAM_ID),
            )
            conn.execute(
                """DELETE FROM teacher_test_sessions
                   WHERE test_id = ? AND student_id = ?""",
                (self.EXAM_ID, self.STUDENT_ID),
            )

        result = student_exams.get_exam(self.EXAM_ID, self.request)
        exam = result["exam"]

        self.assertTrue(exam["password_required"])
        self.assertFalse(exam["unlocked"])
        self.assertEqual(exam["questions"], [])
        self.assertFalse(exam["completed"])

        with self.connect() as conn:
            session = conn.execute(
                """SELECT 1 FROM teacher_test_sessions
                   WHERE test_id = ? AND student_id = ?""",
                (self.EXAM_ID, self.STUDENT_ID),
            ).fetchone()
        self.assertIsNone(session)

    def test_password_protected_autosave_is_blocked_before_unlock(self):
        with self.connect() as conn:
            conn.execute(
                "UPDATE teacher_tests SET password_hash = ? WHERE id = ?",
                ("test-password-hash", self.EXAM_ID),
            )

        with self.assertRaises(HTTPException) as caught:
            student_exams.autosave_exam(
                self.EXAM_ID,
                student_exams.ExamAutosave(
                    answers={str(self.QUESTION_ID): 1}
                ),
                self.request,
            )

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(
            self.session()["answers_json"],
            json.dumps({str(self.QUESTION_ID): 0}),
        )

    def test_five_incorrect_passwords_trigger_lockout_and_block_retry(self):
        with self.connect() as conn:
            conn.execute(
                "UPDATE teacher_tests SET password_hash = ? WHERE id = ?",
                ("test-password-hash", self.EXAM_ID),
            )

        with patch.object(
            student_exams, "verify_password", return_value=False
        ) as verify:
            for number in range(1, 6):
                with self.assertRaises(HTTPException) as caught:
                    student_exams.unlock_exam(
                        self.EXAM_ID,
                        student_exams.ExamUnlockRequest(
                            password="wrong-password"
                        ),
                        self.request,
                    )

                self.assertEqual(
                    caught.exception.status_code,
                    429 if number == 5 else 403,
                )

            with self.connect() as conn:
                record = conn.execute(
                    """SELECT failed_count, locked_until
                       FROM teacher_test_password_attempts
                       WHERE test_id = ? AND student_id = ?""",
                    (self.EXAM_ID, self.STUDENT_ID),
                ).fetchone()

            self.assertEqual(record["failed_count"], 5)
            self.assertIsNotNone(record["locked_until"])

            with self.assertRaises(HTTPException) as caught:
                student_exams.unlock_exam(
                    self.EXAM_ID,
                    student_exams.ExamUnlockRequest(
                        password="correct-password"
                    ),
                    self.request,
                )

            self.assertEqual(caught.exception.status_code, 429)
            self.assertEqual(verify.call_count, 5)

    def test_correct_password_unlocks_exam_and_clears_failed_attempts(self):
        with self.connect() as conn:
            conn.execute(
                "UPDATE teacher_tests SET password_hash = ? WHERE id = ?",
                ("test-password-hash", self.EXAM_ID),
            )
            conn.execute(
                """INSERT INTO teacher_test_password_attempts
                   (test_id, student_id, failed_count, locked_until, updated_at)
                   VALUES (?, ?, 3, NULL, ?)""",
                (
                    self.EXAM_ID,
                    self.STUDENT_ID,
                    student_exams._now_exam_time().isoformat(),
                ),
            )

        with patch.object(
            student_exams, "verify_password", return_value=True
        ):
            result = student_exams.unlock_exam(
                self.EXAM_ID,
                student_exams.ExamUnlockRequest(
                    password="correct-password"
                ),
                self.request,
            )

        self.assertTrue(result["unlocked"])

        with self.connect() as conn:
            unlock = conn.execute(
                """SELECT 1 FROM teacher_test_password_unlocks
                   WHERE test_id = ? AND student_id = ?""",
                (self.EXAM_ID, self.STUDENT_ID),
            ).fetchone()
            attempts = conn.execute(
                """SELECT 1 FROM teacher_test_password_attempts
                   WHERE test_id = ? AND student_id = ?""",
                (self.EXAM_ID, self.STUDENT_ID),
            ).fetchone()

        self.assertIsNotNone(unlock)
        self.assertIsNone(attempts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
