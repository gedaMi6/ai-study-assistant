import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.database.database import get_connection
from app.api.auth import get_current_user
from app.ai.llm import generate_quiz, GeminiQuotaError


router = APIRouter(
    prefix="/quiz",
    tags=["Quiz"]
)


class QuizRequest(BaseModel):
    document_id: str
    question_count: int = 5


class QuizAnswer(BaseModel):
    question_index: int
    selected_answer: int | None = None


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: list[QuizAnswer]


@router.post("/generate")
def generate_quiz_endpoint(
    request: QuizRequest,
    http_request: Request
):

    user = get_current_user(http_request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    connection = get_connection()

    document = connection.execute(
        """
        SELECT id, filename
        FROM documents
        WHERE id = ?
        """,
        (request.document_id,)
    ).fetchone()

    if not document:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    chunks = connection.execute(
        """
        SELECT content
        FROM document_chunks
        WHERE document_id = ?
        ORDER BY id
        """,
        (request.document_id,)
    ).fetchall()

    if not chunks:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="No study material found for this document."
        )

    context = "\n\n".join(
        row["content"]
        for row in chunks
    )

    # Load recent quiz questions so the AI can avoid repeating them.
    previous_quiz_rows = connection.execute(
        """
        SELECT questions
        FROM quizzes
        WHERE document_id = ?
        ORDER BY created_at DESC
        LIMIT 20
        """,
        (request.document_id,)
    ).fetchall()

    previous_questions = []

    for row in previous_quiz_rows:
        try:
            stored_questions = json.loads(row["questions"])

            if isinstance(stored_questions, list):
                for question in stored_questions:
                    if isinstance(question, dict):
                        question_text = question.get("question")

                        if question_text:
                            previous_questions.append(
                                question_text
                            )

        except (json.JSONDecodeError, TypeError):
            continue

    connection.close()

    try:
        quiz = generate_quiz(
            context=context,
            question_count=request.question_count,
            previous_questions=previous_questions,
            generation_nonce=str(uuid.uuid4())
        )

    except GeminiQuotaError as e:
        print(f"Gemini quota error: {e}")

        raise HTTPException(
            status_code=503,
            detail="Gemini API quota has been exhausted. Please try again after the quota resets."
        )

    except Exception as e:
        print(f"Quiz generation error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Failed to generate quiz."
        )

    if not quiz:
        raise HTTPException(
            status_code=500,
            detail="The AI did not generate any questions."
        )

    # Create a unique server-side quiz ID.
    quiz_id = str(uuid.uuid4())

    # Store the COMPLETE quiz server-side.
    # This includes correct answers and explanations.
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO quizzes (
            id,
            document_id,
            questions,
            user_id
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            quiz_id,
            document["id"],
            json.dumps(quiz),
            user["id"]
        )
    )

    connection.commit()
    connection.close()

    # Never send correct answers or explanations
    # to the browser before submission.
    public_quiz = []

    for question in quiz:
        public_quiz.append(
            {
                "question": question["question"],
                "options": question["options"],
                "topic": question["topic"]
            }
        )

    return {
        "status": "success",
        "quiz_id": quiz_id,
        "document_id": document["id"],
        "filename": document["filename"],
        "quiz": public_quiz
    }


@router.post("/submit")
def submit_quiz(
    request: QuizSubmitRequest,
    http_request: Request
):

    user = get_current_user(http_request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    connection = get_connection()

    try:
        # Start a transaction immediately so two simultaneous submissions
        # cannot both pass the one-time-submission check.
        connection.execute("BEGIN IMMEDIATE")

        quiz_row = connection.execute(
            """
            SELECT id, document_id, questions, submitted_at, user_id
            FROM quizzes
            WHERE id = ?
            """,
            (request.quiz_id,)
        ).fetchone()

        if not quiz_row:
            connection.rollback()

            raise HTTPException(
                status_code=404,
                detail="Quiz not found or expired."
            )

        # A quiz can only be submitted once.
        if quiz_row["user_id"] != user["id"]:

            raise HTTPException(
                status_code=403,
                detail="You are not allowed to submit this quize."
            )

        try:
            questions = json.loads(quiz_row["questions"])

        except (json.JSONDecodeError, TypeError):
            connection.rollback()

            raise HTTPException(
                status_code=500,
                detail="Stored quiz data is invalid."
            )

        if not isinstance(questions, list) or not questions:
            connection.rollback()

            raise HTTPException(
                status_code=500,
                detail="Stored quiz contains no questions."
            )

        # Convert submitted answers into a lookup table.
        submitted_answers = {}

        for answer in request.answers:

            if answer.question_index < 0:
                connection.rollback()

                raise HTTPException(
                    status_code=400,
                    detail="Invalid question index."
                )

            if answer.question_index >= len(questions):
                connection.rollback()

                raise HTTPException(
                    status_code=400,
                    detail="Invalid question index."
                )

            if answer.question_index in submitted_answers:
                connection.rollback()

                raise HTTPException(
                    status_code=400,
                    detail="Duplicate answer submitted for a question."
                )

            if answer.selected_answer is not None:

                options = questions[answer.question_index].get(
                    "options",
                    []
                )

                if (
                    answer.selected_answer < 0
                    or answer.selected_answer >= len(options)
                ):
                    connection.rollback()

                    raise HTTPException(
                        status_code=400,
                        detail="Invalid answer option."
                    )

            submitted_answers[answer.question_index] = (
                answer.selected_answer
            )

        score = 0
        results = []

        # Correct answers come ONLY from the server-stored quiz.
        for index, question in enumerate(questions):

            correct_answer = question["correct_answer"]

            selected_answer = submitted_answers.get(index)

            is_correct = (
                selected_answer is not None
                and selected_answer == correct_answer
            )

            if is_correct:
                score += 1

            results.append(
                {
                    "question_index": index,
                    "selected_answer": selected_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "explanation": question["explanation"],
                    "topic": question["topic"]
                }
            )

        total_questions = len(questions)

        percentage = round(
            (score / total_questions) * 100,
            2
        )

        # Mark this quiz as submitted BEFORE creating the attempt.
        # Because this is inside the same transaction, everything succeeds
        # together or everything rolls back.
        connection.execute(
            """
            UPDATE quizzes
            SET submitted_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND submitted_at IS NULL
            """,
            (request.quiz_id,)
        )

        # Store the quiz attempt.
        cursor = connection.execute(
    """
    INSERT INTO quiz_attempts (
        document_id,
        score,
        total_questions,
        percentage,
        user_id
    )
    VALUES (?, ?, ?, ?, ?)
    """,
    (
        quiz_row["document_id"],
        score,
        total_questions,
        percentage,
        user["id"]
    )
)

        attempt_id = cursor.lastrowid

        # Store every question result, including unanswered questions.
        for result in results:

            connection.execute(
                """
                INSERT INTO quiz_answers (
                    attempt_id,
                    question_index,
                    selected_answer,
                    correct_answer,
                    is_correct,
                    topic
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    result["question_index"],
                    result["selected_answer"],
                    result["correct_answer"],
                    int(result["is_correct"]),
                    result["topic"]
                )
            )

        connection.commit()

        return {
            "status": "success",
            "attempt_id": attempt_id,
            "quiz_id": request.quiz_id,
            "document_id": quiz_row["document_id"],
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "results": results
        }

    except HTTPException:
        raise

    except Exception as e:
        connection.rollback()
        print(f"Quiz submission error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Failed to submit quiz."
        )

    finally:
        connection.close()
