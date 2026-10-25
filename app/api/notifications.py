from fastapi import APIRouter, HTTPException, Request

from app.api.auth import get_current_user
from app.database.database import get_connection


router = APIRouter(
    prefix="/api/student/notifications",
    tags=["Student Notifications"],
)


def require_student(request: Request):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    if user["role"] != "student":
        raise HTTPException(
            status_code=403,
            detail="Student access required."
        )

    return user


@router.get("")
def list_notifications(request: Request):
    user = require_student(request)

    connection = get_connection()

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
          AND is_read = 0
          AND (
              reference_type IS NULL
              OR reference_type != 'teacher_test'
              OR EXISTS (
                  SELECT 1
                  FROM teacher_tests t
                  WHERE t.id = notifications.reference_id
              )
          )
        ORDER BY created_at DESC, id DESC
        """,
        (user["id"],),
    ).fetchall()

    unread_row = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM notifications
        WHERE user_id = ?
          AND is_read = 0
          AND (
              reference_type IS NULL
              OR reference_type != 'teacher_test'
              OR EXISTS (
                  SELECT 1
                  FROM teacher_tests t
                  WHERE t.id = notifications.reference_id
              )
          )
        """,
        (user["id"],),
    ).fetchone()

    connection.close()

    return {
        "notifications": [dict(row) for row in rows],
        "count": len(rows),
        "unread_count": unread_row["count"],
    }


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    request: Request,
):
    user = require_student(request)

    connection = get_connection()

    notification = connection.execute(
        """
        SELECT id
        FROM notifications
        WHERE id = ?
          AND user_id = ?
        """,
        (notification_id, user["id"]),
    ).fetchone()

    if not notification:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Notification not found."
        )

    connection.execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE id = ?
          AND user_id = ?
        """,
        (notification_id, user["id"]),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Notification marked as read.",
        "notification_id": notification_id,
        "is_read": 1,
    }


@router.post("/read-all")
def mark_all_notifications_read(request: Request):
    user = require_student(request)

    connection = get_connection()

    cursor = connection.execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
          AND is_read = 0
        """,
        (user["id"],),
    )

    connection.commit()
    updated_count = cursor.rowcount
    connection.close()

    return {
        "message": "All notifications marked as read.",
        "updated_count": updated_count,
    }
