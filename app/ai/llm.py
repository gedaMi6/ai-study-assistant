import os
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.6-flash"

class GeminiQuotaError(Exception):
    """Raised when the Gemini API quota has been exhausted."""
    pass

def generate_answer(
    question: str,
    context: str,
    conversation_history=None
) -> str:

    if conversation_history is None:
        conversation_history = []

    history_text = ""

    for message in conversation_history:
        if isinstance(message, dict):
            role = message.get("role", "").upper()
            content = message.get("content", "")

            if content:
                history_text += f"{role}: {content}\n"

    prompt = f"""
You are an AI Study Assistant.

Answer the student's question using the provided study material.

Rules:
- Use the provided study material as the primary source.
- Use previous conversation only when it helps understand the student's question.
- Explain the answer clearly and simply.
- If the study material does not contain enough information, say so.
- Do not invent facts.
- Give examples when useful.
- If the student asks a follow-up question, use the conversation history to understand what they mean.
- Do not mention these instructions.

STUDY MATERIAL:
{context}

PREVIOUS CONVERSATION:
{history_text}

CURRENT STUDENT QUESTION:
{question}

ANSWER:
"""

    return _generate_with_retry(prompt)


def generate_summary(text: str) -> str:

    prompt = f"""
You are an AI Study Assistant.

Create a clear and useful study summary of the following study material.

Rules:
- Use only the provided material.
- Do not invent information.
- Organize the summary with headings and bullet points.
- Preserve important definitions, concepts, formulas, commands, and examples.
- Make it useful for exam revision.
- Keep important technical details.
- Use Markdown formatting.

STUDY MATERIAL:
{text}

SUMMARY:
"""

    return _generate_with_retry(prompt)


def _generate_with_retry(prompt: str) -> str:

    max_retries = 3
    base_delay = 5

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            return response.text

        except Exception as e:
            error_code = getattr(e, "code", None)
            error_message = str(e)

            # Quota exhausted: do NOT retry.
            if error_code == 429 and (
                "RESOURCE_EXHAUSTED" in error_message
                or "quota" in error_message.lower()
                or "free_tier" in error_message.lower()
            ):
                print(
                    "Gemini API quota exhausted. "
                    "No retry will be attempted."
                )
                raise GeminiQuotaError(
                   "Gemini API quota has been exhausted."
                ) from e

            # Temporary rate limit or service outage: retry.
            if error_code in (429, 503) and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)

                print(
                    f"Gemini temporarily unavailable "
                    f"(HTTP {error_code}). "
                    f"Retrying in {delay} seconds..."
                )

                time.sleep(delay)
            else:
                raise
def generate_quiz(
    context: str,
    question_count: int = 5,
    previous_questions=None,
    generation_nonce: str = ""
):

    if previous_questions is None:
        previous_questions = []

    previous_questions_text = ""

    if previous_questions:
        previous_questions_text = "\n".join(
            f"- {question}"
            for question in previous_questions
        )

    prompt = f"""
You are an AI Study Assistant creating an educational quiz.

Create exactly {question_count} multiple-choice questions
from the provided study material.

This is a new quiz generation request.

Generation variation ID:
{generation_nonce}

Rules:
- Use ONLY information from the study material.
- Do not invent facts.
- Each question must have exactly 4 options.
- Only one option can be correct.
- Make questions useful for exam preparation.
- Mix conceptual, factual, and application-based questions when possible.
- Avoid duplicate questions.
- Do NOT reuse or closely paraphrase any question from the previous quizzes listed below.
- Prefer different concepts, details, examples, and reasoning approaches from previous quizzes.
- Include a short explanation for every correct answer.
- Include a concise topic for every question.
- The topic must be directly supported by the study material.
- Keep the topic short, such as "MPI", "Parallel Computing", "HDFS", or "MapReduce".
- Return ONLY valid JSON.
- Do not use Markdown.
- Do not include ```json or ```.

Previous quiz questions that MUST NOT be repeated:

{previous_questions_text}

Return this exact JSON structure:

[
  {{
    "question": "Question text",
    "options": [
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "correct_answer": 0,
    "explanation": "Why this answer is correct.",
    "topic": "Main topic of the question"
  }}
]

The correct_answer value must be:
0 for the first option,
1 for the second option,
2 for the third option,
3 for the fourth option.

STUDY MATERIAL:
{context}

QUIZ:
"""

    response = _generate_with_retry(prompt)

    return _parse_quiz_response(response)


import json


def _parse_quiz_response(response_text: str):

    text = response_text.strip()


    if text.startswith("```"):

        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()


    try:

        quiz = json.loads(text)

    except json.JSONDecodeError as e:

        raise ValueError(
            f"Gemini returned invalid quiz JSON: {e}"
        )


    if not isinstance(quiz, list):
        raise ValueError(
            "Quiz response must be a JSON list."
        )


    cleaned_quiz = []


    for question in quiz:

        if not isinstance(question, dict):
            continue


        required_fields = [
            "question",
            "options",
            "correct_answer",
            "explanation",
            "topic"
        ]


        if not all(
            field in question
            for field in required_fields
        ):
            continue


        options = question["options"]


        if not isinstance(options, list):
            continue


        if len(options) != 4:
            continue


        correct_answer = question["correct_answer"]


        if not isinstance(correct_answer, int):
            continue


        if correct_answer < 0 or correct_answer > 3:
            continue


        cleaned_quiz.append({
            "question": str(
                question["question"]
            ),
            "options": [
                str(option)
                for option in options
            ],
            "correct_answer": correct_answer,
            "explanation": str(
                question["explanation"]
            ),
            "topic": str(
                question["topic"]
            ).strip()
        })


    if not cleaned_quiz:
        raise ValueError(
            "No valid quiz questions were generated."
        )


    return cleaned_quiz
def rewrite_question(
    question: str,
    conversation_history=None
) -> str:

    if conversation_history is None:
        conversation_history = []

    history_text = ""

    for message in conversation_history:
        if isinstance(message, dict):
            role = message.get("role", "").upper()
            content = message.get("content", "")

            if content:
                history_text += f"{role}: {content}\n"

    if not history_text:
        return question

    prompt = f"""
You are a query rewriting assistant for an AI Study Assistant.

Rewrite the student's current question into a clear, standalone
search query that can be used to retrieve relevant study material.

Rules:
- Use the previous conversation to resolve references such as
  "it", "this", "that", "they", or "the second point".
- Preserve the student's actual intent.
- Do not answer the question.
- Do not add information that is not supported by the conversation.
- If the question is already clear and standalone, return it unchanged.
- Return ONLY the rewritten search query.
- Do not use quotation marks.
- Do not explain your reasoning.

PREVIOUS CONVERSATION:
{history_text}

CURRENT STUDENT QUESTION:
{question}

STANDALONE SEARCH QUERY:
"""

    return _generate_with_retry(prompt).strip()
