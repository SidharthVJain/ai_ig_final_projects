"""Persistent ChromaDB adapter. Imports ChromaDB only when first used."""

from functools import lru_cache
from typing import Any

from backend.app.core.config import get_settings


@lru_cache(maxsize=1)
def get_collection():
    settings = get_settings()
    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover - installation/configuration path
        raise RuntimeError("chromadb is not installed. Install the full requirements.txt.") from exc

    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


class ChromaVectorStore:
    def __init__(self, collection: Any | None = None) -> None:
        self._collection = collection

    @property
    def collection(self):
        return self._collection if self._collection is not None else get_collection()

    def upsert(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(
        self,
        *,
        embedding: list[float],
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        where = {"document_id": {"$in": document_ids}} if document_ids else None
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def list_documents(self) -> list[dict[str, Any]]:
        result = self.collection.get(include=["metadatas"])
        unique: dict[str, dict[str, Any]] = {}
        for metadata in result.get("metadatas") or []:
            if not metadata:
                continue
            document_id = metadata.get("document_id")
            if document_id:
                unique[document_id] = {
                    key: metadata.get(key)
                    for key in (
                        "document_id",
                        "filename",
                        "sha256",
                        "page_count",
                        "uploaded_at",
                    )
                }
        for document in unique.values():
            document["chunk_count"] = sum(
                1
                for metadata in result.get("metadatas") or []
                if metadata and metadata.get("document_id") == document["document_id"]
            )
        return sorted(unique.values(), key=lambda item: item.get("uploaded_at") or "", reverse=True)
