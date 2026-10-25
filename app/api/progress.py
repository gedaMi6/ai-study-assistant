import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.ai.llm import (
    generate_study_recommendation,
    generate_topic_review,
    generate_topic_detail,
    GeminiQuotaError,
)
from app.ai.vector_store import search_chunks
from app.database.database import get_connection


router = APIRouter(
    prefix="/progress",
    tags=["Progress"]
)


def _get_ai_study_focus(user_id: int, topic_rows):
    """
    Automatically identify the student's weakest topic and
    generate a consolidated review using material from all
    uploaded documents.
    """

    if not topic_rows:
        return None

    # Use the student's most recent quiz result for each topic when
    # choosing the current study focus. Lifetime averages can keep an
    # already-improved topic weak forever, even after a successful review.
    connection = get_connection()

    latest_topic_rows = connection.execute(
        """
        SELECT
            qa.topic,
            COUNT(*) AS questions_answered,
            SUM(qa.is_correct) AS correct_answers,
            ROUND(
                100.0 * SUM(qa.is_correct) / COUNT(*),
                1
            ) AS percentage
        FROM quiz_answers qa
        JOIN quiz_attempts att
            ON att.id = qa.attempt_id
        JOIN (
            SELECT
                qa2.topic,
                MAX(att2.id) AS latest_attempt_id
            FROM quiz_answers qa2
            JOIN quiz_attempts att2
                ON att2.id = qa2.attempt_id
            WHERE att2.user_id = ?
              AND qa2.topic IS NOT NULL
              AND TRIM(qa2.topic) != ''
            GROUP BY qa2.topic
        ) latest
            ON latest.latest_attempt_id = att.id
           AND latest.topic = qa.topic
        WHERE att.user_id = ?
        GROUP BY qa.topic
        ORDER BY percentage ASC
        """,
        (user_id, user_id)
    ).fetchall()

    # Only topics below the existing Strong threshold can become
    # the current AI study focus.
    unresolved_topics = [
        row
        for row in latest_topic_rows
        if float(row["percentage"] or 0) < 80
    ]

    connection.close()

    if not unresolved_topics:
        return None

    weakest = unresolved_topics[0]

    topic = str(
        weakest["topic"]
    ).strip()

    performance = float(
        weakest["percentage"] or 0
    )

    questions_answered = int(
        weakest["questions_answered"] or 0
    )

    correct_answers = int(
        weakest["correct_answers"] or 0
    )

    connection = get_connection()

    cached = connection.execute(
        """
        SELECT
            topic,
            performance,
            priority,
            reason,
            what_to_study,
            next_step,
            updated_at
        FROM study_recommendations
        WHERE user_id = ?
          AND topic = ?
        LIMIT 1
        """,
        (user_id, topic)
    ).fetchone()

    cached_review = connection.execute(
        """
        SELECT
            review,
            sources,
            performance,
            updated_at
        FROM study_topic_reviews
        WHERE user_id = ?
          AND topic = ?
        LIMIT 1
        """,
        (user_id, topic)
    ).fetchone()

    connection.close()

    priority = (
        "High"
        if performance < 60
        else "Medium"
        if performance < 80
        else "Low"
    )

    if cached and float(cached["performance"]) == performance:
        recommendation = {
            "topic": topic,
            "performance": performance,
            "priority": cached["priority"],
            "reason": cached["reason"],
            "what_to_study": json.loads(
                cached["what_to_study"]
            ),
            "next_step": cached["next_step"],
            "updated_at": cached["updated_at"]
        }
    else:
        recommendation = None

    review = None

    if (
        cached_review
        and float(cached_review["performance"]) == performance
    ):
        try:
            sources = json.loads(
                cached_review["sources"]
            )
        except Exception:
            sources = []

        review = {
            "review": cached_review["review"],
            "sources": sources,
            "updated_at": cached_review["updated_at"]
        }

    if recommendation and review:
        return {
            **recommendation,
            "review": review["review"],
            "review_sources": review["sources"],
            "review_updated_at": review["updated_at"]
        }

    try:
        results = search_chunks(
            topic,
            n_results=20
        )

        documents = results.get("documents") or [[]]
        metadatas = results.get("metadatas") or [[]]

        document_chunks = (
            documents[0]
            if documents and documents[0]
            else []
        )

        metadata_chunks = (
            metadatas[0]
            if metadatas and metadatas[0]
            else []
        )

        if not document_chunks:
            print(
                f"No study material found for topic: {topic}"
            )
            return recommendation

        study_material_parts = []
        source_documents = []

        # Map Chroma document IDs to human-readable filenames.
        connection = get_connection()

        document_rows = connection.execute(
            """
            SELECT id, filename
            FROM documents
            """
        ).fetchall()

        connection.close()

        document_names = {
            str(row["id"]): str(row["filename"])
            for row in document_rows
        }

        for index, document in enumerate(document_chunks):

            if not document:
                continue

            metadata = (
                metadata_chunks[index]
                if index < len(metadata_chunks)
                else {}
            )

            document_id = (
                metadata.get("document_id")
                if metadata
                else None
            )

            source_name = document_names.get(
                str(document_id),
                "Uploaded study material"
            )

            study_material_parts.append(
                f"SOURCE DOCUMENT: {source_name}\n"
                f"{str(document)}"
            )

            if source_name not in source_documents:
                source_documents.append(
                    source_name
                )

        study_material = "\n\n".join(
            study_material_parts
        )

        if not study_material.strip():
            return recommendation

        if recommendation is None:
            try:
                generated = generate_study_recommendation(
                    topic=topic,
                    performance=performance,
                    study_material=study_material,
                    question_count=questions_answered,
                    correct_count=correct_answers
                )

                recommendation_priority = priority

                connection = get_connection()

                connection.execute(
                    """
                    DELETE FROM study_recommendations
                    WHERE user_id = ?
                      AND topic = ?
                    """,
                    (user_id, topic)
                )

                connection.execute(
                    """
                    INSERT INTO study_recommendations (
                        user_id,
                        topic,
                        performance,
                        priority,
                        reason,
                        what_to_study,
                        next_step
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        topic,
                        performance,
                        recommendation_priority,
                        generated["reason"],
                        json.dumps(
                            generated["what_to_study"]
                        ),
                        generated["next_step"]
                    )
                )

                connection.commit()

                saved = connection.execute(
                    """
                    SELECT
                        topic,
                        performance,
                        priority,
                        reason,
                        what_to_study,
                        next_step,
                        updated_at
                    FROM study_recommendations
                    WHERE user_id = ?
                      AND topic = ?
                    LIMIT 1
                    """,
                    (user_id, topic)
                ).fetchone()

                connection.close()

                recommendation = {
                    "topic": saved["topic"],
                    "performance": float(
                        saved["performance"]
                    ),
                    "priority": saved["priority"],
                    "reason": saved["reason"],
                    "what_to_study": json.loads(
                        saved["what_to_study"]
                    ),
                    "next_step": saved["next_step"],
                    "updated_at": saved["updated_at"]
                }

            except GeminiQuotaError:
                print(
                    "AI quota unavailable while generating "
                    "study recommendation."
                )

            except Exception as e:
                print(
                    f"AI study recommendation generation failed: {e}"
                )

        if cached_review is None or float(
            cached_review["performance"]
        ) != performance:

            try:
                generated_review = generate_topic_review(
                    topic=topic,
                    performance=performance,
                    study_material=study_material
                )

                connection = get_connection()

                connection.execute(
                    """
                    INSERT INTO study_topic_reviews (
                        user_id,
                        topic,
                        performance,
                        review,
                        sources
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, topic)
                    DO UPDATE SET
                        performance = excluded.performance,
                        review = excluded.review,
                        sources = excluded.sources,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        user_id,
                        topic,
                        performance,
                        generated_review,
                        json.dumps(source_documents)
                    )
                )

                connection.commit()
                connection.close()

                review = {
                    "review": generated_review,
                    "sources": source_documents,
                    "updated_at": None
                }

            except GeminiQuotaError:
                print(
                    "AI quota unavailable while generating "
                    "topic review."
                )

            except Exception as e:
                print(
                    f"AI topic review generation failed: {e}"
                )

    except Exception as e:
        print(
            f"AI study focus retrieval failed: {e}"
        )

    if not recommendation and cached:
        try:
            recommendation = {
                "topic": cached["topic"],
                "performance": float(
                    cached["performance"]
                ),
                "priority": cached["priority"],
                "reason": cached["reason"],
                "what_to_study": json.loads(
                    cached["what_to_study"]
                ),
                "next_step": cached["next_step"],
                "updated_at": cached["updated_at"]
            }
        except Exception:
            recommendation = None

    if not recommendation and not review:
        return None

    return {
        **(
            recommendation
            or {
                "topic": topic,
                "performance": performance,
                "priority": priority,
                "reason": (
                    f"You scored {performance:.1f}% "
                    f"on this topic."
                ),
                "what_to_study": [],
                "next_step": (
                    "Review the material below."
                ),
                "updated_at": None
            }
        ),
        "review": (
            review["review"]
            if review
            else None
        ),
        "review_sources": (
            review["sources"]
            if review
            else []
        ),
        "review_updated_at": (
            review["updated_at"]
            if review
            else None
        )
    }


