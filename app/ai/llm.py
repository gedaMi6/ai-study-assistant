import os
import time
import threading

from dotenv import load_dotenv
from google import genai

load_dotenv()

# Load up to 10 Gemini API keys.
# KEY 1 is used first. When Gemini reports quota exhaustion,
# the app automatically moves to the next available key.
API_KEYS = [
    os.getenv(f"GEMINI_API_KEY_{i}")
    for i in range(1, 11)
]

# Backward compatibility: if only GEMINI_API_KEY exists,
# use it as key 1.
if not API_KEYS[0]:
    API_KEYS[0] = os.getenv("GEMINI_API_KEY")

API_KEYS = [key for key in API_KEYS if key]

if not API_KEYS:
    raise RuntimeError("No GEMINI API keys are configured")

_clients = [
    genai.Client(api_key=key)
    for key in API_KEYS
]

_current_key_index = 0
_key_lock = threading.Lock()

MODEL_NAME = "gemini-3.6-flash"


class GeminiQuotaError(Exception):
    """Raised when all configured Gemini API keys are exhausted."""
    pass


def _get_current_client():
    with _key_lock:
        return _clients[_current_key_index]


def _switch_to_next_key():
    global _current_key_index

    with _key_lock:
        if _current_key_index >= len(_clients) - 1:
            return False

        _current_key_index += 1

        print(
            f"Gemini API key quota exhausted. "
            f"Switching to API key "
            f"{_current_key_index + 1}/{len(_clients)}."
        )

        return True

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
You are KANIA.AI.

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
You are KANIA.AI.

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
    """Generate content with automatic Gemini API key rotation."""

    max_retries = 3
    base_delay = 5

    for attempt in range(max_retries):
        try:
            current_client = _get_current_client()

            response = current_client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            return response.text

        except Exception as e:
            error_code = getattr(e, "code", None)
            error_message = str(e)

            # Quota exhausted: switch to the next API key.
            if error_code == 429 and (
                "RESOURCE_EXHAUSTED" in error_message
                or "quota" in error_message.lower()
                or "free_tier" in error_message.lower()
            ):
                switched = _switch_to_next_key()

                if switched:
                    print("Retrying request with the next Gemini API key.")
                    continue

                print(
                    "Gemini API quota exhausted on all configured API keys."
                )

                raise GeminiQuotaError(
                    "Gemini API quota has been exhausted on all configured API keys."
                ) from e

            # Temporary Gemini service outage:
            # try another configured key first, then retry with backoff.
            if error_code == 503:
                switched = _switch_to_next_key()

                if switched:
                    print(
                        "Gemini temporarily unavailable. "
                        "Switching to the next API key."
                    )
                    continue

                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)

                    print(
                        f"Gemini temporarily unavailable (HTTP {error_code}). "
                        f"Retrying in {delay} seconds..."
                    )

                    time.sleep(delay)
                    continue

            raise

def generate_quiz(
    context: str,
    question_count: int = 5,
    previous_questions=None,
    generation_nonce: str = "",
    focus_topic: str | None = None
):

    if previous_questions is None:
        previous_questions = []

    previous_questions_text = ""

    if previous_questions:
        previous_questions_text = "\n".join(
            f"- {question}"
            for question in previous_questions
        )

    focus_topic_instruction = ""

    if focus_topic:
        focus_topic_instruction = f"""
FOCUS TOPIC:
{focus_topic}

This quiz is specifically for practicing the student's weak topic.

Rules for the focus topic:
- Generate ALL questions primarily about the focus topic.
- Use related concepts from the study material when they help explain or test the focus topic.
- Do not generate questions mainly about unrelated topics.
- Make sure every question is directly supported by the provided study material.
"""

    prompt = f"""
You are KANIA.AI creating an educational quiz.

Create exactly {question_count} multiple-choice questions
from the provided study material.

{focus_topic_instruction}

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

def generate_study_recommendation(
    topic: str,
    performance: float,
    study_material: str,
    question_count: int = 0,
    correct_count: int = 0
):
    """
    Generate a personalized, study-material-grounded recommendation
    for the student's weakest topic.
    """

    prompt = f"""
You are KANIA.AI helping a student improve their exam performance.

The student needs help with this topic:

TOPIC:
{topic}

CURRENT PERFORMANCE:
{performance}%

QUESTIONS ANSWERED:
{question_count}

CORRECT ANSWERS:
{correct_count}

Use ONLY the provided study material.

Your job is to create a practical study recommendation for this topic.

Rules:
- Base the recommendation directly on the study material.
- Do not invent facts or concepts that are not present in the material.
- Identify the most important concepts the student should review.
- Focus on the student's weakness, not topics they already perform well on.
- Give 3 to 5 specific things to study.
- Give a clear reason why this topic should be the student's current focus.
- Give one practical next step.
- Keep the language clear and appropriate for a university student.
- Do not give generic motivational advice.
- Return ONLY valid JSON.
- Do not use Markdown.
- Do not include ```json or ```.

Return exactly this structure:

{{
  "topic": "{topic}",
  "performance": {performance},
  "priority": "High",
  "reason": "A short explanation of why this topic should currently be the student's focus.",
  "what_to_study": [
    "Specific concept to review",
    "Specific concept to review",
    "Specific concept to review"
  ],
  "next_step": "A clear action the student should take next."
}}

STUDY MATERIAL:
{study_material}

