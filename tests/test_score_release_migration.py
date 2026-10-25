import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database import database


class ScoreReleaseMigrationTests(unittest.TestCase):
    def test_legacy_attempts_migrate_safely_and_repeatedly(self):
        with tempfile.TemporaryDirectory(
            prefix="kania_score_migration_"
        ) as temp_dir:
            db_path = Path(temp_dir) / "legacy.db"

            with patch.object(database, "DATABASE_PATH", db_path):
                # initialize_database expects an existing users table
                # when it first checks for legacy user columns.
                with sqlite3.connect(db_path) as connection:
                    connection.execute("""
                        CREATE TABLE users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            email TEXT NOT NULL UNIQUE,
                            password_hash TEXT NOT NULL,
                            role TEXT NOT NULL DEFAULT 'student',
                            sidebar_collapsed INTEGER NOT NULL DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                # Create the rest of the disposable application schema.
                database.initialize_database()

                # Replace the attempts table with its legacy definition.
                with sqlite3.connect(db_path) as connection:
                    connection.execute("DROP TABLE teacher_test_answers")
                    connection.execute("DROP TABLE teacher_test_attempts")
                    connection.execute("""
                        CREATE TABLE teacher_test_attempts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            test_id TEXT NOT NULL,
                            student_id INTEGER NOT NULL,
                            score INTEGER NOT NULL,
                            total_questions INTEGER NOT NULL,
                            percentage REAL NOT NULL,
                            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(test_id, student_id)
                        )
                    """)
                    connection.execute("""
                        INSERT INTO teacher_test_attempts (
                            test_id, student_id, score,
                            total_questions, percentage
                        )
                        VALUES ('legacy-test', 1, 7, 10, 70.0)
                    """)

                # Run the migration twice to verify idempotency.
                database.initialize_database()
                database.initialize_database()

                with sqlite3.connect(db_path) as connection:
                    columns = [
                        row[1]
                        for row in connection.execute(
                            "PRAGMA table_info(teacher_test_attempts)"
                        )
                    ]
                    attempt = connection.execute("""
                        SELECT score, total_questions,
                               percentage, score_released
                        FROM teacher_test_attempts
                        WHERE test_id = 'legacy-test'
                    """).fetchone()

                self.assertEqual(columns.count("score_released"), 1)
                self.assertEqual(attempt, (7, 10, 70.0, 0))


if __name__ == "__main__":
    unittest.main()
