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


# ============================================================
# TEACHER TESTS
# Separate teacher-created tests from student AI quizzes.
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional
import json
import uuid


class TeacherTestCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class TeacherQuestionCreate(BaseModel):
    question: str = Field(..., min_length=1)
    options: list[str] = Field(..., min_length=2, max_length=6)
    correct_answer: int = Field(..., ge=0, le=5)
    explanation: Optional[str] = None


class TeacherTestAssign(BaseModel):
    student_ids: list[int] = Field(..., min_length=1)


@router.get("/teacher-tests")
def get_teacher_tests(request: Request):
    teacher = require_admin(request)

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                t.id,
                t.title,
                t.description,
                t.status,
                t.created_at,
                t.published_at,
                COUNT(DISTINCT q.id) AS question_count,
                COUNT(DISTINCT a.student_id) AS assigned_students
            FROM teacher_tests t
            LEFT JOIN teacher_test_questions q
                ON q.test_id = t.id
            LEFT JOIN teacher_test_assignments a
                ON a.test_id = t.id
            WHERE t.creator_id = ?
            GROUP BY
                t.id,
                t.title,
                t.description,
                t.status,
                t.created_at,
                t.published_at
            ORDER BY t.created_at DESC
            """,
            (teacher["id"],)
        ).fetchall()

        return {
            "status": "success",
            "tests": [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "published_at": row["published_at"],
                    "question_count": row["question_count"],
                    "assigned_students": row["assigned_students"]
                }
                for row in rows
            ]
        }

    finally:
        connection.close()


@router.post("/teacher-tests")
def create_teacher_test(
    payload: TeacherTestCreate,
    request: Request
):
    teacher = require_admin(request)

    test_id = str(uuid.uuid4())

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO teacher_tests (
                id,
                creator_id,
                title,
                description,
                status
            )
            VALUES (?, ?, ?, ?, 'draft')
            """,
            (
                test_id,
                teacher["id"],
                payload.title.strip(),
                payload.description.strip()
                if payload.description
                else None
            )
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Teacher test created successfully.",
            "test": {
                "id": test_id,
                "title": payload.title.strip(),
                "description": (
                    payload.description.strip()
                    if payload.description
                    else None
                ),
                "status": "draft"
            }
        }

    finally:
        connection.close()


@router.get("/teacher-tests/{test_id}")
def get_teacher_test(
    test_id: str,
    request: Request
):
    teacher = require_admin(request)

    connection = get_connection()

    try:
        test = connection.execute(
            """
            SELECT
                id,
                title,
                description,
                status,
                created_at,
                published_at
            FROM teacher_tests
            WHERE id = ?
              AND creator_id = ?
            """,
            (test_id, teacher["id"])
        ).fetchone()

        if not test:
            raise HTTPException(
                status_code=404,
                detail="Teacher test not found."
            )

        questions = connection.execute(
            """
            SELECT
                id,
                question_index,
                question,
                options,
                correct_answer,
                explanation
            FROM teacher_test_questions
            WHERE test_id = ?
            ORDER BY question_index ASC
            """,
            (test_id,)
        ).fetchall()

        assignments = connection.execute(
            """
            SELECT
                a.student_id,
                u.name,
                u.email,
                a.assigned_at
            FROM teacher_test_assignments a
            JOIN users u
                ON u.id = a.student_id
            WHERE a.test_id = ?
            ORDER BY u.name ASC
            """,
            (test_id,)
        ).fetchall()

        return {
            "status": "success",
            "test": {
                "id": test["id"],
                "title": test["title"],
                "description": test["description"],
                "status": test["status"],
                "created_at": test["created_at"],
                "published_at": test["published_at"],
                "questions": [
                    {
                        "id": row["id"],
                        "question_index": row["question_index"],
                        "question": row["question"],
                        "options": json.loads(row["options"]),
                        "correct_answer": row["correct_answer"],
                        "explanation": row["explanation"]
                    }
                    for row in questions
                ],
                "assignments": [
                    {
                        "student_id": row["student_id"],
                        "name": row["name"],
                        "email": row["email"],
                        "assigned_at": row["assigned_at"]
                    }
                    for row in assignments
                ]
            }
        }

    finally:
        connection.close()


