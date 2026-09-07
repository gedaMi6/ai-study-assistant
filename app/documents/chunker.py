def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> list[str]:
    """
    Split text into overlapping chunks.

    chunk_size:
        Maximum number of characters per chunk.

    chunk_overlap:
        Number of characters shared between consecutive chunks.
    """

    if not text.strip():
        return []

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - chunk_overlap

    return chunks