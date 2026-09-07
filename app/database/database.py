import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASE_PATH = BASE_DIR / "data" / "study_assistant.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = get_connection()

    # Add role to existing users table if this database predates authentication roles.
    user_columns = [
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    ]

    if "role" not in user_columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'"
        )
    if "sidebar_collapsed" not in user_columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN sidebar_collapsed INTEGER NOT NULL DEFAULT 0"
        )

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user
        ON password_reset_tokens(user_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user
        ON sessions(user_id)
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_user
        ON chat_sessions(user_id)
    """)

    # Add pinning support to existing chat_sessions tables.
    chat_session_columns = [
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(chat_sessions)"
        ).fetchall()
    ]

    if "is_pinned" not in chat_session_columns:
        connection.execute(
            """
            ALTER TABLE chat_sessions
            ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0
            """
        )

    connection.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            extracted_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (document_id)
                REFERENCES documents(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_session
        ON conversations(session_id)
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (document_id)
                REFERENCES documents(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS quiz_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            question_index INTEGER NOT NULL,
            selected_answer INTEGER,
            correct_answer INTEGER NOT NULL,
            is_correct INTEGER NOT NULL,

            FOREIGN KEY (attempt_id)
                REFERENCES quiz_attempts(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            questions TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP NULL,

            FOREIGN KEY (document_id)
                REFERENCES documents(id)
        )
    """)

    # Add topic tracking to existing quiz answer records.
    columns = connection.execute(
        "PRAGMA table_info(quiz_answers)"
    ).fetchall()

    column_names = {
        column["name"]
        for column in columns
    }

    if "topic" not in column_names:
        connection.execute(
            "ALTER TABLE quiz_answers ADD COLUMN topic TEXT"
        )

    # Add submission tracking to existing quizzes.
    columns = connection.execute(
        "PRAGMA table_info(quizzes)"
    ).fetchall()

    column_names = {
        column["name"]
        for column in columns
    }

    if "submitted_at" not in column_names:
        connection.execute(
            "ALTER TABLE quizzes ADD COLUMN submitted_at TIMESTAMP NULL"
        )

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_quiz_attempts_document
        ON quiz_attempts(document_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_quiz_answers_attempt
        ON quiz_answers(attempt_id)
    """)

    connection.commit()
    connection.close()


def save_chunks(document_id: str, chunks: list[str]):
    connection = get_connection()

    # Add role to existing users table if this database predates authentication roles.
    user_columns = [
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    ]

    if "role" not in user_columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'"
        )

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user
        ON sessions(user_id)
    """)

    connection.execute(
        "DELETE FROM document_chunks WHERE document_id = ?",
        (document_id,)
    )

    for index, chunk in enumerate(chunks):
        connection.execute(
            """
            INSERT INTO document_chunks (
                document_id,
                chunk_index,
                content
            )
            VALUES (?, ?, ?)
            """,
            (
                document_id,
                index,
                chunk
            )
        )

    connection.commit()
    connection.close()


def save_message(session_id: str, role: str, content: str):
    connection = get_connection()

    # Add role to existing users table if this database predates authentication roles.
    user_columns = [
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    ]

    if "role" not in user_columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'"
        )

    if "sidebar_collapsed" not in user_columns:
        connection.excute(
           "ALTER TABLE users ADD COLUMN sidebar_collapsed INTEGER NOT NULL DEFAULT 0"
        )

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user
        ON sessions(user_id)
    """)

    connection.execute(
        """
        INSERT INTO conversations (
            session_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            session_id,
            role,
            content
        )
    )

    connection.commit()
    connection.close()


def get_conversation_history(
    session_id: str,
    limit: int = 10
) -> list[dict]:
    connection = get_connection()

    # Add role to existing users table if this database predates authentication roles.
    user_columns = [
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    ]

    if "role" not in user_columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'"
        )

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user
        ON sessions(user_id)
    """)

    rows = connection.execute(
        """
        SELECT role, content
        FROM conversations
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            session_id,
            limit
        )
    ).fetchall()

    connection.close()

    rows.reverse()

    return [
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in rows
    ]
