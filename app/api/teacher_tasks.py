from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
import uuid

from app.api.auth import get_current_user
from app.database.database import get_connection


router = APIRouter(
    prefix="/api/teacher/tasks",
    tags=["Teacher Tasks"],
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


class TeacherTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    instructions: str = Field(..., min_length=1, max_length=5000)
    priority: str = Field(default="normal", max_length=20)
    due_date: Optional[str] = None


class TeacherTaskUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200
    )
    instructions: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=5000
    )
    priority: Optional[str] = Field(
        default=None,
        max_length=20
    )
    due_date: Optional[str] = None


class TeacherTaskAssign(BaseModel):
    student_ids: list[int] = Field(
        ...,
        min_length=1
    )


@router.post("")
def create_task(
    payload: TeacherTaskCreate,
    request: Request
):
    teacher = require_teacher(request)

    allowed_priorities = {"low", "normal", "high"}

    if payload.priority.lower() not in allowed_priorities:
        raise HTTPException(
            status_code=400,
            detail="Priority must be low, normal, or high."
        )

    task_id = str(uuid.uuid4())

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO teacher_tasks (
                id,
                creator_id,
                title,
                instructions,
                priority,
                due_date,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'draft')
            """,
            (
                task_id,
                teacher["id"],
                payload.title.strip(),
                payload.instructions.strip(),
                payload.priority.lower(),
                payload.due_date,
            )
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Teacher task created successfully.",
            "task": {
                "id": task_id,
                "title": payload.title.strip(),
                "instructions": payload.instructions.strip(),
                "priority": payload.priority.lower(),
                "due_date": payload.due_date,
                "status": "draft",
            }
        }

    finally:
        connection.close()


@router.get("")
def list_tasks(request: Request):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
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
                COUNT(DISTINCT m.id) AS material_count,
                COUNT(DISTINCT a.student_id) AS assigned_students
            FROM teacher_tasks t
            LEFT JOIN teacher_task_materials m
                ON m.task_id = t.id
            LEFT JOIN teacher_task_assignments a
                ON a.task_id = t.id
            WHERE t.creator_id = ?
            GROUP BY
                t.id,
                t.title,
                t.instructions,
                t.priority,
                t.due_date,
                t.status,
                t.created_at,
                t.published_at
            ORDER BY t.created_at DESC
            """,
            (teacher["id"],)
        ).fetchall()

        return {
            "status": "success",
            "tasks": [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "instructions": row["instructions"],
                    "priority": row["priority"],
                    "due_date": row["due_date"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "published_at": row["published_at"],
                    "material_count": row["material_count"],
                    "assigned_students": row["assigned_students"],
                }
                for row in rows
            ]
        }

    finally:
        connection.close()


@router.get("/students")
def list_assignable_students(request: Request):
    require_teacher(request)
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, name, email
            FROM users
            WHERE role = 'student'
            ORDER BY name COLLATE NOCASE ASC
            """
        ).fetchall()
        return {
            "status": "success",
            "students": [dict(row) for row in rows]
        }
    finally:
        connection.close()


@router.get("/{task_id}")
def get_task(
    task_id: str,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        task = connection.execute(
            """
            SELECT
                id,
                title,
                instructions,
                priority,
                due_date,
                status,
                created_at,
                published_at
            FROM teacher_tasks
            WHERE id = ?
              AND creator_id = ?
            """,
            (task_id, teacher["id"])
        ).fetchone()

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Teacher task not found."
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
                external_reference,
                created_at
            FROM teacher_task_materials
            WHERE task_id = ?
            ORDER BY material_index ASC
            """,
            (task_id,)
        ).fetchall()

        assignments = connection.execute(
            """
            SELECT
                a.student_id,
                u.name,
                u.email,
                a.assigned_at
            FROM teacher_task_assignments a
            JOIN users u
                ON u.id = a.student_id
            WHERE a.task_id = ?
            ORDER BY u.name ASC
            """,
            (task_id,)
        ).fetchall()

        return {
            "status": "success",
            "task": {
                "id": task["id"],
                "title": task["title"],
                "instructions": task["instructions"],
                "priority": task["priority"],
                "due_date": task["due_date"],
                "status": task["status"],
                "created_at": task["created_at"],
                "published_at": task["published_at"],
                "materials": [
                    {
                        "id": row["id"],
                        "material_index": row["material_index"],
                        "source_type": row["source_type"],
                        "document_id": row["document_id"],
                        "title": row["title"],
                        "book": row["book"],
                        "chapter": row["chapter"],
                        "topic": row["topic"],
                        "section": row["section"],
                        "instructions": row["instructions"],
                        "external_reference": row["external_reference"],
                        "created_at": row["created_at"],
                    }
                    for row in materials
                ],
                "assignments": [
                    {
                        "student_id": row["student_id"],
                        "name": row["name"],
                        "email": row["email"],
                        "assigned_at": row["assigned_at"],
                    }
                    for row in assignments
                ],
            }
        }

    finally:
        connection.close()


