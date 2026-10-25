import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, hash_password
from app.database.database import get_connection


router = APIRouter(
    prefix="/api/teacher/exams",
    tags=["Teacher Exams"],
)


def require_teacher(request: Request):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Teacher access required."
        )

    return user


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(
        default=None,
        max_length=1000
    )
    duration_minutes: int = Field(default=60, ge=1, le=600)
    deadline_at: Optional[datetime] = None
    exam_password: Optional[str] = Field(default=None, max_length=128)


class ExamQuestionCreate(BaseModel):
    question: str = Field(..., min_length=1)
    question_type: str = "multiple_choice"
    options: list[str] = Field(default_factory=list, max_length=6)
    correct_answer: Optional[int] = Field(default=None, ge=0, le=5)
    correct_answer_text: Optional[str] = None
    explanation: Optional[str] = None
class ExamAssign(BaseModel):
    student_ids: list[int] = Field(..., min_length=1)


@router.get("/notifications")
def list_teacher_notifications(request: Request):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                id,
                type,
                title,
                message,
                reference_type,
                reference_id,
                is_read,
                created_at
            FROM notifications
            WHERE user_id = ?
              AND type = 'exam_submitted'
              AND is_read = 0
            ORDER BY created_at DESC, id DESC
            """,
            (teacher["id"],)
        ).fetchall()

        unread_row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM notifications
            WHERE user_id = ?
              AND type = 'exam_submitted'
              AND is_read = 0
            """,
            (teacher["id"],)
        ).fetchone()

        return {
            "status": "success",
            "notifications": [dict(row) for row in rows],
            "count": len(rows),
            "unread_count": unread_row["count"]
        }

    finally:
        connection.close()



@router.post("/notifications/read-all")
def mark_all_teacher_notifications_read(request: Request):
    teacher = require_teacher(request)
    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE user_id = ?
              AND type = 'exam_submitted'
              AND is_read = 0
            """,
            (teacher["id"],)
        )
        connection.commit()
        return {"status": "success"}
    finally:
        connection.close()


@router.post("/notifications/{notification_id}/read")
def mark_teacher_notification_read(
    notification_id: int,
    request: Request
):
    teacher = require_teacher(request)
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
              AND user_id = ?
              AND type = 'exam_submitted'
            """,
            (notification_id, teacher["id"])
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Notification not found."
            )

        connection.commit()
        return {"status": "success"}

    finally:
        connection.close()


