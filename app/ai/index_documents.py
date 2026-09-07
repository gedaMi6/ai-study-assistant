import sqlite3

from app.ai.vector_store import add_chunk


DB_PATH = "data/study_assistant.db"


def index_all_chunks():
    db = sqlite3.connect(DB_PATH)

    rows = db.execute(
        """
        SELECT id, document_id, chunk_index, content
        FROM document_chunks
        ORDER BY id
        """
    ).fetchall()

    db.close()

    print(f"Found {len(rows)} chunks in SQLite.")

    for chunk_id, document_id, chunk_index, content in rows:
        add_chunk(
            chunk_id=str(chunk_id),
            content=content,
            document_id=document_id,
            chunk_index=chunk_index,
        )

        print(f"Indexed chunk {chunk_index} (ID: {chunk_id})")

    print(f"\nSuccessfully indexed {len(rows)} chunks.")


if __name__ == "__main__":
    index_all_chunks()
