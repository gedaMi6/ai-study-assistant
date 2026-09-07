import fitz
from pathlib import Path


def extract_text_from_pdf(file_path: Path) -> str:
    """
    Extract text from every page of a PDF.
    """

    document = fitz.open(file_path)

    pages = []

    for page in document:
        text = page.get_text()
        if text.strip():
            pages.append(text)

    document.close()

    return "\n\n".join(pages)