@router.put("/{task_id}")
def update_task(
    task_id: str,
    payload: TeacherTaskUpdate,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        task = connection.execute(
            """
            SELECT id, status
            FROM teacher_tasks
            WHERE id = ?
              AND creator_id = ?
            """,
            (task_id, teacher["id"])
        ).fetchone()

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Teacher task not found."
            )

        if task["status"] == "published":
            raise HTTPException(
                status_code=400,
                detail="Published tasks cannot be edited."
            )

        updates = []
        values = []

        if payload.title is not None:
            updates.append("title = ?")
            values.append(payload.title.strip())

        if payload.instructions is not None:
            updates.append("instructions = ?")
            values.append(payload.instructions.strip())

        if payload.priority is not None:
            priority = payload.priority.lower()

            if priority not in {"low", "normal", "high"}:
                raise HTTPException(
                    status_code=400,
                    detail="Priority must be low, normal, or high."
                )

            updates.append("priority = ?")
            values.append(priority)

        if payload.due_date is not None:
            updates.append("due_date = ?")
            values.append(payload.due_date)

        if not updates:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update."
            )

        values.extend([task_id, teacher["id"]])

        connection.execute(
            f"""
            UPDATE teacher_tasks
            SET {", ".join(updates)}
            WHERE id = ?
              AND creator_id = ?
            """,
            values
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Teacher task updated successfully."
        }

    finally:
        connection.close()


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        task = connection.execute(
            """
            SELECT id, status
            FROM teacher_tasks
            WHERE id = ?
              AND creator_id = ?
            """,
            (task_id, teacher["id"])
        ).fetchone()

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Teacher task not found."
            )

        if task["status"] == "published":
            raise HTTPException(
                status_code=400,
                detail="Published tasks cannot be deleted."
            )

        connection.execute(
            """
            DELETE FROM teacher_tasks
            WHERE id = ?
              AND creator_id = ?
            """,
            (task_id, teacher["id"])
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Teacher task deleted successfully."
        }

    finally:
        connection.close()


class TeacherTaskMaterialCreate(BaseModel):
    source_type: str = Field(default="reference", max_length=30)
    document_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=300)
    book: Optional[str] = Field(default=None, max_length=300)
    chapter: Optional[str] = Field(default=None, max_length=200)
    topic: Optional[str] = Field(default=None, max_length=300)
    section: Optional[str] = Field(default=None, max_length=300)
    instructions: Optional[str] = Field(default=None, max_length=2000)
    external_reference: Optional[str] = Field(default=None, max_length=1000)


