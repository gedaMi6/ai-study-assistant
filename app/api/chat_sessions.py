from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.database.database import get_connection

router = APIRouter(prefix="/chat", tags=["Chat Sessions"])


class CreateChatRequest(BaseModel):
    session_id: str | None = None


class RenameChatRequest(BaseModel):
    title: str


class PinChatRequest(BaseModel):
    is_pinned: bool


def require_user(request: Request):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    return user


def make_title(text: str | None) -> str:
    if not text:
        return "New chat"

    title = " ".join(text.strip().split())

    if not title:
        return "New chat"

    if len(title) <= 50:
        return title

    return title[:47].rstrip() + "..."


def get_first_question(connection, session_id: str):
    row = connection.execute(
        """
        SELECT content
        FROM conversations
        WHERE session_id = ?
          AND role = 'user'
        ORDER BY id ASC
        LIMIT 1
        """,
        (session_id,)
    ).fetchone()

    return row["content"] if row else None


def ensure_chat_session(
    session_id: str,
    user_id: int,
    title: str | None = None
):
    connection = get_connection()

    existing = connection.execute(
        """
        SELECT
            id,
            user_id,
            title,
            created_at,
            updated_at,
            is_pinned
        FROM chat_sessions
        WHERE id = ?
        """,
        (session_id,)
    ).fetchone()

    if existing:
        if existing["user_id"] != user_id:
            connection.close()

            raise HTTPException(
                status_code=403,
                detail="You do not have access to this chat."
            )

        if (
            title
            and existing["title"] == "New chat"
        ):
            new_title = make_title(title)

            connection.execute(
                """
                UPDATE chat_sessions
                SET title = ?
                WHERE id = ?
                  AND user_id = ?
                """,
                (
                    new_title,
                    session_id,
                    user_id
                )
            )

            connection.commit()

            existing = connection.execute(
                """
                SELECT
                    id,
                    user_id,
                    title,
                    created_at,
                    updated_at,
                    is_pinned
                FROM chat_sessions
                WHERE id = ?
                """,
                (session_id,)
            ).fetchone()

        connection.close()

        return dict(existing)

    first_question = get_first_question(
        connection,
        session_id
    )

    final_title = make_title(
        title or first_question
    )

    connection.execute(
        """
        INSERT INTO chat_sessions (
            id,
            user_id,
            title,
            is_pinned
        )
        VALUES (?, ?, ?, 0)
        """,
        (
            session_id,
            user_id,
            final_title
        )
    )

    connection.commit()

    row = connection.execute(
        """
        SELECT
            id,
            user_id,
            title,
            created_at,
            updated_at,
            is_pinned
        FROM chat_sessions
        WHERE id = ?
        """,
        (session_id,)
    ).fetchone()

    connection.close()

    return dict(row)


def touch_chat_session(
    session_id: str,
    user_id: int
):
    connection = get_connection()

    connection.execute(
        """
        UPDATE chat_sessions
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND user_id = ?
        """,
        (
            session_id,
            user_id
        )
    )

    connection.commit()
    connection.close()


