from fastapi import APIRouter, Request, HTTPException

from app.api.teacher_tasks import require_teacher
from app.database.database import get_connection


router = APIRouter(
    prefix="/api/teacher/exam-monitoring",
    tags=["Teacher Exam Monitoring"]
)


@router.get("")
def get_monitoring_events(
    request: Request,
    limit: int = 50,
    unseen_only: bool = False
):
    teacher = require_teacher(request)

    if limit < 1:
        limit = 1

    if limit > 200:
        limit = 200

    connection = get_connection()

    try:
        query = """
            SELECT
                e.id,
                e.exam_id,
                e.student_id,
                u.name AS student_name,
                u.email AS student_email,
                t.title AS exam_title,
                e.event_type,
                e.event_detail,
                e.created_at,
                e.is_seen
            FROM teacher_exam_monitoring_events e
            JOIN users u
                ON u.id = e.student_id
            JOIN teacher_tests t
                ON t.id = e.exam_id
        """

        query += """
            WHERE t.creator_id = ?
        """
        params = [teacher["id"]]

        if unseen_only:
            query += """
                AND e.is_seen = 0
            """

        query += """
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT ?
        """

        params.append(limit)

        rows = connection.execute(
            query,
            params
        ).fetchall()

        events = []

        for row in rows:
            events.append({
                "id": row["id"],
                "exam_id": row["exam_id"],
                "student_id": row["student_id"],
                "student_name": row["student_name"],
                "student_email": row["student_email"],
                "exam_title": row["exam_title"],
                "event_type": row["event_type"],
                "event_detail": row["event_detail"],
                "created_at": row["created_at"],
                "is_seen": bool(row["is_seen"])
            })

        unseen_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM teacher_exam_monitoring_events e
            JOIN teacher_tests t ON t.id = e.exam_id
            WHERE t.creator_id = ?
              AND e.is_seen = 0
            """,
            (teacher["id"],)
        ).fetchone()["count"]

        return {
            "status": "success",
            "events": events,
            "unseen_count": unseen_count
        }

    finally:
        connection.close()


@router.post("/{event_id}/seen")
def mark_monitoring_event_seen(
    event_id: int,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        event = connection.execute(
            """
            SELECT e.id
            FROM teacher_exam_monitoring_events e
            JOIN teacher_tests t ON t.id = e.exam_id
            WHERE e.id = ?
              AND t.creator_id = ?
            """,
            (event_id, teacher["id"])
        ).fetchone()

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Monitoring event not found."
            )

        connection.execute(
            """
            UPDATE teacher_exam_monitoring_events
            SET is_seen = 1
            WHERE id = ?
            """,
            (event_id,)
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Monitoring event marked as seen."
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
