from app.ai.vector_store import search_chunks
from app.ai.llm import generate_answer, rewrite_question
from app.database.database import get_connection


def get_conversation_history(session_id: str, limit: int = 10) -> list[dict]:
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT role, content
        FROM conversations
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit)
    ).fetchall()

    connection.close()

    # Reverse so the oldest message comes first
    rows = list(reversed(rows))

    return [
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in rows
    ]


def save_message(session_id: str, role: str, content: str):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO conversations (
            session_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (session_id, role, content)
    )

    connection.commit()
    connection.close()

def answer_question(
    question: str,
    n_results: int = 3,
    session_id: str = "default"
) -> dict:

    # Get previous conversation before saving the current question
    history = get_conversation_history(
        session_id,
        limit=10
    )

    # Rewrite the question using conversation context
    search_query = rewrite_question(
        question,
        history
    )

    print(f"Original question: {question}")
    print(f"Search query: {search_query}")

    # Save the user's current question
    save_message(
        session_id,
        "user",
        question
    )

    # Retrieve relevant study material using the rewritten query
    results = search_chunks(
        search_query,
        n_results
    )

    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    if not documents:
        answer = (
            "I couldn't find relevant study material "
            "for that question."
        )

        save_message(
            session_id,
            "assistant",
            answer
        )

        return {
            "answer": answer,
            "sources": []
        }

    chunks = documents[0]

    metadata_list = (
        metadatas[0]
        if metadatas
        else []
    )

    context = "\n\n".join(chunks)

    # Generate the final answer using the original question
    # plus the previous conversation
    answer = generate_answer(
        question,
        context,
        history
    )

    # Save AI response
    save_message(
        session_id,
        "assistant",
        answer
    )

    sources = []

    connection = get_connection()

    for metadata in metadata_list:

        document_id = metadata.get(
            "document_id"
        )

        chunk_index = metadata.get(
            "chunk_index"
        )

        if not document_id:
            continue

        row = connection.execute(
            """
            SELECT filename
            FROM documents
            WHERE id = ?
            """,
            (document_id,)
        ).fetchone()

        if row:
            sources.append({
                "document": row["filename"],
                "chunk": chunk_index
            })

    connection.close()

    # Remove duplicate sources
    unique_sources = []
    seen = set()

    for source in sources:

        key = (
            source["document"],
            source["chunk"]
        )

        if key not in seen:
            seen.add(key)
            unique_sources.append(source)

    return {
        "answer": answer,
        "sources": unique_sources
    }