class TopicDetailRequest(BaseModel):
    topic: str
    study_point: str


@router.post("/topic-detail")
def get_topic_detail(
    payload: TopicDetailRequest,
    request: Request
):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    topic = payload.topic.strip()
    study_point = payload.study_point.strip()

    if not topic or not study_point:
        raise HTTPException(
            status_code=400,
            detail="Topic and study point are required."
        )

    connection = get_connection()

    document_row = connection.execute(
        """
        SELECT
            att.document_id
        FROM quiz_answers qa
        JOIN quiz_attempts att
            ON att.id = qa.attempt_id
        WHERE att.user_id = ?
          AND qa.topic = ?
        ORDER BY att.created_at DESC
        LIMIT 1
        """,
        (user["id"], topic)
    ).fetchone()

    connection.close()

    if not document_row:
        raise HTTPException(
            status_code=404,
            detail="No study document was found for this topic."
        )

    document_id = document_row["document_id"]

    try:
        results = search_chunks(
            study_point,
            n_results=6,
            document_id=document_id
        )

        documents = results.get("documents") or []

        if not documents or not documents[0]:
            raise HTTPException(
                status_code=404,
                detail="No relevant study material was found."
            )

        study_material = "\n\n".join(
            str(document)
            for document in documents[0]
            if document
        )

        if not study_material.strip():
            raise HTTPException(
                status_code=404,
                detail="No relevant study material was found."
            )

        detail = generate_topic_detail(
            topic=topic,
            study_point=study_point,
            context=study_material
        )

        return {
            "status": "success",
            "topic": topic,
            "study_point": study_point,
            "detail": detail,
            "document_id": document_id
        }

    except GeminiQuotaError:
        raise HTTPException(
            status_code=503,
            detail="AI quota is temporarily unavailable."
        )

    except HTTPException:
        raise

    except Exception as e:
        print(
            f"Topic detail generation failed: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to generate topic detail."
        )


