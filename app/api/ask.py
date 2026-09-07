from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.api.chat_sessions import (
    ensure_chat_session,
    touch_chat_session
)
from app.services.rag import (
    answer_question,
    get_conversation_history
)


router = APIRouter(
    prefix="/ask",
    tags=["AI Assistant"]
)


class QuestionRequest(BaseModel):
    question: str
    n_results: int = 3
    session_id: str = "default"


@router.get("/history/{session_id}")
def get_history(
    session_id: str,
    request: Request
):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    # Make sure this session belongs to the
    # currently authenticated user.
    ensure_chat_session(
        session_id=session_id,
        user_id=user["id"]
    )

    history = get_conversation_history(
        session_id,
        limit=100
    )

    return {
        "status": "success",
        "session_id": session_id,
        "messages": history
    }


@router.post("")
def ask_question(
    request: Request,
    data: QuestionRequest
):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    if not data.question.strip():
        return {
            "status": "error",
            "message": "Question cannot be empty."
        }

    # Create/register the chat session for this user.
    # The first question becomes its title.
    ensure_chat_session(
        session_id=data.session_id,
        user_id=user["id"],
        title=data.question
    )

    result = answer_question(
        data.question,
        data.n_results,
        data.session_id
    )

    # Move this conversation to the top of
    # the recent-chat list.
    touch_chat_session(
        session_id=data.session_id,
        user_id=user["id"]
    )

    return {
        "status": "success",
        "question": data.question,
        "answer": result["answer"],
        "sources": result["sources"],
        "session_id": data.session_id
    }
