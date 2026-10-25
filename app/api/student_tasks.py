from fastapi import APIRouter, HTTPException, Request

from app.api.auth import get_current_user
from app.database.database import get_connection


router = APIRouter(
    prefix="/api/student/tasks",
    tags=["Student Tasks"],
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
def list_student_tasks(request: Request):
    user = require_student(request)

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            t.id,
            t.title,
            t.instructions,
            t.priority,
            t.due_date,
            t.status,
            t.created_at,
            t.published_at,
            p.status AS progress_status,
            p.completed_at,
            (
                SELECT COUNT(*)
                FROM teacher_task_materials m
                WHERE m.task_id = t.id
            ) AS material_count
        FROM teacher_task_assignments a
        JOIN teacher_tasks t
            ON t.id = a.task_id
        LEFT JOIN teacher_task_progress p
            ON p.task_id = t.id
            AND p.student_id = ?
        WHERE a.student_id = ?
          AND t.status = 'published'
        ORDER BY
            CASE t.priority
                WHEN 'high' THEN 1
                WHEN 'normal' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            CASE
                WHEN t.due_date IS NULL THEN 1
                ELSE 0
            END,
            t.due_date ASC,
            t.created_at DESC
        """,
        (user["id"], user["id"]),
    ).fetchall()

    connection.close()

    return {
        "tasks": [dict(row) for row in rows],
        "count": len(rows),
    }


@router.get("/{task_id}")
def get_student_task(task_id: str, request: Request):
    user = require_student(request)

    connection = get_connection()

    task = connection.execute(
        """
        SELECT
            t.id,
            t.title,
            t.instructions,
            t.priority,
            t.due_date,
            t.status,
            t.created_at,
            t.published_at,
            p.status AS progress_status,
            p.completed_at
        FROM teacher_task_assignments a
        JOIN teacher_tasks t
            ON t.id = a.task_id
        LEFT JOIN teacher_task_progress p
            ON p.task_id = t.id
            AND p.student_id = ?
        WHERE a.task_id = ?
          AND a.student_id = ?
          AND t.status = 'published'
        """,
        (user["id"], task_id, user["id"]),
    ).fetchone()

    if not task:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Task not found."
        )

    materials = connection.execute(
        """
        SELECT
            id,
            material_index,
            source_type,
            document_id,
            title,
            book,
            chapter,
            topic,
            section,
            instructions,
            external_reference
        FROM teacher_task_materials
        WHERE task_id = ?
        ORDER BY material_index ASC
        """,
        (task_id,),
    ).fetchall()

    connection.close()

    return {
        "task": dict(task),
        "materials": [dict(row) for row in materials],
    }


@router.post("/{task_id}/complete")
def complete_student_task(task_id: str, request: Request):
    user = require_student(request)

    connection = get_connection()

    assignment = connection.execute(
        """
        SELECT
            t.id
        FROM teacher_task_assignments a
        JOIN teacher_tasks t
            ON t.id = a.task_id
        WHERE a.task_id = ?
          AND a.student_id = ?
          AND t.status = 'published'
        """,
        (task_id, user["id"]),
    ).fetchone()

    if not assignment:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Task not found."
        )

    connection.execute(
        """
        INSERT INTO teacher_task_progress (
            task_id,
            student_id,
            status,
            completed_at,
            updated_at
        )
        VALUES (?, ?, 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(task_id, student_id)
        DO UPDATE SET
            status = 'completed',
            completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """,
        (task_id, user["id"]),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Task marked as completed.",
        "task_id": task_id,
        "status": "completed",
    }