@router.get("/submissions/{attempt_id}")
def get_submission(
    attempt_id: int,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        submission = connection.execute(
            """
            SELECT
                a.id,
                a.test_id,
                a.student_id,
                a.score,
                a.total_questions,
                a.percentage,
                a.submitted_at,
                COALESCE(a.score_released, 0) AS score_released,
                t.title AS exam_title,
                t.description AS exam_description,
                u.name AS student_name,
                u.email AS student_email
            FROM teacher_test_attempts a
            INNER JOIN teacher_tests t
                ON t.id = a.test_id
            INNER JOIN users u
                ON u.id = a.student_id
            WHERE a.id = ?
              AND t.creator_id = ?
            """,
            (attempt_id, teacher["id"])
        ).fetchone()

        if not submission:
            raise HTTPException(
                status_code=404,
                detail="Submission not found."
            )

        questions = connection.execute(
            """
            SELECT
                q.id,
                q.question_index,
                q.question,
                q.question_type,
                q.options,
                q.correct_answer,
                q.correct_answer_text,
                a.selected_answer,
                a.selected_answer_text,
                a.correct_answer_text AS submitted_correct_answer_text,
                a.is_correct
            FROM teacher_test_questions q
            LEFT JOIN teacher_test_answers a
                ON a.question_id = q.id
               AND a.attempt_id = ?
            WHERE q.test_id = ?
            ORDER BY q.question_index ASC
            """,
            (
                attempt_id,
                submission["test_id"]
            )
        ).fetchall()

        question_results = []

        for row in questions:
            try:
                options = json.loads(row["options"])
            except (TypeError, json.JSONDecodeError):
                options = []

            question_results.append({
                "id": row["id"],
                "question_index": row["question_index"],
                "question": row["question"],
                "question_type": row["question_type"],
                "options": options,
                "correct_answer": row["correct_answer"],
                "correct_answer_text": row["correct_answer_text"],
                "selected_answer": row["selected_answer"],
                "selected_answer_text": row["selected_answer_text"],
                "submitted_correct_answer_text": row["submitted_correct_answer_text"],
                "is_correct": bool(row["is_correct"])
                    if row["is_correct"] is not None
                    else False
            })

        return {
            "status": "success",
            "submission": {
                "attempt_id": submission["id"],
                "exam_id": submission["test_id"],
                "exam_title": submission["exam_title"],
                "exam_description": submission["exam_description"],
                "student_id": submission["student_id"],
                "student_name": submission["student_name"],
                "student_email": submission["student_email"],
                "score": submission["score"],
                "total_questions": submission["total_questions"],
                "percentage": submission["percentage"],
                "submitted_at": submission["submitted_at"],
                "score_released": bool(submission["score_released"]),
                "questions": question_results
            }
        }

    finally:
        connection.close()


@router.get("/{exam_id}/submissions")
def list_submissions(
    exam_id: str,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        exam = connection.execute(
            """
            SELECT id, title
            FROM teacher_tests
            WHERE id = ?
              AND creator_id = ?
            """,
            (exam_id, teacher["id"])
        ).fetchone()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        rows = connection.execute(
            """
            SELECT
                a.id AS attempt_id,
                a.test_id,
                a.student_id,
                a.score,
                a.total_questions,
                a.percentage,
                a.submitted_at,
                COALESCE(a.score_released, 0) AS score_released,
                u.name AS student_name,
                u.email AS student_email
            FROM teacher_test_attempts a
            INNER JOIN users u
                ON u.id = a.student_id
            WHERE a.test_id = ?
            ORDER BY a.submitted_at DESC
            """,
            (exam_id,)
        ).fetchall()

        submissions = [
            {
                "attempt_id": row["attempt_id"],
                "exam_id": row["test_id"],
                "student_id": row["student_id"],
                "student_name": row["student_name"],
                "student_email": row["student_email"],
                "score": row["score"],
                "total_questions": row["total_questions"],
                "percentage": row["percentage"],
                "submitted_at": row["submitted_at"],
                "score_released": bool(row["score_released"])
            }
            for row in rows
        ]

        return {
            "status": "success",
            "exam": {
                "id": exam["id"],
                "title": exam["title"]
            },
            "submissions": submissions
        }

    finally:
        connection.close()


@router.post("/submissions/{attempt_id}/release")
def release_score(
    attempt_id: int,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        submission = connection.execute(
            """
            SELECT
                a.id,
                a.test_id,
                a.student_id,
                a.score_released,
                t.title AS exam_title
            FROM teacher_test_attempts a
            INNER JOIN teacher_tests t
                ON t.id = a.test_id
            WHERE a.id = ?
              AND t.creator_id = ?
            """,
            (attempt_id, teacher["id"])
        ).fetchone()

        if not submission:
            raise HTTPException(
                status_code=404,
                detail="Submission not found."
            )

        if submission["score_released"]:
            return {
                "status": "success",
                "message": "Score has already been released.",
                "already_released": True
            }

        connection.execute(
            """
            UPDATE teacher_test_attempts
            SET score_released = 1
            WHERE id = ?
            """,
            (attempt_id,)
        )

        existing_notification = connection.execute(
            """
            SELECT id
            FROM notifications
            WHERE user_id = ?
              AND type = 'exam_result_released'
              AND reference_type = 'teacher_test'
              AND reference_id = ?
            LIMIT 1
            """,
            (
                submission["student_id"],
                submission["test_id"]
            )
        ).fetchone()

        if not existing_notification:
            connection.execute(
                """
                INSERT OR IGNORE INTO notifications (
                    user_id,
                    type,
                    title,
                    message,
                    reference_type,
                    reference_id,
                    is_read
                )
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    submission["student_id"],
                    "exam_result_released",
                    "Exam Result Released",
                    (
                        f'Your result for '
                        f'"{submission["exam_title"]}" '
                        f'is now available.'
                    ),
                    "teacher_test",
                    submission["test_id"]
                )
            )

        connection.commit()

        return {
            "status": "success",
            "message": "Score released successfully.",
            "already_released": False,
            "student_notified": True
        }

    finally:
        connection.close()


@router.post("")
def create_exam(
    payload: ExamCreate,
    request: Request
):
    teacher = require_teacher(request)

    exam_password = (
        payload.exam_password.strip()
        if payload.exam_password and payload.exam_password.strip()
        else None
    )
    if exam_password and len(exam_password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Exam password must contain at least 4 characters."
        )

    password_hash = hash_password(exam_password) if exam_password else None
    exam_id = str(uuid.uuid4())

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO teacher_tests (
                id,
                creator_id,
                title,
                description,
                status,
                duration_minutes,
                deadline_at,
                password_hash
            )
            VALUES (?, ?, ?, ?, 'draft', ?, ?, ?)
            """,
            (
                exam_id,
                teacher["id"],
                payload.title.strip(),
                payload.description.strip()
                if payload.description
                else None,
                payload.duration_minutes,
                (
                    payload.deadline_at.astimezone().isoformat()
                    if payload.deadline_at
                    else None
                ),
                password_hash
            )
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Exam created successfully.",
            "exam": {
                "id": exam_id,
                "title": payload.title.strip(),
                "description": (
                    payload.description.strip()
                    if payload.description
                    else None
                ),
                "status": "draft",
                "duration_minutes": payload.duration_minutes,
                "password_protected": bool(password_hash),
                "deadline_at": (
                    payload.deadline_at.astimezone().isoformat()
                    if payload.deadline_at
                    else None
                )
            }
        }

    finally:
        connection.close()


@router.get("")
def list_exams(request: Request):
    teacher = require_teacher(request)

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
            "exams": [
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



@router.get("/{exam_id}")
def get_exam(
    exam_id: str,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        exam = connection.execute(
            """
            SELECT
                id,
                title,
                description,
                status,
                created_at,
                published_at,
                duration_minutes,
                deadline_at
            FROM teacher_tests
            WHERE id = ?
              AND creator_id = ?
            """,
            (exam_id, teacher["id"])
        ).fetchone()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        questions = connection.execute(
            """
            SELECT
                id,
                question_index,
                question,
                question_type,
                options,
                correct_answer,
                correct_answer_text,
                explanation
            FROM teacher_test_questions
            WHERE test_id = ?
            ORDER BY question_index ASC
            """,
            (exam_id,)
        ).fetchall()

        assigned_rows = connection.execute(
            """
            SELECT student_id
            FROM teacher_test_assignments
            WHERE test_id = ?
            ORDER BY student_id
            """,
            (exam_id,)
        ).fetchall()

        return {
            "status": "success",
            "exam": {
                "id": exam["id"],
                "title": exam["title"],
                "description": exam["description"],
                "status": exam["status"],
                "created_at": exam["created_at"],
                "published_at": exam["published_at"],
                "duration_minutes": exam["duration_minutes"],
                "deadline_at": exam["deadline_at"],
                "assigned_student_ids": [
                    row["student_id"] for row in assigned_rows
                ],
                "questions": [
                    {
                        "id": row["id"],
                        "question_index": row["question_index"],
                        "question": row["question"],
                        "question_type": row["question_type"],
                        "options": json.loads(row["options"]),
                        "correct_answer": row["correct_answer"],
                        "correct_answer_text": row["correct_answer_text"],
                        "explanation": row["explanation"]
                    }
                    for row in questions
                ]
            }
        }

    finally:
        connection.close()


@router.post("/{exam_id}/questions")
def add_question(exam_id: str, payload: ExamQuestionCreate, request: Request):
    teacher = require_teacher(request)

    question = payload.question.strip()
    question_type = payload.question_type.strip().lower()
    options = [str(option).strip() for option in payload.options]
    correct_answer = payload.correct_answer
    correct_answer_text = None

    if not question:
        raise HTTPException(status_code=400, detail="Question text is required.")

    if question_type == "multiple_choice":
        if not 2 <= len(options) <= 6 or any(not item for item in options):
            raise HTTPException(
                status_code=400,
                detail="Multiple-choice questions need 2 to 6 non-empty options."
            )
        if correct_answer is None or not 0 <= correct_answer < len(options):
            raise HTTPException(
                status_code=400,
                detail="Choose a correct answer from the provided options."
            )
    elif question_type == "true_false":
        options = ["False", "True"]
        if correct_answer not in (0, 1):
            raise HTTPException(
                status_code=400,
                detail="Choose either False or True as the correct answer."
            )
    elif question_type == "fill_blank":
        options = []
        correct_answer = 0
        correct_answer_text = (payload.correct_answer_text or "").strip()
        if not correct_answer_text:
            raise HTTPException(
                status_code=400,
                detail="The correct text answer is required."
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported question type."
        )

    connection = get_connection()
    try:
        exam = connection.execute(
            "SELECT id, status FROM teacher_tests WHERE id = ? AND creator_id = ?",
            (exam_id, teacher["id"]),
        ).fetchone()

        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found.")

        if exam["status"] != "draft":
            raise HTTPException(
                status_code=400,
                detail="Questions can only be added to draft exams."
            )

        next_index = connection.execute(
            "SELECT COALESCE(MAX(question_index), -1) + 1 "
            "FROM teacher_test_questions WHERE test_id = ?",
            (exam_id,),
        ).fetchone()[0]

        cursor = connection.execute(
            """
            INSERT INTO teacher_test_questions
                (test_id, question_index, question, options, correct_answer,
                 explanation, question_type, correct_answer_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam_id,
                next_index,
                question,
                json.dumps(options),
                correct_answer,
                payload.explanation.strip() if payload.explanation else None,
                question_type,
                correct_answer_text,
            ),
        )
        connection.commit()

        return {
            "success": True,
            "message": "Question added successfully.",
            "question_id": cursor.lastrowid,
            "question_index": next_index,
            "question_type": question_type,
        }
    finally:
        connection.close()

@router.delete("/{exam_id}/questions/{question_id}")
def delete_question(
    exam_id: str,
    question_id: int,
    request: Request,
):
    teacher = require_teacher(request)
    connection = get_connection()

    try:
        exam = connection.execute(
            """
            SELECT id, status
            FROM teacher_tests
            WHERE id = ? AND creator_id = ?
            """,
            (exam_id, teacher["id"]),
        ).fetchone()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail="Exam not found.",
            )

        if exam["status"] != "draft":
            raise HTTPException(
                status_code=400,
                detail="Questions can only be deleted from draft exams.",
            )

        question = connection.execute(
            """
            SELECT id
            FROM teacher_test_questions
            WHERE id = ? AND test_id = ?
            """,
            (question_id, exam_id),
        ).fetchone()

        if not question:
            raise HTTPException(
                status_code=404,
                detail="Question not found in this exam.",
            )

        connection.execute(
            """
            DELETE FROM teacher_test_questions
            WHERE id = ? AND test_id = ?
            """,
            (question_id, exam_id),
        )

        # Keep question numbering consecutive after deletion.
        remaining = connection.execute(
            """
            SELECT id
            FROM teacher_test_questions
            WHERE test_id = ?
            ORDER BY question_index ASC, id ASC
            """,
            (exam_id,),
        ).fetchall()

        for index, row in enumerate(remaining):
            connection.execute(
                """
                UPDATE teacher_test_questions
                SET question_index = ?
                WHERE id = ?
                """,
                (index, row["id"]),
            )

        connection.commit()

        return {
            "success": True,
            "message": "Question deleted successfully.",
            "remaining_questions": len(remaining),
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.delete("/{exam_id}")
def delete_exam(exam_id: str, request: Request):
    """
    Permanently delete an exam owned by the authenticated teacher
    and its dependent exam records.
    """
    teacher = require_teacher(request)
    connection = get_connection()

    try:
        exam = connection.execute(
            """
            SELECT id, title
            FROM teacher_tests
            WHERE id = ? AND creator_id = ?
            """,
            (exam_id, teacher["id"]),
        ).fetchone()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail="Exam not found.",
            )

        # Explicitly delete dependent records in one transaction.
        # This also works when SQLite foreign-key enforcement is off.
        connection.execute("BEGIN")

        dependent_deletes = [
            (
                "teacher_test_answers",
                """
                DELETE FROM teacher_test_answers
                WHERE attempt_id IN (
                    SELECT id FROM teacher_test_attempts
                    WHERE test_id = ?
                )
                OR question_id IN (
                    SELECT id FROM teacher_test_questions
                    WHERE test_id = ?
                )
                """,
                (exam_id, exam_id),
            ),
            (
                "teacher_exam_monitoring_events",
                "DELETE FROM teacher_exam_monitoring_events WHERE exam_id = ?",
                (exam_id,),
            ),
            (
                "teacher_test_password_attempts",
                "DELETE FROM teacher_test_password_attempts WHERE test_id = ?",
                (exam_id,),
            ),
            (
                "teacher_test_password_unlocks",
                "DELETE FROM teacher_test_password_unlocks WHERE test_id = ?",
                (exam_id,),
            ),
            (
                "teacher_test_sessions",
                "DELETE FROM teacher_test_sessions WHERE test_id = ?",
                (exam_id,),
            ),
            (
                "teacher_test_assignments",
                "DELETE FROM teacher_test_assignments WHERE test_id = ?",
                (exam_id,),
            ),
            (
                "teacher_test_attempts",
                "DELETE FROM teacher_test_attempts WHERE test_id = ?",
                (exam_id,),
            ),
            (
                "teacher_test_questions",
                "DELETE FROM teacher_test_questions WHERE test_id = ?",
                (exam_id,),
            ),
        ]

        existing_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

        for table, sql, parameters in dependent_deletes:
            if table in existing_tables:
                connection.execute(sql, parameters)

        # Remove notifications linked to this exam before deleting it.
        connection.execute(
            """
            DELETE FROM notifications
            WHERE reference_type = 'teacher_test'
              AND reference_id = ?
            """,
            (exam_id,),
        )

        connection.execute(
            "DELETE FROM teacher_tests WHERE id = ? AND creator_id = ?",
            (exam_id, teacher["id"]),
        )

        if connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise HTTPException(
                status_code=409,
                detail="Exam could not be deleted. Please refresh and try again.",
            )

        connection.commit()

        return {
            "success": True,
            "message": "Exam and related records deleted successfully.",
            "exam_id": exam_id,
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/{exam_id}/publish")
def publish_exam(
    exam_id: str,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        exam = connection.execute(
            """
            SELECT id, title, status, deadline_at
            FROM teacher_tests
            WHERE id = ?
              AND creator_id = ?
            """,
            (exam_id, teacher["id"])
        ).fetchone()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        if exam["status"] != "draft":
            raise HTTPException(
                status_code=400,
                detail="Only draft exams can be published."
            )

        if exam["deadline_at"]:
            try:
                deadline = datetime.fromisoformat(exam["deadline_at"])
                if deadline.tzinfo is None:
                    deadline = deadline.astimezone()
                now = datetime.now().astimezone()
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail="The exam deadline is invalid."
                )

            if deadline <= now:
                raise HTTPException(
                    status_code=400,
                    detail="The exam deadline must be in the future."
                )

        type_counts = {
            row["question_type"]: row["count"]
            for row in connection.execute(
                """
                SELECT COALESCE(question_type, 'multiple_choice') AS question_type,
                       COUNT(*) AS count
                FROM teacher_test_questions
                WHERE test_id = ?
                GROUP BY COALESCE(question_type, 'multiple_choice')
                """,
                (exam_id,)
            ).fetchall()
        }

        required_types = {
            "multiple_choice": "multiple-choice",
            "true_false": "true/false",
            "fill_blank": "fill-in-the-blank",
        }
        missing_types = [
            label for key, label in required_types.items()
            if type_counts.get(key, 0) < 1
        ]

        if missing_types:
            raise HTTPException(
                status_code=400,
                detail="Add at least one question of each type before publishing. Missing: "
                       + ", ".join(missing_types) + "."
            )

        # Publish the exam and assign it to every current student
        # in the same database transaction.
        connection.execute(
            """
            UPDATE teacher_tests
            SET
                status = 'published',
                published_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND creator_id = ?
              AND status = 'draft'
            """,
            (exam_id, teacher["id"])
        )

        students = connection.execute(
            """
            SELECT id
            FROM users
            WHERE role = 'student'
            ORDER BY id
            """
        ).fetchall()

        assigned_count = 0

        for student in students:
            student_id = student["id"]

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO teacher_test_assignments (
                    test_id,
                    student_id
                )
                VALUES (?, ?)
                """,
                (exam_id, student_id)
            )

            # Notify only when a new assignment was created.
            if cursor.rowcount > 0:
                assigned_count += 1

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
                        f'You have been assigned a new exam: "{exam["title"]}".',
                        "teacher_test",
                        exam_id
                    )
                )

        connection.commit()

        return {
            "status": "success",
            "message": (
                "Exam published and automatically assigned to all students."
            ),
            "assigned_students": assigned_count,
            "total_students": len(students)
        }

    finally:
        connection.close()


@router.post("/{exam_id}/assign")
def assign_exam(
    exam_id: str,
    payload: ExamAssign,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        exam = connection.execute(
            """
            SELECT id, title, status
            FROM teacher_tests
            WHERE id = ?
              AND creator_id = ?
            """,
            (exam_id, teacher["id"])
        ).fetchone()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        if exam["status"] != "published":
            raise HTTPException(
                status_code=400,
                detail="Only published exams can be assigned."
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
                (exam_id, student_id)
            )

            if cursor.rowcount > 0:
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
                        f'You have been assigned a new exam: "{exam["title"]}".',
                        "teacher_test",
                        exam_id
                    )
                )

        connection.commit()

        return {
            "status": "success",
            "message": "Exam assigned successfully.",
            "assigned_students": unique_student_ids
        }

    finally:
        connection.close()
