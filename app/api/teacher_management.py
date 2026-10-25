import sqlite3

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.api.auth import get_current_user, hash_password
from app.database.database import get_connection


router = APIRouter(
    prefix="/api/admin/teachers",
    tags=["Admin Teacher Management"],
)


class TeacherCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


def require_admin(request: Request):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required.",
        )

    return user


@router.get("")
def list_teachers(request: Request):
    require_admin(request)

    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, name, email, created_at
            FROM users
            WHERE role = 'teacher'
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

        return {
            "teachers": [dict(row) for row in rows],
            "count": len(rows),
        }
    finally:
        connection.close()


@router.post("", status_code=201)
def create_teacher(data: TeacherCreate, request: Request):
    require_admin(request)

    name = data.name.strip()
    email = str(data.email).strip().lower()

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Name must contain at least 2 characters.",
        )

    connection = get_connection()
    try:
        existing = connection.execute(
            "SELECT id FROM users WHERE lower(email) = ?",
            (email,),
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists.",
            )

        cursor = connection.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (?, ?, ?, 'teacher')
            """,
            (name, email, hash_password(data.password)),
        )
        teacher_id = cursor.lastrowid
        connection.commit()

        return {
            "status": "success",
            "message": "Teacher account created successfully.",
            "teacher": {
                "id": teacher_id,
                "name": name,
                "email": email,
                "role": "teacher",
            },
        }

    except sqlite3.IntegrityError:
        connection.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )
    finally:
        connection.close()
