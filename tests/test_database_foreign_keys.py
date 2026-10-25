import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database import database


class DatabaseForeignKeyTests(unittest.TestCase):
    def test_application_connection_enables_foreign_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "foreign_keys_test.db"

            with patch.object(database, "DATABASE_PATH", db_path):
                setup = sqlite3.connect(db_path)
                try:
                    setup.executescript("""
                        CREATE TABLE users (
                            id INTEGER PRIMARY KEY
                        );

                        CREATE TABLE sessions (
                            id INTEGER PRIMARY KEY,
                            user_id INTEGER NOT NULL,
                            FOREIGN KEY (user_id)
                                REFERENCES users(id) ON DELETE CASCADE
                        );

                        INSERT INTO users (id) VALUES (1);
                        INSERT INTO sessions (id, user_id) VALUES (1, 1);
                    """)
                    setup.commit()
                finally:
                    setup.close()

                conn = database.get_connection()
                try:
                    enabled = conn.execute(
                        "PRAGMA foreign_keys"
                    ).fetchone()[0]
                    self.assertEqual(enabled, 1)

                    conn.execute("DELETE FROM users WHERE id = 1")
                    remaining = conn.execute(
                        "SELECT COUNT(*) FROM sessions"
                    ).fetchone()[0]
                    self.assertEqual(remaining, 0)
                    conn.commit()
                finally:
                    conn.close()


if __name__ == "__main__":
    unittest.main()
