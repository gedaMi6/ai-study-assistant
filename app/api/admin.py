from fastapi import APIRouter, HTTPException, Request

from app.database.database import get_connection
from app.api.auth import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


def require_admin(request: Request):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )

    return user


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard")
def get_admin_dashboard(request: Request):
    require_admin(request)

    connection = get_connection()

    try:
        students = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM users
            WHERE role = 'student'
            """
        ).fetchone()["count"]

        documents = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM documents
            """
        ).fetchone()["count"]

        quiz_attempts = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM quiz_attempts
            """
        ).fetchone()["count"]

        average_score = connection.execute(
            """
            SELECT COALESCE(AVG(percentage), 0) AS average
            FROM quiz_attempts
            """
        ).fetchone()["average"]

        chat_messages = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM conversations
            """
        ).fetchone()["count"]

        recent_quizzes = connection.execute(
            """
            SELECT
                qa.id,
                qa.score,
                qa.total_questions,
                qa.percentage,
                qa.created_at,
                d.filename,
                u.name AS student_name
            FROM quiz_attempts qa
            LEFT JOIN documents d
                ON qa.document_id = d.id
            LEFT JOIN users u
                ON qa.user_id = u.id
            ORDER BY qa.created_at DESC
            LIMIT 8
            """
        ).fetchall()

        recent_documents = connection.execute(
            """
            SELECT
                d.id,
                d.filename,
                d.created_at,
                COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN document_chunks c
                ON d.id = c.document_id
            GROUP BY d.id, d.filename, d.created_at
            ORDER BY d.created_at DESC
            LIMIT 6
            """
        ).fetchall()

        return {
            "status": "success",
            "overview": {
                "students": students,
                "documents": documents,
                "quiz_attempts": quiz_attempts,
                "average_score": round(float(average_score or 0), 1),
                "chat_messages": chat_messages
            },
            "recent_quizzes": [
                {
                    "id": row["id"],
                    "score": row["score"],
                    "total_questions": row["total_questions"],
                    "percentage": float(row["percentage"] or 0),
                    "created_at": row["created_at"],
                    "filename": row["filename"] or "Unknown document",
                    "student_name": row["student_name"] or "Unassigned"
                }
                for row in recent_quizzes
            ],
            "recent_documents": [
                {
                    "id": row["id"],
                    "filename": row["filename"],
                    "created_at": row["created_at"],
                    "chunk_count": row["chunk_count"]
                }
                for row in recent_documents
            ]
        }

    finally:
        connection.close()


# ============================================================
# DOCUMENTS
# ============================================================

@router.get("/documents")
def get_admin_documents(request: Request):
    require_admin(request)

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                d.id,
                d.filename,
                d.created_at,
                COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN document_chunks c
                ON d.id = c.document_id
            GROUP BY d.id, d.filename, d.created_at
            ORDER BY d.created_at DESC
            """
        ).fetchall()

        return {
            "status": "success",
            "documents": [
                {
                    "id": row["id"],
                    "filename": row["filename"],
                    "created_at": row["created_at"],
                    "chunk_count": row["chunk_count"]
                }
                for row in rows
            ]
        }

    finally:
        connection.close()


# ============================================================
# STUDENTS
# ============================================================

@router.get("/students")
def get_admin_students(request: Request):
    require_admin(request)

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                u.id,
                u.name,
                u.email,
                u.created_at,
                COUNT(qa.id) AS quiz_attempts,
                COALESCE(AVG(qa.percentage), 0) AS average_score,
                MAX(qa.created_at) AS last_quiz
            FROM users u
            LEFT JOIN quiz_attempts qa
                ON qa.user_id = u.id
            WHERE u.role = 'student'
            GROUP BY
                u.id,
                u.name,
                u.email,
                u.created_at
            ORDER BY u.created_at DESC
            """
        ).fetchall()

        return {
            "status": "success",
            "students": [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "email": row["email"],
                    "created_at": row["created_at"],
                    "quiz_attempts": row["quiz_attempts"],
                    "average_score": round(
                        float(row["average_score"] or 0),
                        1
                    ),
                    "last_quiz": row["last_quiz"]
                }
                for row in rows
            ]
        }

    finally:
        connection.close()


# ============================================================
# STUDENT DETAILS
# ============================================================