RECOMMENDATION:
"""

    response = _generate_with_retry(prompt)

    return _parse_study_recommendation(response)


def _parse_study_recommendation(response_text: str):
    text = response_text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        recommendation = json.loads(text)

    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini returned invalid recommendation JSON: {e}"
        )

    if not isinstance(recommendation, dict):
        raise ValueError(
            "Study recommendation response must be a JSON object."
        )

    required_fields = [
        "topic",
        "performance",
        "priority",
        "reason",
        "what_to_study",
        "next_step"
    ]

    if not all(
        field in recommendation
        for field in required_fields
    ):
        raise ValueError(
            "Study recommendation is missing required fields."
        )

    what_to_study = recommendation["what_to_study"]

    if not isinstance(what_to_study, list):
        raise ValueError(
            "what_to_study must be a list."
        )

    what_to_study = [
        str(item).strip()
        for item in what_to_study
        if str(item).strip()
    ]

    if not what_to_study:
        raise ValueError(
            "Study recommendation contains no study topics."
        )

    try:
        parsed_performance = float(
            recommendation["performance"]
        )
    except (TypeError, ValueError):
        raise ValueError(
            "Study recommendation contains invalid performance."
        )

    return {
        "topic": str(
            recommendation["topic"]
        ).strip(),

        "performance": parsed_performance,

        "priority": str(
            recommendation["priority"]
        ).strip(),

        "reason": str(
            recommendation["reason"]
        ).strip(),

        "what_to_study": what_to_study,

        "next_step": str(
            recommendation["next_step"]
        ).strip()
    }

def generate_topic_review(
    topic: str,
    performance: float,
    study_material: str
):
    """
    Generate a complete review for a weak topic using
    material retrieved from all relevant uploaded documents.
    """

    prompt = f"""
You are KANIA.AI helping a university student
review a topic they are struggling with.

WEAK TOPIC:
{topic}

STUDENT PERFORMANCE:
{performance}%

The study material below was retrieved from the student's
uploaded documents. It may contain material from multiple
documents.

STUDY MATERIAL:
{study_material}

Create a complete, structured study review for the student.

Requirements:

- Use ONLY the supplied study material.
- Do not use outside knowledge.
- Do not invent facts, numbers, examples, definitions,
  terminology, or explanations.
- Explain the topic from the beginning as if the student
  is weak in this area.
- Cover all important concepts from the retrieved material
  that relate to the weak topic.
- Combine overlapping information instead of repeating it.
- Clearly explain important terms.
- Include comparisons when the material contains comparisons.
- Include examples only when supported by the material.
- Highlight important facts the student should remember.
- Point out relationships between related concepts.
- Organize the review into clear sections.
- End with a short "What to remember" section.
- End with a practical "Next step" for studying this topic.
- If the retrieved material is insufficient, explicitly say so.

Return only the study review.
"""

    return _generate_with_retry(prompt)


def generate_topic_detail(
    topic: str,
    study_point: str,
    context: str
):
    """
    Explain a selected study topic using only the supplied
    uploaded-document context.
    """

    prompt = f"""
You are KANIA.AI.

The student selected this topic:
{topic}

The specific study point they want to understand is:
{study_point}

Use ONLY the study material provided below.

STUDY MATERIAL:
{context}

Explain the selected study point clearly for a university student.

Requirements:
- Stay strictly grounded in the study material.
- Define important concepts mentioned in the material.
- If the topic involves a comparison, clearly compare the concepts.
- Use simple examples only when they are supported by the material.
- Do not invent facts, numbers, specifications, examples, or terminology.
- Do not rely on outside knowledge.
- If the material does not contain enough information, explicitly say that.
- Organize the explanation with short paragraphs and bullet points when useful.
- Focus specifically on what the student selected, not unrelated topics.

Return only the explanation.
"""

    return _generate_with_retry(prompt)


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
You are a query rewriting assistant for KANIA.AI.

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


def generate_flashcards(
    context: str,
    card_count: int = 10,
    focus_topic: str | None = None,
) -> list[dict]:
    """Generate validated question-and-answer flashcards from study material."""
    import json

    card_count = max(1, min(int(card_count), 30))

    topic_instruction = ""
    if focus_topic:
        topic_instruction = f"""
Focus primarily on this topic: {focus_topic}
Every card must remain grounded in the supplied study material.
"""

    prompt = f"""
You are KANIA.AI, an educational flashcard generator.

Create exactly {card_count} useful flashcards from the study material.

{topic_instruction}

Rules:
- Use only facts supported by the supplied study material.
- Each question must test one clear concept.
- Answers must be accurate, concise, and useful for revision.
- Avoid duplicate or nearly duplicate cards.
- Include a short topic for every card.
- Return only valid JSON, with no Markdown fences.

Required JSON structure:
[
  {{
    "question": "A clear study question",
    "answer": "An accurate answer",
    "topic": "Short topic name"
  }}
]

STUDY MATERIAL:
{context}

FLASHCARDS:
"""

    response = _generate_with_retry(prompt).strip()

    if response.startswith("```"):
        lines = response.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines).strip()

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError("AI returned invalid flashcard JSON.") from exc

    if not isinstance(parsed, list):
        raise ValueError("AI flashcard response must be a JSON list.")

    cards = []
    seen = set()

    for item in parsed:
        if not isinstance(item, dict):
            continue

        question = item.get("question")
        answer = item.get("answer")
        topic = item.get("topic", "General")

        if not isinstance(question, str) or not isinstance(answer, str):
            continue

        question = question.strip()
        answer = answer.strip()
        topic = str(topic).strip() or "General"

        if not question or not answer:
            continue

        normalized = question.casefold()
        if normalized in seen:
            continue

        seen.add(normalized)
        cards.append({
            "question": question,
            "answer": answer,
            "topic": topic,
        })

    if not cards:
        raise ValueError("AI did not generate any valid flashcards.")

    return cards[:card_count]
