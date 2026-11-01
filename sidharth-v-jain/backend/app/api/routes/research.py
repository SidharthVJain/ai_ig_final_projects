"""PDF ingestion and grounded research Q&A endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.api.dependencies import get_rag_service
from backend.app.schemas.rag import (
    AskRequest,
    AskResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from backend.app.services.rag_service import RAGService, RAGServiceError

router = APIRouter(prefix="/api/v1/research", tags=["Research Assistant"])
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a research PDF",
)
async def upload_document(
    service: RAGServiceDep,
    file: Annotated[UploadFile, File(description="Text-based PDF document")],
) -> DocumentUploadResponse:
    """Extract, chunk, embed, and persist an uploaded PDF."""
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported.")

    settings = service.settings
    max_bytes = settings.max_pdf_size_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    await file.close()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"PDF is too large. Maximum upload size is {settings.max_pdf_size_mb} MB.",
        )
    try:
        return service.ingest_pdf(filename=filename, pdf_bytes=content)
    except RAGServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/documents", response_model=DocumentListResponse, summary="List indexed PDFs")
async def list_documents(service: RAGServiceDep) -> DocumentListResponse:
    try:
        return service.list_documents()
    except RAGServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/ask", response_model=AskResponse, summary="Ask a question about uploaded PDFs")
async def ask_documents(
    payload: AskRequest,
    service: RAGServiceDep,
) -> AskResponse:
    try:
        return service.ask(
            question=payload.question,
            document_ids=payload.document_ids,
            top_k=payload.top_k,
        )
    except RAGServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
