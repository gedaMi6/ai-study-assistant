from app.database.database import get_connection


def get_student_performance(user_id: int) -> dict:
    """
    Collect quiz performance for one authenticated student.

    Only quiz attempts belonging to the supplied user_id
    are included.
    """

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

    recent_attempts = connection.execute(
        """
        SELECT
            id,
            document_id,
            score,
            total_questions,
            percentage,
            created_at
        FROM quiz_attempts
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    topics = []

    for row in topic_rows:
        percentage = float(row["percentage"] or 0)

        if percentage < 60:
            level = "Weak"
        elif percentage < 80:
            level = "Developing"
        else:
            level = "Strong"

        topics.append(
            {
                "topic": row["topic"],
                "questions_answered": row["questions_answered"],
                "correct_answers": row["correct_answers"],
                "percentage": percentage,
                "level": level,
            }
        )

    attempts = [
        {
            "id": row["id"],
            "document_id": row["document_id"],
            "score": row["score"],
            "total_questions": row["total_questions"],
            "percentage": float(row["percentage"]),
            "created_at": row["created_at"],
        }
        for row in recent_attempts
    ]

    weak_topics = [
        topic["topic"]
        for topic in topics
        if topic["level"] == "Weak"
    ]

    developing_topics = [
        topic["topic"]
        for topic in topics
        if topic["level"] == "Developing"
    ]

    strong_topics = [
        topic["topic"]
        for topic in topics
        if topic["level"] == "Strong"
    ]

    return {
        "overall": {
            "total_attempts": overall["total_attempts"],
            "average_percentage": round(
                float(overall["average_percentage"] or 0),
                1
            ),
            "total_correct": overall["total_correct"],
            "total_questions": overall["total_questions"],
        },
        "topics": topics,
        "weak_topics": weak_topics,
        "developing_topics": developing_topics,
        "strong_topics": strong_topics,
        "recent_attempts": attempts,
    }


def build_coach_context(user_id: int) -> str:
    """
    Convert the student's performance into concise
    context that can later be given to Gemini.
    """

    performance = get_student_performance(user_id)

    overall = performance["overall"]

    context = f"""
STUDENT PERFORMANCE

Total quiz attempts:
{overall["total_attempts"]}

Average score:
{overall["average_percentage"]}%

Questions answered correctly:
{overall["total_correct"]}

Total questions:
{overall["total_questions"]}

WEAK TOPICS:
{", ".join(performance["weak_topics"]) or "None yet"}

DEVELOPING TOPICS:
{", ".join(performance["developing_topics"]) or "None yet"}

STRONG TOPICS:
{", ".join(performance["strong_topics"]) or "None yet"}

TOPIC PERFORMANCE:
"""

    for topic in performance["topics"]:
        context += (
            f"- {topic['topic']}: "
            f"{topic['percentage']}% "
            f"({topic['level']})\n"
        )

    context += "\nRECENT QUIZ ATTEMPTS:\n"

    for attempt in performance["recent_attempts"]:
        context += (
            f"- {attempt['percentage']}% "
            f"({attempt['score']}/{attempt['total_questions']}) "
            f"on {attempt['created_at']}\n"
        )

    return context.strip()
