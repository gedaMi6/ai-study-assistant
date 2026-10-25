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
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_email
        ON email_verification_tokens(email)
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

    connection.execute("""
        CREATE TABLE IF NOT EXISTS flashcard_sets (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            document_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id),

            FOREIGN KEY (document_id)
                REFERENCES documents(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id TEXT PRIMARY KEY,
            set_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            document_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            topic TEXT,
            difficulty TEXT DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'learning',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (set_id)
                REFERENCES flashcard_sets(id),

            FOREIGN KEY (user_id)
                REFERENCES users(id),

            FOREIGN KEY (document_id)
                REFERENCES documents(id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_flashcard_sets_user
        ON flashcard_sets(user_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_flashcards_set
        ON flashcards(set_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_flashcards_user
        ON flashcards(user_id)
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS study_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            performance REAL NOT NULL,
            priority TEXT NOT NULL,
            reason TEXT NOT NULL,
            what_to_study TEXT NOT NULL,
            next_step TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_study_recommendations_user
        ON study_recommendations(user_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_study_recommendations_user_topic
        ON study_recommendations(user_id, topic)
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS study_topic_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            performance REAL NOT NULL,
            review TEXT NOT NULL,
            sources TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, topic),

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_study_topic_reviews_user
        ON study_topic_reviews(user_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_study_topic_reviews_user_topic
        ON study_topic_reviews(user_id, topic)
    """)


    # ============================================================
    # TEACHER TEST SYSTEM
    # Separate from the existing AI-generated student quizzes.
    # ============================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_tests (
            id TEXT PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP NULL,

            FOREIGN KEY (creator_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_test_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT NOT NULL,
            question_index INTEGER NOT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_answer INTEGER NOT NULL,
            explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (test_id)
                REFERENCES teacher_tests(id)
                ON DELETE CASCADE,

            UNIQUE(test_id, question_index)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_test_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (test_id)
                REFERENCES teacher_tests(id)
                ON DELETE CASCADE,

            FOREIGN KEY (student_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            UNIQUE(test_id, student_id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_test_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage REAL NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (test_id)
                REFERENCES teacher_tests(id)
                ON DELETE CASCADE,

            FOREIGN KEY (student_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            UNIQUE(test_id, student_id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_test_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_answer INTEGER,
            correct_answer INTEGER NOT NULL,
            is_correct INTEGER NOT NULL,

            FOREIGN KEY (attempt_id)
                REFERENCES teacher_test_attempts(id)
                ON DELETE CASCADE,

            FOREIGN KEY (question_id)
                REFERENCES teacher_test_questions(id)
                ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_tests_creator
        ON teacher_tests(creator_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_test_questions_test
        ON teacher_test_questions(test_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_test_assignments_student
        ON teacher_test_assignments(student_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_test_attempts_test
        ON teacher_test_attempts(test_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_test_attempts_student
        ON teacher_test_attempts(student_id)
    """)


    # ============================================================
    # TEACHER EXAM MONITORING
    # Records browser-level exam activity such as tab/window
    # changes and forbidden keyboard shortcuts.
    # ============================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_exam_monitoring_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_detail TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_seen INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (exam_id)
                REFERENCES teacher_tests(id)
                ON DELETE CASCADE,

            FOREIGN KEY (student_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_exam_monitoring_exam
        ON teacher_exam_monitoring_events(exam_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_exam_monitoring_student
        ON teacher_exam_monitoring_events(student_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_exam_monitoring_unseen
        ON teacher_exam_monitoring_events(is_seen)
    """)


    # ============================================================
    # TEACHER MY TASKS SYSTEM
    # Separate from AI-generated study recommendations.
    # A task can contain multiple materials from different sources,
    # books, chapters, topics, and sections.
    # ============================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_tasks (
            id TEXT PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            instructions TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'normal',
            due_date TIMESTAMP NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP NULL,

            FOREIGN KEY (creator_id)
                REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_task_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            material_index INTEGER NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'reference',
            document_id TEXT NULL,
            title TEXT NOT NULL,
            book TEXT NULL,
            chapter TEXT NULL,
            topic TEXT NULL,
            section TEXT NULL,
            instructions TEXT NULL,
            external_reference TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (task_id)
                REFERENCES teacher_tasks(id)
                ON DELETE CASCADE,

            UNIQUE(task_id, material_index)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_task_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (task_id)
                REFERENCES teacher_tasks(id)
                ON DELETE CASCADE,

            FOREIGN KEY (student_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            UNIQUE(task_id, student_id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_task_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'assigned',
            completed_at TIMESTAMP NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (task_id)
                REFERENCES teacher_tasks(id)
                ON DELETE CASCADE,

            FOREIGN KEY (student_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            UNIQUE(task_id, student_id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_tasks_creator
        ON teacher_tasks(creator_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_tasks_status
        ON teacher_tasks(status)
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            reference_type TEXT NULL,
            reference_id TEXT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_user
        ON notifications(user_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_unread
        ON notifications(user_id, is_read)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_reference
        ON notifications(reference_type, reference_id)
    """)

    connection.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        uq_exam_result_notification_per_student
        ON notifications(user_id, reference_id)
        WHERE type = 'exam_result_released'
          AND reference_type = 'teacher_test'
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_task_materials_task
        ON teacher_task_materials(task_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_task_assignments_student
        ON teacher_task_assignments(student_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher_task_progress_student
        ON teacher_task_progress(student_id)
    """)



    # KANIA exam question-type migrations. Safe to run repeatedly.
    def ensure_exam_column(table, column, definition):
        existing = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})")
        }
        if column not in existing:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

    ensure_exam_column(
        "teacher_test_questions", "question_type",
        "TEXT NOT NULL DEFAULT 'multiple_choice'"
    )
    ensure_exam_column(
        "teacher_test_questions", "correct_answer_text", "TEXT"
    )
    ensure_exam_column(
        "teacher_test_answers", "selected_answer_text", "TEXT"
    )
    ensure_exam_column(
        "teacher_test_answers", "correct_answer_text", "TEXT"
    )

    # KANIA timed teacher-exam support. Safe to run repeatedly.
    ensure_exam_column(
        "teacher_tests", "duration_minutes",
        "INTEGER NOT NULL DEFAULT 60"
    )
    ensure_exam_column(
        "teacher_tests", "deadline_at", "TEXT"
    )
    ensure_exam_column(
        "teacher_tests", "password_hash", "TEXT"
    )

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_test_password_unlocks (
            test_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            unlocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (test_id, student_id),
            FOREIGN KEY (test_id) REFERENCES teacher_tests(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_test_password_attempts (
            test_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            failed_count INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (test_id, student_id),
            FOREIGN KEY (test_id) REFERENCES teacher_tests(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teacher_test_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            answers_json TEXT NOT NULL DEFAULT '{}',
            submitted_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (test_id)
                REFERENCES teacher_tests(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id)
                REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(test_id, student_id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_teacher_test_sessions_student
        ON teacher_test_sessions(student_id, test_id)
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
