import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.ai.llm import generate_flashcards, GeminiQuotaError
from app.database.database import get_connection


router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


def ensure_review_columns(connection):
    """Add spaced-repetition fields without deleting existing flashcards."""
    existing = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(flashcards)"
        ).fetchall()
    }

    migrations = {
        "next_review_at": "TEXT",
        "interval_days": "INTEGER NOT NULL DEFAULT 0",
        "ease_factor": "REAL NOT NULL DEFAULT 2.5",
        "repetitions": "INTEGER NOT NULL DEFAULT 0",
        "last_reviewed_at": "TEXT",
    }

    for name, definition in migrations.items():
        if name not in existing:
            connection.execute(
                f"ALTER TABLE flashcards ADD COLUMN {name} {definition}"
            )

    connection.commit()


def require_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


class GenerateFlashcardsRequest(BaseModel):
    document_id: str
    card_count: int = Field(default=10, ge=1, le=30)
    topic: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)


class ReviewFlashcardRequest(BaseModel):
    rating: str


@router.post("/generate")
def generate_flashcard_set(data: GenerateFlashcardsRequest, request: Request):
    user = require_user(request)
    connection = get_connection()

    try:
        ensure_review_columns(connection)

        document = connection.execute(
            "SELECT id, filename FROM documents WHERE id = ?",
            (data.document_id,),
        ).fetchone()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")

        chunks = connection.execute(
            """
            SELECT content
            FROM document_chunks
            WHERE document_id = ?
            ORDER BY chunk_index, id
            """,
            (data.document_id,),
        ).fetchall()

        context = "\n\n".join(row["content"] for row in chunks).strip()

        if not context:
            raise HTTPException(
                status_code=404,
                detail="No study material found for this document.",
            )

        # Keep prompts bounded for large uploaded documents.
        context = context[:60000]

    finally:
        connection.close()

    try:
        cards = generate_flashcards(
            context=context,
            card_count=data.card_count,
            focus_topic=data.topic,
        )
    except GeminiQuotaError:
        raise HTTPException(
            status_code=503,
            detail="AI quota is exhausted. Please try again after it resets.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        print(f"Flashcard generation error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not generate flashcards. Check the server logs.",
        )

    set_id = str(uuid.uuid4())
    title = (data.title or "").strip() or (
        f"{document['filename']} Flashcards"
    )
    now = datetime.now(timezone.utc).isoformat()

    connection = get_connection()
    try:
        ensure_review_columns(connection)
        connection.execute("BEGIN")

        connection.execute(
            """
            INSERT INTO flashcard_sets (id, user_id, document_id, title)
            VALUES (?, ?, ?, ?)
            """,
            (set_id, user["id"], data.document_id, title),
        )

        saved_cards = []
        for card in cards:
            card_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO flashcards (
                    id, set_id, user_id, document_id,
                    question, answer, topic, difficulty, status,
                    next_review_at, interval_days, ease_factor, repetitions
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'medium', 'learning', ?, 0, 2.5, 0)
                """,
                (
                    card_id,
                    set_id,
                    user["id"],
                    data.document_id,
                    card["question"],
                    card["answer"],
                    card.get("topic", "General"),
                    now,
                ),
            )
            saved_cards.append({
                "id": card_id,
                "question": card["question"],
                "answer": card["answer"],
                "topic": card.get("topic", "General"),
                "status": "learning",
                "next_review_at": now,
            })

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return {
        "status": "success",
        "set_id": set_id,
        "title": title,
        "document_id": data.document_id,
        "filename": document["filename"],
        "card_count": len(saved_cards),
        "cards": saved_cards,
    }


@router.get("/sets")
def list_flashcard_sets(request: Request):
    user = require_user(request)
    connection = get_connection()

    try:
        ensure_review_columns(connection)
        rows = connection.execute(
            """
            SELECT
                s.id, s.document_id, s.title, s.created_at,
                d.filename,
                COUNT(f.id) AS card_count,
                SUM(
                    CASE
                        WHEN f.id IS NOT NULL
                         AND (f.next_review_at IS NULL
                              OR f.next_review_at <= ?)
                        THEN 1 ELSE 0
                    END
                ) AS due_count
            FROM flashcard_sets s
            LEFT JOIN documents d ON d.id = s.document_id
            LEFT JOIN flashcards f ON f.set_id = s.id
            WHERE s.user_id = ?
            GROUP BY s.id
            ORDER BY s.created_at DESC
            """,
            (datetime.now(timezone.utc).isoformat(), user["id"]),
        ).fetchall()

        return {
            "status": "success",
            "sets": [
                {
                    "id": row["id"],
                    "document_id": row["document_id"],
                    "title": row["title"],
                    "filename": row["filename"],
                    "created_at": row["created_at"],
                    "card_count": row["card_count"],
                    "due_count": row["due_count"] or 0,
                }
                for row in rows
            ],
        }
    finally:
        connection.close()


@router.get("/sets/{set_id}")
def get_flashcard_set(set_id: str, request: Request):
    user = require_user(request)
    connection = get_connection()

    try:
        ensure_review_columns(connection)
        card_set = connection.execute(
            """
            SELECT id, title, document_id, created_at
            FROM flashcard_sets
            WHERE id = ? AND user_id = ?
            """,
            (set_id, user["id"]),
        ).fetchone()

        if not card_set:
            raise HTTPException(
                status_code=404,
                detail="Flashcard set not found.",
            )

        rows = connection.execute(
            """
            SELECT id, question, answer, topic, difficulty, status,
                   next_review_at, interval_days, repetitions
            FROM flashcards
            WHERE set_id = ? AND user_id = ?
            ORDER BY created_at, rowid
            """,
            (set_id, user["id"]),
        ).fetchall()

        return {
            "status": "success",
            "set": dict(card_set),
            "cards": [dict(row) for row in rows],
        }
    finally:
        connection.close()


@router.post("/{card_id}/review")
def review_flashcard(
    card_id: str,
    data: ReviewFlashcardRequest,
    request: Request,
):
    user = require_user(request)
    rating = data.rating.strip().lower()

    if rating not in {"again", "hard", "good", "easy"}:
        raise HTTPException(
            status_code=422,
            detail="Rating must be again, hard, good, or easy.",
        )

    now = datetime.now(timezone.utc)
    connection = get_connection()

    try:
        ensure_review_columns(connection)
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute(
            """
            SELECT id, interval_days, ease_factor, repetitions
            FROM flashcards
            WHERE id = ? AND user_id = ?
            """,
            (card_id, user["id"]),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Flashcard not found.")

        interval = int(row["interval_days"] or 0)
        ease = float(row["ease_factor"] or 2.5)
        repetitions = int(row["repetitions"] or 0)

        if rating == "again":
            interval = 0
            repetitions = 0
            ease = max(1.3, ease - 0.20)
            due = now + timedelta(minutes=10)
            status = "learning"
        elif rating == "hard":
            interval = max(1, round(interval * 1.2)) if interval else 1
            repetitions += 1
            ease = max(1.3, ease - 0.15)
            due = now + timedelta(days=interval)
            status = "learning"
        elif rating == "good":
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = max(1, round(max(interval, 1) * ease))
            repetitions += 1
            due = now + timedelta(days=interval)
            status = "review"
        else:  # easy
            if repetitions == 0:
                interval = 4
            elif repetitions == 1:
                interval = 7
            else:
                interval = max(1, round(max(interval, 1) * (ease + 0.3)))
            repetitions += 1
            ease += 0.15
            due = now + timedelta(days=interval)
            status = "mastered" if repetitions >= 3 else "review"

        due_text = due.isoformat()
        reviewed_text = now.isoformat()

        connection.execute(
            """
            UPDATE flashcards
            SET interval_days = ?, ease_factor = ?, repetitions = ?,
                next_review_at = ?, last_reviewed_at = ?,
                status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (
                interval, ease, repetitions, due_text, reviewed_text,
                status, card_id, user["id"],
            ),
        )
        connection.commit()

        return {
            "status": "success",
            "card_id": card_id,
            "rating": rating,
            "next_review_at": due_text,
            "interval_days": interval,
            "repetitions": repetitions,
            "ease_factor": round(ease, 2),
            "card_status": status,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
