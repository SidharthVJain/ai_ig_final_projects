"""PDF text extraction and page-aware overlapping text chunking."""

from dataclasses import dataclass
import re

import fitz


class PDFProcessingError(ValueError):
    """Raised when a PDF cannot be safely read or has no extractable text."""


@dataclass(frozen=True)
class TextChunk:
    text: str
    page_number: int
    chunk_index: int


def extract_pdf_pages(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Extract normalized text from a PDF as (1-based page number, text)."""
    if not pdf_bytes or b"%PDF-" not in pdf_bytes[:1024]:
        raise PDFProcessingError("The uploaded file does not appear to be a valid PDF.")

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            pages: list[tuple[int, str]] = []
            for page_index, page in enumerate(document):
                text = page.get_text("text")
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    pages.append((page_index + 1, text))
            page_count = document.page_count
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        raise PDFProcessingError("Could not read this PDF. It may be damaged or encrypted.") from exc

    if page_count == 0:
        raise PDFProcessingError("The PDF contains no pages.")
    if not pages:
        raise PDFProcessingError(
            "No selectable text was found. This version supports text-based PDFs, not scanned-image PDFs."
        )
    return pages


def chunk_pages(
    pages: list[tuple[int, str]], *, chunk_size: int = 1000, overlap: int = 150
) -> list[TextChunk]:
    """Split each page into character chunks with overlap, preserving page numbers."""
    if chunk_size < 100:
        raise ValueError("chunk_size must be at least 100 characters.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size.")

    chunks: list[TextChunk] = []
    chunk_index = 0
    step = chunk_size - overlap
    for page_number, text in pages:
        text = text.strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            piece = text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    TextChunk(
                        text=piece,
                        page_number=page_number,
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1
            if start + chunk_size >= len(text):
                break
            start += step
    return chunks
