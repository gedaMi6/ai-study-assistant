from fastapi import APIRouter, Request

from app.api.teacher_tasks import require_teacher
from app.database.database import get_connection


router = APIRouter(
    prefix="/api/teacher/student-status",
    tags=["Teacher Student Status"]
)


def get_status(average: float, attempts: int) -> tuple[str, str]:
    if attempts == 0:
        return "No Activity", "No quiz or exam activity yet."

    if average < 60:
        return "Needs Help", "Performance is below 60%."

    if average < 70:
        return "At Risk", "Performance is below the 70% target."

    if average < 85:
        return "Performing Well", "Performance is steady but has room to improve."

    return "Excellent", "Consistently strong quiz performance."


@router.get("")
def get_student_status(request: Request):
    require_teacher(request)

    connection = get_connection()

    try:
        students = connection.execute(
            """
            SELECT
                u.id,
                u.name,
                u.email,

                (
                    SELECT COUNT(*)
                    FROM quiz_attempts qa
                    WHERE qa.user_id = u.id
                ) AS quiz_attempts,

                (
                    SELECT COALESCE(AVG(qa.percentage), 0)
                    FROM quiz_attempts qa
                    WHERE qa.user_id = u.id
                ) AS quiz_average,

                (
                    SELECT COUNT(*)
                    FROM teacher_test_attempts ta
                    WHERE ta.student_id = u.id
                      AND ta.score_released = 1
                ) AS exam_attempts,

                (
                    SELECT COALESCE(AVG(ta.percentage), 0)
                    FROM teacher_test_attempts ta
                    WHERE ta.student_id = u.id
                      AND ta.score_released = 1
                ) AS exam_average,

                (
                    SELECT MAX(qa.created_at)
                    FROM quiz_attempts qa
                    WHERE qa.user_id = u.id
                ) AS last_quiz,

                (
                    SELECT MAX(ta.submitted_at)
                    FROM teacher_test_attempts ta
                    WHERE ta.student_id = u.id
                      AND ta.score_released = 1
                ) AS last_exam

            FROM users u
            WHERE u.role = 'student'
            ORDER BY u.name ASC
            """
        ).fetchall()

        results = []

        for student in students:
            student_id = student["id"]

            quiz_attempts = int(student["quiz_attempts"] or 0)
            exam_attempts = int(student["exam_attempts"] or 0)

            total_attempts = quiz_attempts + exam_attempts

            quiz_average = float(student["quiz_average"] or 0)
            exam_average = float(student["exam_average"] or 0)

            if total_attempts:
                average = (
                    (
                        quiz_average * quiz_attempts
                        + exam_average * exam_attempts
                    )
                    / total_attempts
                )
            else:
                average = 0.0

            average = round(average, 1)

            status, reason = get_status(
                average,
                total_attempts
            )

            topic_rows = connection.execute(
                """
                SELECT
                    qa.topic,
                    ROUND(
                        100.0 * SUM(qa.is_correct) / COUNT(*),
                        1
                    ) AS percentage
                FROM quiz_answers qa
                JOIN quiz_attempts q
                    ON q.id = qa.attempt_id
                WHERE q.user_id = ?
                  AND qa.topic IS NOT NULL
                  AND TRIM(qa.topic) != ''
                GROUP BY qa.topic
                ORDER BY percentage ASC
                LIMIT 3
                """,
                (student_id,)
            ).fetchall()

            weak_topics = [
                {
                    "topic": row["topic"],
                    "percentage": float(
                        row["percentage"] or 0
                    )
                }
                for row in topic_rows
                if float(row["percentage"] or 0) < 70
            ]

            if weak_topics:
                reason = (
                    "Weak performance in "
                    + ", ".join(
                        topic["topic"]
                        for topic in weak_topics
                    )
                    + "."
                )

            last_quiz = student["last_quiz"]
            last_exam = student["last_exam"]

            quiz_history = connection.execute(
                """
                SELECT
                    percentage,
                    created_at AS completed_at,
                    'Quiz' AS activity_type
                FROM quiz_attempts
                WHERE user_id = ?
                """,
                (student_id,)
            ).fetchall()

            exam_history = connection.execute(
                """
                SELECT
                    percentage,
                    submitted_at AS completed_at,
                    'Exam' AS activity_type
                FROM teacher_test_attempts
                WHERE student_id = ?
                  AND score_released = 1
                """,
                (student_id,)
            ).fetchall()

            performance_history = [
                {
                    "percentage": round(
                        float(row["percentage"] or 0),
                        1
                    ),
                    "completed_at": row["completed_at"],
                    "activity_type": row["activity_type"]
                }
                for row in list(quiz_history) + list(exam_history)
            ]

            performance_history.sort(
                key=lambda item: str(
                    item["completed_at"] or ""
                )
            )

            performance_history = performance_history[-5:]

            if len(performance_history) < 2:
                trend = "No Data"
                trend_change = 0.0
            else:
                first_score = performance_history[0]["percentage"]
                latest_score = performance_history[-1]["percentage"]
                trend_change = round(
                    latest_score - first_score,
                    1
                )

                if trend_change >= 10:
                    trend = "Improving"
                elif trend_change <= -10:
                    trend = "Declining"
                else:
                    trend = "Stable"

            if last_quiz and last_exam:
                last_activity = max(
                    str(last_quiz),
                    str(last_exam)
                )
            else:
                last_activity = last_quiz or last_exam

            results.append(
                {
                    "id": student_id,
                    "name": student["name"],
                    "email": student["email"],
                    "quiz_attempts": quiz_attempts,
                    "exam_attempts": exam_attempts,
                    "total_attempts": total_attempts,
                    "quiz_average": round(quiz_average, 1),
                    "exam_average": round(exam_average, 1),
                    "average_score": average,
                    "last_quiz": last_quiz,
                    "last_exam": last_exam,
                    "last_activity": last_activity,
                    "performance_history": performance_history,
                    "trend": trend,
                    "trend_change": trend_change,
                    "status": status,
                    "reason": reason,
                    "weak_topics": weak_topics
                }
            )

        results.sort(
            key=lambda student: (
                student["status"] == "No Activity",
                student["average_score"],
                student["name"].lower()
            )
        )

        summary = {
            "total": len(results),
            "needs_help": sum(
                1 for student in results
                if student["status"] == "Needs Help"
            ),
            "at_risk": sum(
                1 for student in results
                if student["status"] == "At Risk"
            ),
            "performing_well": sum(
                1 for student in results
                if student["status"] == "Performing Well"
            ),
            "excellent": sum(
                1 for student in results
                if student["status"] == "Excellent"
            ),
            "no_activity": sum(
                1 for student in results
                if student["status"] == "No Activity"
            )
        }

        return {
            "status": "success",
            "summary": summary,
            "students": results
        }

    finally:
        connection.close()