@router.post("/{task_id}/materials")
def add_task_material(
    task_id: str,
    payload: TeacherTaskMaterialCreate,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        task = connection.execute(
            """
            SELECT id, status
            FROM teacher_tasks
            WHERE id = ?
              AND creator_id = ?
            """,
            (task_id, teacher["id"])
        ).fetchone()

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Teacher task not found."
            )

        if task["status"] == "published":
            raise HTTPException(
                status_code=400,
                detail="Published tasks cannot be edited."
            )

        next_index = connection.execute(
            """
            SELECT COALESCE(MAX(material_index), -1) + 1
            FROM teacher_task_materials
            WHERE task_id = ?
            """,
            (task_id,)
        ).fetchone()[0]

        connection.execute(
            """
            INSERT INTO teacher_task_materials (
                task_id,
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                next_index,
                payload.source_type.strip(),
                payload.document_id,
                payload.title.strip(),
                payload.book.strip() if payload.book else None,
                payload.chapter.strip() if payload.chapter else None,
                payload.topic.strip() if payload.topic else None,
                payload.section.strip() if payload.section else None,
                payload.instructions.strip()
                if payload.instructions
                else None,
                payload.external_reference.strip()
                if payload.external_reference
                else None,
            )
        )

        connection.commit()

        material_id = connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        return {
            "status": "success",
            "message": "Study material added successfully.",
            "material": {
                "id": material_id,
                "task_id": task_id,
                "material_index": next_index,
                "source_type": payload.source_type.strip(),
                "document_id": payload.document_id,
                "title": payload.title.strip(),
                "book": payload.book.strip() if payload.book else None,
                "chapter": payload.chapter.strip() if payload.chapter else None,
                "topic": payload.topic.strip() if payload.topic else None,
                "section": payload.section.strip() if payload.section else None,
                "instructions": (
                    payload.instructions.strip()
                    if payload.instructions
                    else None
                ),
                "external_reference": (
                    payload.external_reference.strip()
                    if payload.external_reference
                    else None
                ),
            }
        }

    finally:
        connection.close()


@router.post("/{task_id}/publish")
def publish_task(
    task_id: str,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        task = connection.execute(
            """
            SELECT id, status
            FROM teacher_tasks
            WHERE id = ?
              AND creator_id = ?
            """,
            (task_id, teacher["id"])
        ).fetchone()

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Teacher task not found."
            )

        if task["status"] == "published":
            raise HTTPException(
                status_code=400,
                detail="Task is already published."
            )

        material_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM teacher_task_materials
            WHERE task_id = ?
            """,
            (task_id,)
        ).fetchone()[0]

        if material_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Add at least one study material before publishing."
            )

        connection.execute(
            """
            UPDATE teacher_tasks
            SET status = 'published',
                published_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND creator_id = ?
            """,
            (task_id, teacher["id"])
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Teacher task published successfully."
        }

    finally:
        connection.close()


@router.post("/{task_id}/assign")
def assign_task(
    task_id: str,
    payload: TeacherTaskAssign,
    request: Request
):
    teacher = require_teacher(request)

    connection = get_connection()

    try:
        task = connection.execute(
            """
            SELECT id, status
            FROM teacher_tasks
            WHERE id = ?
              AND creator_id = ?
            """,
            (task_id, teacher["id"])
        ).fetchone()

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Teacher task not found."
            )

        if task["status"] != "published":
            raise HTTPException(
                status_code=400,
                detail="Publish the task before assigning it."
            )

        unique_student_ids = list(dict.fromkeys(payload.student_ids))

        placeholders = ",".join("?" for _ in unique_student_ids)

        students = connection.execute(
            f"""
            SELECT id
            FROM users
            WHERE id IN ({placeholders})
              AND role = 'student'
            """,
            unique_student_ids
        ).fetchall()

        valid_student_ids = {row["id"] for row in students}

        invalid_ids = [
            student_id
            for student_id in unique_student_ids
            if student_id not in valid_student_ids
        ]

        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "One or more student IDs are invalid.",
                    "invalid_student_ids": invalid_ids,
                }
            )

        for student_id in unique_student_ids:
            connection.execute(
                """
                INSERT OR IGNORE INTO teacher_task_assignments (
                    task_id,
                    student_id
                )
                VALUES (?, ?)
                """,
                (task_id, student_id)
            )

            connection.execute(
                """
                INSERT OR IGNORE INTO teacher_task_progress (
                    task_id,
                    student_id,
                    status
                )
                VALUES (?, ?, 'assigned')
                """,
                (task_id, student_id)
            )

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
                    "task_assigned",
                    "New Study Task",
                    f'You have been assigned a new study task: "{task["title"]}".',
                    "teacher_task",
                    task_id
                )
            )

        connection.commit()

        return {
            "status": "success",
            "message": "Task assigned successfully.",
            "assigned_students": unique_student_ids,
        }

    finally:
        connection.close()