@router.post("/teacher-tests/{test_id}/questions")
def add_teacher_question(
    test_id: str,
    payload: TeacherQuestionCreate,
    request: Request
):
    teacher = require_admin(request)

    if payload.correct_answer >= len(payload.options):
        raise HTTPException(
            status_code=400,
            detail="Correct answer must match one of the provided options."
        )

    connection = get_connection()

    try:
        test = connection.execute(
            """
            SELECT id, status
            FROM teacher_tests
            WHERE id = ?
              AND creator_id = ?
            """,
            (test_id, teacher["id"])
        ).fetchone()

        if not test:
            raise HTTPException(
                status_code=404,
                detail="Teacher test not found."
            )

        if test["status"] != "draft":
            raise HTTPException(
                status_code=400,
                detail="Questions can only be added to a draft test."
            )

        next_index = connection.execute(
            """
            SELECT COALESCE(MAX(question_index), -1) + 1 AS next_index
            FROM teacher_test_questions
            WHERE test_id = ?
            """,
            (test_id,)
        ).fetchone()["next_index"]

        cursor = connection.execute(
            """
            INSERT INTO teacher_test_questions (
                test_id,
                question_index,
                question,
                options,
                correct_answer,
                explanation
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                test_id,
                next_index,
                payload.question.strip(),
                json.dumps(payload.options),
                payload.correct_answer,
                payload.explanation.strip()
                if payload.explanation
                else None
            )
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Question added successfully.",
            "question": {
                "id": cursor.lastrowid,
                "question_index": next_index
            }
        }

    finally:
        connection.close()


@router.post("/teacher-tests/{test_id}/publish")
def publish_teacher_test(
    test_id: str,
    request: Request
):
    teacher = require_admin(request)

    connection = get_connection()

    try:
        test = connection.execute(
            """
            SELECT id, status
            FROM teacher_tests
            WHERE id = ?
              AND creator_id = ?
            """,
            (test_id, teacher["id"])
        ).fetchone()

        if not test:
            raise HTTPException(
                status_code=404,
                detail="Teacher test not found."
            )

        question_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM teacher_test_questions
            WHERE test_id = ?
            """,
            (test_id,)
        ).fetchone()["count"]

        if question_count == 0:
            raise HTTPException(
                status_code=400,
                detail="A test must contain at least one question before publishing."
            )

        if test["status"] == "published":
            return {
                "status": "success",
                "message": "Test is already published."
            }

        connection.execute(
            """
            UPDATE teacher_tests
            SET
                status = 'published',
                published_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND creator_id = ?
            """,
            (test_id, teacher["id"])
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Teacher test published successfully."
        }

    finally:
        connection.close()


@router.post("/teacher-tests/{test_id}/assign")
def assign_teacher_test(
    test_id: str,
    payload: TeacherTestAssign,
    request: Request
):
    teacher = require_admin(request)

    connection = get_connection()

    try:
        test = connection.execute(
            """
            SELECT id, status
            FROM teacher_tests
            WHERE id = ?
              AND creator_id = ?
            """,
            (test_id, teacher["id"])
        ).fetchone()

        if not test:
            raise HTTPException(
                status_code=404,
                detail="Teacher test not found."
            )

        if test["status"] != "published":
            raise HTTPException(
                status_code=400,
                detail="Only published tests can be assigned."
            )

        unique_student_ids = list(dict.fromkeys(payload.student_ids))

        for student_id in unique_student_ids:
            student = connection.execute(
                """
                SELECT id
                FROM users
                WHERE id = ?
                  AND role = 'student'
                """,
                (student_id,)
            ).fetchone()

            if not student:
                raise HTTPException(
                    status_code=400,
                    detail=f"Student {student_id} was not found."
                )

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO teacher_test_assignments (
                    test_id,
                    student_id
                )
                VALUES (?, ?)
                """,
                (test_id, student_id)
            )

            if cursor.rowcount > 0:
                test_title = connection.execute(
                    """
                    SELECT title
                    FROM teacher_tests
                    WHERE id = ?
                    """,
                    (test_id,)
                ).fetchone()["title"]

                connection.execute(
                    """
                    INSERT INTO notifications (
                        user_id,
                        type,
                        title,
                        message,
                        reference_type,
                        reference_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        "exam_assigned",
                        "New Exam",
                        f'You have been assigned a new exam: "{test_title}".',
                        "teacher_test",
                        test_id
                    )
                )

        connection.commit()

        assigned_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM teacher_test_assignments
            WHERE test_id = ?
            """,
            (test_id,)
        ).fetchone()["count"]

        return {
            "status": "success",
            "message": "Test assigned successfully.",
            "assigned_students": assigned_count
        }

    finally:
        connection.close()