@router.get("/students/{student_id}")
def get_student_details(
    student_id: int,
    request: Request
):
    require_admin(request)

    connection = get_connection()

    try:
        student = connection.execute(
            """
            SELECT
                id,
                name,
                email,
                created_at,
                profile_image
            FROM users
            WHERE id = ?
              AND role = 'student'
            """,
            (student_id,)
        ).fetchone()

        if not student:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        attempts = connection.execute(
            """
            SELECT
                qa.id,
                qa.score,
                qa.total_questions,
                qa.percentage,
                qa.created_at,
                d.filename
            FROM quiz_attempts qa
            LEFT JOIN documents d
                ON qa.document_id = d.id
            WHERE qa.user_id = ?
            ORDER BY qa.created_at DESC
            LIMIT 20
            """,
            (student_id,)
        ).fetchall()

        topic_rows = connection.execute(
            """
            SELECT
                qa.topic,
                COUNT(*) AS questions_answered,
                SUM(qa.is_correct) AS correct_answers,
                ROUND(
                    100.0 * SUM(qa.is_correct) / COUNT(*),
                    1
                ) AS percentage
            FROM quiz_answers qa
            JOIN quiz_attempts q
                ON q.id = qa.attempt_id
            WHERE q.user_id = ?
              AND qa.topic IS NOT NULL
              AND TRIM(qa.topic) != ''
            GROUP BY qa.topic
            ORDER BY percentage ASC
            """,
            (student_id,)
        ).fetchall()

        return {
            "status": "success",
            "student": {
                "id": student["id"],
                "name": student["name"],
                "email": student["email"],
                "created_at": student["created_at"],
                "profile_image": student["profile_image"]
            },
            "quiz_attempts": [
                {
                    "id": row["id"],
                    "score": row["score"],
                    "total_questions": row["total_questions"],
                    "percentage": float(row["percentage"] or 0),
                    "created_at": row["created_at"],
                    "filename": row["filename"] or "Unknown document"
                }
                for row in attempts
            ],
            "topics": [
                {
                    "topic": row["topic"],
                    "questions_answered": row["questions_answered"],
                    "correct_answers": row["correct_answers"],
                    "percentage": float(row["percentage"] or 0)
                }
                for row in topic_rows
            ]
        }

    finally:
        connection.close()


# ============================================================
# ANALYTICS
# ============================================================

@router.get("/analytics")
def get_admin_analytics(request: Request):
    require_admin(request)

    connection = get_connection()

    try:
        topic_rows = connection.execute(
            """
            SELECT
                topic,
                COUNT(*) AS questions_answered,
                SUM(is_correct) AS correct_answers,
                ROUND(
                    100.0 * SUM(is_correct) / COUNT(*),
                    1
                ) AS percentage
            FROM quiz_answers
            WHERE topic IS NOT NULL
              AND TRIM(topic) != ''
            GROUP BY topic
            ORDER BY percentage ASC
            """
        ).fetchall()

        document_rows = connection.execute(
            """
            SELECT
                d.id,
                d.filename,
                COUNT(DISTINCT qa.id) AS quiz_attempts,
                COALESCE(AVG(qa.percentage), 0) AS average_score
            FROM documents d
            LEFT JOIN quiz_attempts qa
                ON qa.document_id = d.id
            GROUP BY d.id, d.filename
            ORDER BY quiz_attempts DESC
            """
        ).fetchall()

        daily_rows = connection.execute(
            """
            SELECT
                DATE(created_at) AS date,
                COUNT(*) AS attempts,
                ROUND(AVG(percentage), 1) AS average_score
            FROM quiz_attempts
            GROUP BY DATE(created_at)
            ORDER BY date ASC
            LIMIT 30
            """
        ).fetchall()

        student_activity = connection.execute(
            """
            SELECT
                u.id,
                u.name,
                COUNT(qa.id) AS quiz_attempts,
                COALESCE(AVG(qa.percentage), 0) AS average_score
            FROM users u
            LEFT JOIN quiz_attempts qa
                ON qa.user_id = u.id
            WHERE u.role = 'student'
            GROUP BY u.id, u.name
            ORDER BY quiz_attempts DESC
            """
        ).fetchall()

        return {
            "status": "success",

            "topics": [
                {
                    "topic": row["topic"],
                    "questions_answered": row["questions_answered"],
                    "correct_answers": row["correct_answers"],
                    "percentage": float(row["percentage"] or 0)
                }
                for row in topic_rows
            ],

            "documents": [
                {
                    "id": row["id"],
                    "filename": row["filename"],
                    "quiz_attempts": row["quiz_attempts"],
                    "average_score": round(
                        float(row["average_score"] or 0),
                        1
                    )
                }
                for row in document_rows
            ],

            "daily_activity": [
                {
                    "date": row["date"],
                    "attempts": row["attempts"],
                    "average_score": float(row["average_score"] or 0)
                }
                for row in daily_rows
            ],

            "student_activity": [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "quiz_attempts": row["quiz_attempts"],
                    "average_score": round(
                        float(row["average_score"] or 0),
                        1
                    )
                }
                for row in student_activity
            ]
        }

    finally:
        connection.close()
