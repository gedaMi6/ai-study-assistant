import json
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, verify_password
from app.database.database import get_connection


router = APIRouter(
    prefix="/api/student/exams",
    tags=["Student Exams"],
)


def require_student(request: Request):
    user = get_current_user(request)

    if not user or user["role"] != "student":
        raise HTTPException(
            status_code=401,
            detail="Student authentication required."
        )

    return user


class ExamSubmit(BaseModel):
    answers: dict[str, object] = Field(default_factory=dict)
    auto_submit: bool = False


class ExamAutosave(BaseModel):
    answers: dict[str, object] = Field(default_factory=dict)


class ExamUnlockRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)


def _is_exam_unlocked(connection, exam, student_id):
    if not exam["password_hash"]:
        return True
    return connection.execute(
        """SELECT 1 FROM teacher_test_password_unlocks
           WHERE test_id = ? AND student_id = ?""",
        (exam["id"], student_id),
    ).fetchone() is not None


def _require_exam_unlocked(connection, exam, student_id):
    if exam["password_hash"] and not _is_exam_unlocked(
        connection, exam, student_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Enter the exam password before accessing this exam."
        )


def _parse_exam_time(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone()


def _now_exam_time():
    return datetime.now().astimezone()


def _ensure_exam_session(connection, exam, student_id):
    session = connection.execute(
        """SELECT started_at, expires_at, answers_json, submitted_at
           FROM teacher_test_sessions
           WHERE test_id = ? AND student_id = ?""",
        (exam["id"], student_id),
    ).fetchone()
    if session:
        return session

    now = _now_exam_time()
    duration = max(1, int(exam["duration_minutes"] or 60))
    expiry = now + timedelta(minutes=duration)
    deadline = _parse_exam_time(exam["deadline_at"])
    if deadline and deadline < expiry:
        expiry = deadline

    started_at = now.isoformat()
    expires_at = expiry.isoformat()
    connection.execute(
        """INSERT INTO teacher_test_sessions
           (test_id, student_id, started_at, expires_at, answers_json)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(test_id, student_id) DO NOTHING""",
        (exam["id"], student_id, started_at, expires_at, "{}"),
    )
    connection.commit()
    return connection.execute(
        """SELECT started_at, expires_at, answers_json, submitted_at
           FROM teacher_test_sessions
           WHERE test_id = ? AND student_id = ?""",
        (exam["id"], student_id),
    ).fetchone()


@router.get("")
def list_exams(request: Request):
    student = require_student(request)

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                t.id,
                t.title,
                t.description,
                t.published_at,
                a.assigned_at,
                ta.score,
                ta.total_questions,
                ta.percentage,
                ta.submitted_at,
                COALESCE(ta.score_released, 0) AS score_released
            FROM teacher_tests t
            INNER JOIN teacher_test_assignments a
                ON a.test_id = t.id
            LEFT JOIN teacher_test_attempts ta
                ON ta.test_id = t.id
               AND ta.student_id = ?
            WHERE a.student_id = ?
              AND t.status = 'published'
            ORDER BY
                CASE
                    WHEN ta.id IS NULL THEN 0
                    ELSE 1
                END,
                t.published_at DESC
            """,
            (student["id"], student["id"])
        ).fetchall()

        return {
            "status": "success",
            "exams": [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "published_at": row["published_at"],
                    "assigned_at": row["assigned_at"],
                    "completed": row["score"] is not None,
                    "score_released": bool(row["score_released"]),
                    "score": (
                        row["score"]
                        if row["score_released"]
                        else None
                    ),
                    "total_questions": (
                        row["total_questions"]
                        if row["score_released"]
                        else None
                    ),
                    "percentage": (
                        row["percentage"]
                        if row["score_released"]
                        else None
                    ),
                    "submitted_at": row["submitted_at"],
                }
                for row in rows
            ]
        }

    finally:
        connection.close()


@router.get("/{exam_id}")
def get_exam(exam_id: str, request: Request):
    student = require_student(request)

    connection = get_connection()

    try:
        exam = connection.execute(
            """
            SELECT
                t.id,
                t.title,
                t.description,
                t.published_at,
                t.duration_minutes,
                t.deadline_at,
                t.password_hash
            FROM teacher_tests t
            INNER JOIN teacher_test_assignments a
                ON a.test_id = t.id
            WHERE t.id = ?
              AND a.student_id = ?
              AND t.status = 'published'
            """,
            (exam_id, student["id"])
        ).fetchone()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        attempt = connection.execute(
            """
            SELECT
                score,
                total_questions,
                percentage,
                submitted_at,
                COALESCE(score_released, 0) AS score_released
            FROM teacher_test_attempts
            WHERE test_id = ?
              AND student_id = ?
            """,
            (exam_id, student["id"])
        ).fetchone()

        # Do not expose questions or start a timer before the password is verified.
        if attempt is None and exam["password_hash"] and not _is_exam_unlocked(
            connection, exam, student["id"]
        ):
            return {
                "status": "success",
                "exam": {
                    "id": exam["id"],
                    "title": exam["title"],
                    "description": exam["description"],
                    "password_required": True,
                    "unlocked": False,
                    "completed": False,
                    "questions": []
                }
            }

        questions = connection.execute(
            """
            SELECT
                id,
                question_index,
                question,
                question_type,
                options
            FROM teacher_test_questions
            WHERE test_id = ?
            ORDER BY question_index ASC
            """,
            (exam_id,)
        ).fetchall()

        session = None
        if attempt is None:
            session = _ensure_exam_session(connection, exam, student["id"])

        saved_answers = {}
        if session:
            try:
                saved_answers = json.loads(session["answers_json"] or "{}")
                if not isinstance(saved_answers, dict):
                    saved_answers = {}
            except (TypeError, ValueError):
                saved_answers = {}

        return {
            "status": "success",
            "exam": {
                "id": exam["id"],
                "title": exam["title"],
                "description": exam["description"],
                "published_at": exam["published_at"],
                "duration_minutes": exam["duration_minutes"],
                "deadline_at": exam["deadline_at"],
                "password_required": bool(exam["password_hash"]),
                "unlocked": True,
                "session_started_at": session["started_at"] if session else None,
                "expires_at": session["expires_at"] if session else None,
                "saved_answers": saved_answers,
                "completed": attempt is not None,
                "score_released": (
                    bool(attempt["score_released"])
                    if attempt
                    else False
                ),
                "score": (
                    attempt["score"]
                    if attempt and attempt["score_released"]
                    else None
                ),
                "total_questions": (
                    attempt["total_questions"]
                    if attempt and attempt["score_released"]
                    else len(questions)
                ),
                "percentage": (
                    attempt["percentage"]
                    if attempt and attempt["score_released"]
                    else None
                ),
                "submitted_at": (
                    attempt["submitted_at"]
                    if attempt
                    else None
                ),
                "questions": [
                    {
                        "id": row["id"],
                        "question_index": row["question_index"],
                        "question": row["question"],
                        "question_type": row["question_type"],
                        "options": json.loads(row["options"]),
                    }
                    for row in questions
                ]
            }
        }

    finally:
        connection.close()


@router.post("/{exam_id}/unlock")
def unlock_exam(
    exam_id: str,
    payload: ExamUnlockRequest,
    request: Request
):
    student = require_student(request)
    connection = get_connection()

    try:
        # Assignment and published status are checked before password verification.
        exam = connection.execute(
            """
            SELECT t.id, t.password_hash
            FROM teacher_tests t
            INNER JOIN teacher_test_assignments a ON a.test_id = t.id
            WHERE t.id = ? AND a.student_id = ? AND t.status = 'published'
            """,
            (exam_id, student["id"])
        ).fetchone()

        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found.")

        if not exam["password_hash"]:
            return {"status": "success", "unlocked": True}

        if _is_exam_unlocked(connection, exam, student["id"]):
            return {"status": "success", "unlocked": True}

        now = _now_exam_time()
        attempt = connection.execute(
            """SELECT failed_count, locked_until
               FROM teacher_test_password_attempts
               WHERE test_id = ? AND student_id = ?""",
            (exam_id, student["id"])
        ).fetchone()

        locked_until = (
            _parse_exam_time(attempt["locked_until"])
            if attempt and attempt["locked_until"] else None
        )
        if locked_until and now < locked_until:
            raise HTTPException(
                status_code=429,
                detail="Too many incorrect passwords. Try again in 15 minutes."
            )

        if not verify_password(payload.password, exam["password_hash"]):
            failed_count = (
                int(attempt["failed_count"])
                if attempt and not (locked_until and now >= locked_until)
                else 0
            ) + 1
            new_lock = (
                (now + timedelta(minutes=15)).isoformat()
                if failed_count >= 5 else None
            )
            connection.execute(
                """INSERT INTO teacher_test_password_attempts
                   (test_id, student_id, failed_count, locked_until, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(test_id, student_id) DO UPDATE SET
                     failed_count = excluded.failed_count,
                     locked_until = excluded.locked_until,
                     updated_at = excluded.updated_at""",
                (exam_id, student["id"], failed_count, new_lock, now.isoformat())
            )
            connection.commit()
            if new_lock:
                raise HTTPException(
                    status_code=429,
                    detail="Too many incorrect passwords. Try again in 15 minutes."
                )
            raise HTTPException(status_code=403, detail="Incorrect exam password.")

        connection.execute(
            """INSERT OR IGNORE INTO teacher_test_password_unlocks
               (test_id, student_id, unlocked_at) VALUES (?, ?, ?)""",
            (exam_id, student["id"], now.isoformat())
        )
        connection.execute(
            "DELETE FROM teacher_test_password_attempts WHERE test_id = ? AND student_id = ?",
            (exam_id, student["id"])
        )
        connection.commit()
        return {"status": "success", "unlocked": True}

    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/{exam_id}/session")
def autosave_exam(
    exam_id: str,
    payload: ExamAutosave,
    request: Request,
):
    student = require_student(request)
    connection = get_connection()

    try:
        exam = connection.execute(
            """
            SELECT t.id, t.duration_minutes, t.deadline_at, t.password_hash
            FROM teacher_tests t
            INNER JOIN teacher_test_assignments a ON a.test_id = t.id
            WHERE t.id = ? AND a.student_id = ? AND t.status = 'published'
            """,
            (exam_id, student["id"]),
        ).fetchone()

        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found.")

        _require_exam_unlocked(connection, exam, student["id"])

        # Create a session if necessary. This helper may commit when creating
        # one, so acquire the write lock immediately afterward and recheck all
        # submission-sensitive state under that lock.
        _ensure_exam_session(connection, exam, student["id"])
        connection.execute("BEGIN IMMEDIATE")

        attempt = connection.execute(
            "SELECT id FROM teacher_test_attempts WHERE test_id = ? AND student_id = ?",
            (exam_id, student["id"]),
        ).fetchone()
        if attempt:
            raise HTTPException(
                status_code=400,
                detail="This exam has already been submitted.",
            )

        session = connection.execute(
            """
            SELECT expires_at, submitted_at
            FROM teacher_test_sessions
            WHERE test_id = ? AND student_id = ?
            """,
            (exam_id, student["id"]),
        ).fetchone()

        if not session:
            raise HTTPException(
                status_code=409,
                detail="Exam session is unavailable.",
            )

        if session["submitted_at"] is not None:
            raise HTTPException(
                status_code=409,
                detail="This exam session has already been finalized.",
            )

        if _now_exam_time() >= _parse_exam_time(session["expires_at"]):
            raise HTTPException(
                status_code=409,
                detail="Exam time has expired. Submitting saved answers.",
            )

        # Autosave receives a complete snapshot from the browser.
        # The conditional update is a final guard against finalized sessions.
        snapshot = payload.answers
        cursor = connection.execute(
            """
            UPDATE teacher_test_sessions
            SET answers_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE test_id = ? AND student_id = ? AND submitted_at IS NULL
            """,
            (json.dumps(snapshot), exam_id, student["id"]),
        )

        if cursor.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail="Exam session has already been finalized.",
            )

        connection.commit()
        return {"status": "success", "saved": True}

    except HTTPException:
        connection.rollback()
        raise
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()



def _grade_and_record_exam(
    connection, exam, exam_id, student_id, answers_to_grade
):
    questions = connection.execute(
        """
        SELECT
            id,
            question_index,
            correct_answer,
            question_type,
            correct_answer_text
        FROM teacher_test_questions
        WHERE test_id = ?
        ORDER BY question_index ASC
        """,
        (exam_id,)
    ).fetchall()

    if not questions:
        raise HTTPException(
            status_code=400,
            detail="This exam has no questions."
        )

    score = 0
    answer_records = []

    for question in questions:
        question_id = question["id"]
        question_type = question["question_type"] or "multiple_choice"
        submitted = answers_to_grade.get(str(question_id))

        selected_answer = None
        selected_answer_text = None
        correct_answer_text = question["correct_answer_text"]
        is_correct = False

        if question_type in ("multiple_choice", "true_false"):
            if submitted is not None and not isinstance(submitted, bool):
                try:
                    selected_answer = int(submitted)
                except (TypeError, ValueError):
                    selected_answer = None

            is_correct = (
                selected_answer is not None
                and selected_answer == question["correct_answer"]
            )

        elif question_type == "fill_blank":
            if isinstance(submitted, str):
                selected_answer_text = submitted.strip()
            expected = (correct_answer_text or "").strip()
            is_correct = bool(
                selected_answer_text
                and expected
                and selected_answer_text.casefold() == expected.casefold()
            )

        if is_correct:
            score += 1

        answer_records.append(
            (
                question_id,
                selected_answer,
                question["correct_answer"],
                1 if is_correct else 0,
                selected_answer_text,
                correct_answer_text,
            )
        )

    total_questions = len(questions)
    percentage = round(
        (score / total_questions) * 100,
        2
    )

    cursor = connection.execute(
        """
        INSERT INTO teacher_test_attempts (
            test_id,
            student_id,
            score,
            total_questions,
            percentage
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            exam_id,
            student_id,
            score,
            total_questions,
            percentage
        )
    )

    attempt_id = cursor.lastrowid

    for (
        question_id,
        selected_answer,
        correct_answer,
        is_correct,
        selected_answer_text,
        correct_answer_text,
    ) in answer_records:
        connection.execute(
            """
            INSERT INTO teacher_test_answers (
                attempt_id,
                question_id,
                selected_answer,
                correct_answer,
                is_correct,
                selected_answer_text,
                correct_answer_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                question_id,
                selected_answer,
                correct_answer,
                is_correct,
                selected_answer_text,
                correct_answer_text,
            )
        )

    # Notify the teacher who created this exam.
    connection.execute(
        """
        INSERT INTO notifications (
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
            exam["creator_id"],
            "exam_submitted",
            "Exam Submitted",
            f'A student has submitted the exam "{exam["title"]}".',
            "teacher_test",
            exam_id,
        ),
    )

    connection.execute(
        """UPDATE teacher_test_sessions
           SET submitted_at = COALESCE(submitted_at, CURRENT_TIMESTAMP),
               updated_at = CURRENT_TIMESTAMP
           WHERE test_id = ? AND student_id = ?""",
        (exam_id, student_id),
    )
    return {"attempt_id": attempt_id, "total_questions": total_questions}

@router.post("/{exam_id}/submit")
def submit_exam(
    exam_id: str,
    payload: ExamSubmit,
    request: Request
):
    student = require_student(request)

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")
        exam = connection.execute(
            """
            SELECT
                t.id,
                t.title,
                t.creator_id,
                t.duration_minutes,
                t.deadline_at,
                t.password_hash
            FROM teacher_tests t
            INNER JOIN teacher_test_assignments a
                ON a.test_id = t.id
            WHERE t.id = ?
              AND a.student_id = ?
              AND t.status = 'published'
            """,
            (exam_id, student["id"])
        ).fetchone()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        _require_exam_unlocked(connection, exam, student["id"])

        existing_attempt = connection.execute(
            """
            SELECT id
            FROM teacher_test_attempts
            WHERE test_id = ?
              AND student_id = ?
            """,
            (exam_id, student["id"])
        ).fetchone()

        if existing_attempt:
            raise HTTPException(
                status_code=400,
                detail="This exam has already been submitted."
            )

        session = connection.execute(
            """SELECT started_at, expires_at, answers_json, submitted_at
               FROM teacher_test_sessions
               WHERE test_id = ? AND student_id = ?""",
            (exam_id, student["id"]),
        ).fetchone()

        if not session:
            raise HTTPException(
                status_code=409,
                detail="Exam session has not started. Open the exam before submitting.",
            )

        expired = _now_exam_time() >= _parse_exam_time(session["expires_at"])

        if expired and not payload.auto_submit:
            raise HTTPException(
                status_code=409,
                detail="Exam time has expired. Only automatic submission of saved answers is allowed.",
            )

        if payload.auto_submit and not expired:
            raise HTTPException(
                status_code=409,
                detail="Automatic submission is only allowed after the exam time expires.",
            )

        try:
            saved = json.loads(session["answers_json"] or "{}")
            if not isinstance(saved, dict):
                saved = {}
        except (TypeError, ValueError):
            saved = {}

        # At expiry, grade only the last server-saved snapshot.
        # Before expiry, a manual submission can include its latest answers.
        answers_to_grade = (
            saved if expired
            else {**saved, **payload.answers}
        )

        result = _grade_and_record_exam(
            connection, exam, exam_id, student['id'], answers_to_grade
        )
        connection.commit()

        return {
            "status": "success",
            "message": "Exam submitted successfully. Your teacher will release the result when it is ready.",
            "result": {
                "exam_id": exam_id,
                "exam_title": exam["title"],
                "score_released": False,
                "score": None,
                "total_questions": result["total_questions"],
                "percentage": None,
                "submitted_at": connection.execute(
                    """
                    SELECT submitted_at
                    FROM teacher_test_attempts
                    WHERE id = ?
                    """,
                    (result["attempt_id"],)
                ).fetchone()["submitted_at"]
            }
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def process_expired_exam_sessions():
    """Finalize expired exams even when the student has closed the browser."""
    scan_connection = get_connection()
    try:
        candidates = scan_connection.execute(
            """
            SELECT test_id, student_id, expires_at
            FROM teacher_test_sessions
            WHERE submitted_at IS NULL
            """
        ).fetchall()
    finally:
        scan_connection.close()

    now = _now_exam_time()
    expired_candidates = []
    for candidate in candidates:
        expiry = _parse_exam_time(candidate["expires_at"])
        if expiry and now >= expiry:
            expired_candidates.append(
                (candidate["test_id"], candidate["student_id"])
            )

    processed = 0

    for exam_id, student_id in expired_candidates:
        connection = get_connection()
        try:
            # Serialize finalization against other writers, including
            # simultaneous expiry-worker iterations.
            connection.execute("BEGIN IMMEDIATE")

            session = connection.execute(
                """
                SELECT expires_at, answers_json, submitted_at
                FROM teacher_test_sessions
                WHERE test_id = ? AND student_id = ?
                """,
                (exam_id, student_id),
            ).fetchone()

            if not session or session["submitted_at"] is not None:
                connection.rollback()
                continue

            expiry = _parse_exam_time(session["expires_at"])
            if not expiry or _now_exam_time() < expiry:
                connection.rollback()
                continue

            existing_attempt = connection.execute(
                """
                SELECT id
                FROM teacher_test_attempts
                WHERE test_id = ? AND student_id = ?
                """,
                (exam_id, student_id),
            ).fetchone()

            if existing_attempt:
                connection.execute(
                    """
                    UPDATE teacher_test_sessions
                    SET submitted_at = COALESCE(submitted_at, CURRENT_TIMESTAMP),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE test_id = ? AND student_id = ?
                    """,
                    (exam_id, student_id),
                )
                connection.commit()
                continue

            exam = connection.execute(
                "SELECT * FROM teacher_tests WHERE id = ?",
                (exam_id,),
            ).fetchone()

            if not exam:
                connection.rollback()
                continue

            try:
                saved_answers = json.loads(session["answers_json"] or "{}")
            except (TypeError, ValueError):
                saved_answers = {}

            if not isinstance(saved_answers, dict):
                saved_answers = {}

            _grade_and_record_exam(
                connection,
                exam,
                exam_id,
                student_id,
                saved_answers,
            )
            connection.commit()
            processed += 1

        except Exception as exc:
            connection.rollback()
            print(
                f"[KANIA exam expiry] Could not finalize exam "
                f"{exam_id} for student {student_id}: {exc}"
            )
        finally:
            connection.close()

    return processed


class ExamMonitorEvent(BaseModel):
    event_type: str
    event_detail: str | None = None


@router.post("/{exam_id}/monitor")
def monitor_exam_event(
    exam_id: str,
    payload: ExamMonitorEvent,
    request: Request
):
    student = require_student(request)

    allowed_events = {
        "EXAM_STARTED",
        "TAB_SWITCH",
        "WINDOW_BLUR",
        "WINDOW_FOCUS",
        "FORBIDDEN_KEY",
    }

    event_type = payload.event_type.strip().upper()

    if event_type not in allowed_events:
        raise HTTPException(
            status_code=400,
            detail="Invalid monitoring event type."
        )

    connection = get_connection()

    try:
        exam = connection.execute(
            """
            SELECT t.id, t.password_hash
            FROM teacher_tests t
            INNER JOIN teacher_test_assignments a ON a.test_id = t.id
            WHERE t.id = ? AND a.student_id = ? AND t.status = 'published'
            """,
            (exam_id, student["id"])
        ).fetchone()

        if not exam:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        _require_exam_unlocked(connection, exam, student["id"])

        detail = (
            payload.event_detail.strip()
            if payload.event_detail
            else None
        )

        connection.execute(
            """
            INSERT INTO teacher_exam_monitoring_events (
                exam_id,
                student_id,
                event_type,
                event_detail
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                exam_id,
                student["id"],
                event_type,
                detail
            )
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Monitoring event recorded."
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


print("=== STUDENT EXAMS API CREATED ===")
