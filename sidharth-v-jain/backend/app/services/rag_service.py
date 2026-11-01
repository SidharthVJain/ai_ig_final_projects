"""Document ingestion, persistent retrieval, and grounded Q&A orchestration."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from uuid import uuid4

from backend.app.core.config import get_settings
from backend.app.rag.document_processing import chunk_pages, extract_pdf_pages
from backend.app.rag.embedding_service import EmbeddingService
from backend.app.rag.vector_store import ChromaVectorStore
from backend.app.schemas.rag import (
    AskResponse,
    DocumentListResponse,
    DocumentSummary,
    DocumentUploadResponse,
    SourceReference,
)
from backend.app.services.groq_service import GroqService


class RAGServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class RAGService:
    def __init__(
        self,
        *,
        embeddings: EmbeddingService | None = None,
        vector_store: ChromaVectorStore | None = None,
        groq_factory=GroqService,
    ) -> None:
        self.settings = get_settings()
        self.embeddings = embeddings or EmbeddingService()
        self.vector_store = vector_store or ChromaVectorStore()
        self.groq_factory = groq_factory

    def ingest_pdf(self, *, filename: str, pdf_bytes: bytes) -> DocumentUploadResponse:
        settings = self.settings
        max_bytes = settings.max_pdf_size_mb * 1024 * 1024
        if len(pdf_bytes) > max_bytes:
            raise RAGServiceError(
                f"PDF is too large. Maximum upload size is {settings.max_pdf_size_mb} MB.",
                413,
            )
        if Path(filename).suffix.lower() != ".pdf":
            raise RAGServiceError("Only PDF files are supported.", 415)

        try:
            pages = extract_pdf_pages(pdf_bytes)
            chunks = chunk_pages(
                pages, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap
            )
        except ValueError as exc:
            raise RAGServiceError(str(exc), 422) from exc

        digest = hashlib.sha256(pdf_bytes).hexdigest()
        try:
            existing = next(
                (doc for doc in self.vector_store.list_documents() if doc.get("sha256") == digest),
                None,
            )
        except RuntimeError as exc:
            raise RAGServiceError(str(exc), 503) from exc
        if existing:
            summary = DocumentSummary.model_validate(existing)
            return DocumentUploadResponse(
                status="indexed",
                document=summary,
                message="This PDF is already indexed; the existing document was kept.",
            )

        document_id = str(uuid4())
        uploaded_at = datetime.now(timezone.utc)
        safe_filename = Path(filename.replace("\\", "/")).name[:240]
        texts = [chunk.text for chunk in chunks]
        try:
            vectors = self.embeddings.embed_documents(texts)
            metadatas = [
                {
                    "document_id": document_id,
                    "filename": safe_filename,
                    "sha256": digest,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "page_count": len(pages),
                    "uploaded_at": uploaded_at.isoformat(),
                }
                for chunk in chunks
            ]
            self.vector_store.upsert(
                ids=[f"{document_id}:{chunk.chunk_index}" for chunk in chunks],
                documents=texts,
                metadatas=metadatas,
                embeddings=vectors,
            )
        except (RuntimeError, ValueError) as exc:
            raise RAGServiceError(str(exc), 503) from exc
        except Exception as exc:
            raise RAGServiceError(f"Could not index this PDF: {exc}", 500) from exc

        summary = DocumentSummary(
            document_id=document_id,
            filename=safe_filename,
            sha256=digest,
            page_count=len(pages),
            chunk_count=len(chunks),
            uploaded_at=uploaded_at,
        )
        return DocumentUploadResponse(
            status="indexed",
            document=summary,
            message=f"Indexed {len(chunks)} text chunks from {len(pages)} text-bearing pages.",
        )

    def list_documents(self) -> DocumentListResponse:
        try:
            items = [DocumentSummary.model_validate(item) for item in self.vector_store.list_documents()]
        except RuntimeError as exc:
            raise RAGServiceError(str(exc), 503) from exc
        return DocumentListResponse(total_count=len(items), items=items)

    def retrieve_context(
        self, *, question: str, document_ids: list[str], top_k: int = 5
    ) -> str:
        """Retrieve source-labelled passages for use by downstream agents."""
        try:
            documents = self.vector_store.list_documents()
        except RuntimeError as exc:
            raise RAGServiceError(str(exc), 503) from exc
        known_ids = {item.get("document_id") for item in documents}
        unknown = sorted(set(document_ids) - known_ids)
        if unknown:
            raise RAGServiceError("One or more selected documents are not indexed.", 404)
        if not document_ids:
            return ""
        try:
            query_embedding = self.embeddings.embed_query(question)
            results = self.vector_store.query(
                embedding=query_embedding, top_k=top_k, document_ids=document_ids
            )
        except Exception as exc:
            raise RAGServiceError(f"Research document retrieval failed: {exc}", 503) from exc
        texts = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        passages = []
        for index, (text, metadata) in enumerate(zip(texts, metadatas), start=1):
            passages.append(
                f"[P{index}] Source: {metadata.get('filename', 'Unknown document')} "
                f"| Page: {metadata.get('page_number', 'unknown')}\n{text}"
            )
        if not passages:
            raise RAGServiceError("No matching passages were found in the selected documents.", 404)
        return "\n\n---\n\n".join(passages)

    def ask(
        self, *, question: str, document_ids: list[str] | None = None, top_k: int | None = None
    ) -> AskResponse:
        settings = self.settings
        try:
            documents = self.vector_store.list_documents()
        except RuntimeError as exc:
            raise RAGServiceError(str(exc), 503) from exc
        known_ids = {item.get("document_id") for item in documents}
        if not known_ids:
            raise RAGServiceError("Upload a research PDF before asking a question.", 404)
        if document_ids:
            unknown = sorted(set(document_ids) - known_ids)
            if unknown:
                raise RAGServiceError("One or more selected documents are not indexed.", 404)

        try:
            query_embedding = self.embeddings.embed_query(question)
            results = self.vector_store.query(
                embedding=query_embedding,
                top_k=top_k or settings.rag_top_k,
                document_ids=document_ids,
            )
        except RuntimeError as exc:
            raise RAGServiceError(str(exc), 503) from exc
        except Exception as exc:
            raise RAGServiceError(f"Document retrieval failed: {exc}", 500) from exc

        result_docs = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        if not result_docs:
            raise RAGServiceError("No matching passages were found in the selected documents.", 404)

        sources: list[SourceReference] = []
        context_parts: list[str] = []
        for index, (text, metadata) in enumerate(zip(result_docs, metadatas), start=1):
            citation_id = f"S{index}"
            filename = str(metadata.get("filename") or "Unknown document")
            page_number = int(metadata.get("page_number") or 1)
            sources.append(
                SourceReference(
                    citation_id=citation_id,
                    document_id=str(metadata.get("document_id") or ""),
                    filename=filename,
                    page_number=page_number,
                    excerpt=re.sub(r"\s+", " ", str(text)).strip()[:600],
                )
            )
            context_parts.append(
                f"[{citation_id}] File: {filename} | Page: {page_number}\n{text}"
            )

        try:
            groq = self.groq_factory()
            answer = groq.answer(question=question, context="\n\n---\n\n".join(context_parts))
            model = groq.model
        except Exception as exc:
            raise RAGServiceError(str(exc), 503) from exc

        return AskResponse(
            question=question,
            answer=answer,
            model=model,
            retrieved_count=len(sources),
            sources=sources,
        )