@router.get("")
def get_progress(request: Request):

    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    user_id = user["id"]

    connection = get_connection()

    overall = connection.execute(
        """
        SELECT
            COUNT(*) AS total_attempts,
            COALESCE(AVG(percentage), 0) AS average_percentage,
            COALESCE(SUM(score), 0) AS total_correct,
            COALESCE(SUM(total_questions), 0) AS total_questions
        FROM quiz_attempts
        WHERE user_id = ?
        """
        ,
        (user_id,)
    ).fetchone()

    topic_rows = connection.execute(
        """
        SELECT
            qa.topic,
            COUNT(*) AS questions_answered,
            SUM(qa.is_correct) AS correct_answers,
            ROUND(
                100.0 * SUM(qa.is_correct) / COUNT(*),
                1
            ) AS percentage
        FROM quiz_answers qa
        JOIN quiz_attempts att
            ON att.id = qa.attempt_id
        WHERE att.user_id = ?
          AND qa.topic IS NOT NULL
          AND TRIM(qa.topic) != ''
        GROUP BY qa.topic
        ORDER BY percentage ASC
        """,
        (user_id,)
    ).fetchall()

    topics = []
    weak_topics = []
    recommendations = []

    for row in topic_rows:

        percentage = float(
            row["percentage"] or 0
        )

        if percentage < 60:
            level = "Weak"
            status = "weak"

            weak_topics.append(
                row["topic"]
            )

            recommendations.append(
                f"Review {row['topic']} and take "
                f"another quiz focused on this topic."
            )

        elif percentage < 80:
            level = "Developing"
            status = "developing"

            recommendations.append(
                f"Practice {row['topic']} again "
                f"to improve your understanding."
            )

        else:
            level = "Strong"
            status = "strong"

        # Calculate improvement from the previous attempt
        # for this topic.
        topic_attempts = connection.execute(
            """
            SELECT
                att.id,
                ROUND(
                    100.0 * SUM(qa.is_correct) / COUNT(*),
                    1
                ) AS percentage
            FROM quiz_answers qa
            JOIN quiz_attempts att
                ON att.id = qa.attempt_id
            WHERE att.user_id = ?
              AND qa.topic = ?
            GROUP BY att.id
            ORDER BY att.id DESC
            LIMIT 2
            """,
            (user_id, row["topic"])
        ).fetchall()

        previous_percentage = None
        improvement = None
        trend = "new"

        if len(topic_attempts) >= 2:

            current_percentage = float(
                topic_attempts[0]["percentage"] or 0
            )

            previous_percentage = float(
                topic_attempts[1]["percentage"] or 0
            )

            improvement = round(
                current_percentage - previous_percentage,
                1
            )

            if improvement > 0:
                trend = "improving"
            elif improvement < 0:
                trend = "declining"
            else:
                trend = "stable"

        topics.append(
            {
                "topic": row["topic"],
                "questions_answered": row["questions_answered"],
                "correct_answers": row["correct_answers"],
                "percentage": percentage,
                "previous_percentage": previous_percentage,
                "improvement": improvement,
                "trend": trend,
                "level": level,
                "status": status
            }
        )

    connection.close()

    study_focus = _get_ai_study_focus(
        user_id,
        topic_rows
    )

    return {
        "status": "success",

        "overall": {
            "total_attempts": overall["total_attempts"],
            "average_percentage": round(
                float(
                    overall["average_percentage"] or 0
                ),
                1
            ),
            "total_correct": overall["total_correct"],
            "total_questions": overall["total_questions"]
        },

        "topics": topics,

        "weak_topics": weak_topics,

        "recommendations": recommendations,

        "study_focus": study_focus
    }


@router.get("/grades")
def get_released_grades(request: Request):

    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    if user["role"] != "student":
        raise HTTPException(
            status_code=403,
            detail="Student access required."
        )

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                a.id AS attempt_id,
                a.test_id AS exam_id,
                t.title AS exam_title,
                a.score,
                a.total_questions,
                a.percentage,
                a.submitted_at
            FROM teacher_test_attempts a
            INNER JOIN teacher_tests t
                ON t.id = a.test_id
            WHERE a.student_id = ?
              AND COALESCE(a.score_released, 0) = 1
            ORDER BY a.submitted_at DESC
            """,
            (user["id"],)
        ).fetchall()

        grades = [
            {
                "attempt_id": row["attempt_id"],
                "exam_id": row["exam_id"],
                "exam_title": row["exam_title"],
                "score": row["score"],
                "total_questions": row["total_questions"],
                "percentage": float(row["percentage"] or 0),
                "submitted_at": row["submitted_at"]
            }
            for row in rows
        ]

        return {
            "status": "success",
            "grades": grades
        }

    finally:
        connection.close()