@router.get("/sessions")
def list_chat_sessions(request: Request):
    user = require_user(request)

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            title,
            created_at,
            updated_at,
            is_pinned
        FROM chat_sessions
        WHERE user_id = ?
        ORDER BY
            is_pinned DESC,
            datetime(updated_at) DESC,
            datetime(created_at) DESC
        LIMIT 50
        """,
        (user["id"],)
    ).fetchall()

    connection.close()

    sessions = [
        {
            "session_id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_pinned": bool(row["is_pinned"])
        }
        for row in rows
    ]

    return {
        "status": "success",
        "sessions": sessions
    }


@router.post("/sessions")
def create_chat_session(
    request: Request,
    data: CreateChatRequest
):
    user = require_user(request)

    session_id = (
        data.session_id.strip()
        if data.session_id
        else str(uuid4())
    )

    if not session_id:
        session_id = str(uuid4())

    session = ensure_chat_session(
        session_id=session_id,
        user_id=user["id"]
    )

    return {
        "status": "success",
        "session": {
            "session_id": session["id"],
            "title": session["title"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "is_pinned": bool(session["is_pinned"])
        }
    }


@router.get("/sessions/{session_id}")
def get_chat_session(
    session_id: str,
    request: Request
):
    user = require_user(request)

    connection = get_connection()

    session = connection.execute(
        """
        SELECT
            id,
            title,
            created_at,
            updated_at,
            is_pinned
        FROM chat_sessions
        WHERE id = ?
          AND user_id = ?
        """,
        (
            session_id,
            user["id"]
        )
    ).fetchone()

    if not session:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Chat session not found."
        )

    messages = connection.execute(
        """
        SELECT
            role,
            content,
            created_at
        FROM conversations
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,)
    ).fetchall()

    connection.close()

    return {
        "status": "success",
        "session": {
            "session_id": session["id"],
            "title": session["title"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "is_pinned": bool(session["is_pinned"])
        },
        "messages": [
            {
                "role": message["role"],
                "content": message["content"],
                "created_at": message["created_at"]
            }
            for message in messages
        ]
    }


@router.patch("/sessions/{session_id}")
def rename_chat_session(
    session_id: str,
    request: Request,
    data: RenameChatRequest
):
    user = require_user(request)

    title = " ".join(data.title.strip().split())

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Chat title cannot be empty."
        )

    if len(title) > 60:
        title = title[:57].rstrip() + "..."

    connection = get_connection()

    existing = connection.execute(
        """
        SELECT id
        FROM chat_sessions
        WHERE id = ?
          AND user_id = ?
        """,
        (
            session_id,
            user["id"]
        )
    ).fetchone()

    if not existing:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Chat session not found."
        )

    connection.execute(
        """
        UPDATE chat_sessions
        SET
            title = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND user_id = ?
        """,
        (
            title,
            session_id,
            user["id"]
        )
    )

    connection.commit()

    row = connection.execute(
        """
        SELECT
            id,
            title,
            created_at,
            updated_at,
            is_pinned
        FROM chat_sessions
        WHERE id = ?
          AND user_id = ?
        """,
        (
            session_id,
            user["id"]
        )
    ).fetchone()

    connection.close()

    return {
        "status": "success",
        "session": {
            "session_id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_pinned": bool(row["is_pinned"])
        }
    }


@router.patch("/sessions/{session_id}/pin")
def pin_chat_session(
    session_id: str,
    request: Request,
    data: PinChatRequest
):
    user = require_user(request)

    connection = get_connection()

    existing = connection.execute(
        """
        SELECT id
        FROM chat_sessions
        WHERE id = ?
          AND user_id = ?
        """,
        (
            session_id,
            user["id"]
        )
    ).fetchone()

    if not existing:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Chat session not found."
        )

    connection.execute(
        """
        UPDATE chat_sessions
        SET
            is_pinned = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND user_id = ?
        """,
        (
            1 if data.is_pinned else 0,
            session_id,
            user["id"]
        )
    )

    connection.commit()

    row = connection.execute(
        """
        SELECT
            id,
            title,
            created_at,
            updated_at,
            is_pinned
        FROM chat_sessions
        WHERE id = ?
          AND user_id = ?
        """,
        (
            session_id,
            user["id"]
        )
    ).fetchone()

    connection.close()

    return {
        "status": "success",
        "session": {
            "session_id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_pinned": bool(row["is_pinned"])
        }
    }


@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    request: Request
):
    user = require_user(request)

    connection = get_connection()

    existing = connection.execute(
        """
        SELECT id
        FROM chat_sessions
        WHERE id = ?
          AND user_id = ?
        """,
        (
            session_id,
            user["id"]
        )
    ).fetchone()

    if not existing:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Chat session not found."
        )

    connection.execute(
        """
        DELETE FROM conversations
        WHERE session_id = ?
        """,
        (session_id,)
    )

    connection.execute(
        """
        DELETE FROM chat_sessions
        WHERE id = ?
          AND user_id = ?
        """,
        (
            session_id,
            user["id"]
        )
    )

    connection.commit()
    connection.close()

    return {
        "status": "success",
        "session_id": session_id
    }
