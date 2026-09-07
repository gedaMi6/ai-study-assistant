import chromadb

from app.ai.embeddings import generate_embedding


CHROMA_PATH = "data/chroma"

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(
    name="document_chunks"
)


def add_chunk(
    chunk_id: str,
    content: str,
    document_id: str,
    chunk_index: int,
):
    embedding = generate_embedding(content)

    collection.upsert(
        ids=[chunk_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[
            {
                "document_id": document_id,
                "chunk_index": chunk_index,
            }
        ],
    )


def search_chunks(query: str, n_results: int = 5):
    query_embedding = generate_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    return results


def delete_document_chunks(document_id: str):
    """Remove all vector-store chunks belonging to a document."""
    collection.delete(
        where={"document_id": document_id}
    )
