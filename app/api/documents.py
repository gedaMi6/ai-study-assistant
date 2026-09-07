from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.documents.processor import (
    extract_text_from_pdf,
    extract_text_from_pptx
)
from app.documents.chunker import chunk_text
from app.database.database import get_connection, save_chunks
from app.ai.vector_store import add_chunk, delete_document_chunks
from app.ai.llm import generate_summary, GeminiQuotaError

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("")
def list_documents():

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            d.id,
            d.filename,
            d.created_at,
            COUNT(c.document_id) AS chunk_count
        FROM documents d
        LEFT JOIN document_chunks c
            ON d.id = c.document_id
        GROUP BY
            d.id,
            d.filename,
            d.created_at
        ORDER BY d.created_at DESC
        """
    ).fetchall()

    connection.close()

    return {
        "status": "success",
        "documents": [
            {
                "id": row["id"],
                "filename": row["filename"],
                "created_at": row["created_at"],
                "chunk_count": row["chunk_count"]
            }
            for row in rows
        ]
    }


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided."
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in [".pdf", ".pptx"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and PowerPoint (.pptx) files are currently supported."
        )

    document_id = str(uuid4())

    safe_filename = Path(file.filename).name
    saved_filename = f"{document_id}_{safe_filename}"

    file_path = UPLOAD_DIR / saved_filename

    content = await file.read()
    file_path.write_bytes(content)

    try:
        if extension == ".pdf":
            extracted_text = extract_text_from_pdf(file_path)

        elif extension == ".pptx":
            extracted_text = extract_text_from_pptx(file_path)

    except Exception as e:
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )

    if not extracted_text.strip():
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail="No readable text was found in the document."
        )

    chunks = chunk_text(extracted_text)

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO documents (
            id,
            filename,
            stored_filename,
            extracted_text
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            document_id,
            safe_filename,
            saved_filename,
            extracted_text
        )
    )

    connection.commit()
    connection.close()

    save_chunks(
        document_id,
        chunks
    )

    for chunk_index, content in enumerate(chunks):
        add_chunk(
            chunk_id=f"{document_id}_{chunk_index}",
            content=content,
            document_id=document_id,
            chunk_index=chunk_index,
        )

    return {
        "status": "success",
        "document_id": document_id,
        "filename": safe_filename,
        "characters_extracted": len(extracted_text),
        "chunks_created": len(chunks),
        "message": "Document uploaded and processed successfully."
    }
@router.delete("/{document_id}")
def delete_document(document_id: str):

    connection = get_connection()

    row = connection.execute(
        """
        SELECT stored_filename
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    ).fetchone()

    if not row:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        # Remove embeddings from ChromaDB.
        delete_document_chunks(document_id)

        # Remove document chunks from SQLite.
        connection.execute(
            "DELETE FROM document_chunks WHERE document_id = ?",
            (document_id,)
        )

        # Remove the document record.
        connection.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,)
        )

        connection.commit()

        # Remove the physical PDF.
        file_path = UPLOAD_DIR / row["stored_filename"]
        file_path.unlink(missing_ok=True)

    except Exception as e:
        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )

    finally:
        connection.close()

    return {
        "status": "success",
        "document_id": document_id,
        "message": "Document deleted successfully."
    }


@router.get("/{document_id}/summary")
def summarize_document(document_id: str):

    connection = get_connection()

    row = connection.execute(
        """
        SELECT filename, extracted_text
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    ).fetchone()

    connection.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:
        summary = generate_summary(
            row["extracted_text"]
        )

    except GeminiQuotaError as e:
        print(f"Gemini quota error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Gemini API quota has been exhausted. Please try again after the quota resets."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )

    return {
        "status": "success",
        "document_id": document_id,
        "filename": row["filename"],
        "summary": summary
    }
