"""Lazy sentence-transformers embedding model wrapper."""

from functools import lru_cache
from typing import Sequence

from backend.app.core.config import get_settings


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - installation/configuration path
        raise RuntimeError(
            "sentence-transformers is not installed. Install the full requirements.txt."
        ) from exc
    return SentenceTransformer(model_name)


class EmbeddingService:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or get_settings().embedding_model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        model = _load_model(self.model_name)
        encoder = getattr(model, "encode_document", model.encode)
        vectors = encoder(list(texts), normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        model = _load_model(self.model_name)
        encoder = getattr(model, "encode_query", model.encode)
        vector = encoder([text], normalize_embeddings=True)
        return vector[0].tolist()
