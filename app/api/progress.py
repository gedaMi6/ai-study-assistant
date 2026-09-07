from fastapi import APIRouter, HTTPException, Request

from app.api.auth import get_current_user
from app.database.database import get_connection


router = APIRouter(
    prefix="/progress",
    tags=["Progress"]
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
        """,
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

    connection.close()

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

        topics.append(
            {
                "topic": row["topic"],
                "questions_answered": row["questions_answered"],
                "correct_answers": row["correct_answers"],
                "percentage": percentage,
                "level": level,
                "status": status
            }
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

        "recommendations": recommendations
    }
