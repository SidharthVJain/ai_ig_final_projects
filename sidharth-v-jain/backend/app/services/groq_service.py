"""Groq chat-completion client for grounded research answers."""

from backend.app.core.config import get_settings


class GroqServiceError(RuntimeError):
    """Raised when the Groq API is unavailable or not configured."""


class GroqService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.groq_api_key:
            raise GroqServiceError(
                "GROQ_API_KEY is not configured. Add your key to the backend .env file."
            )
        try:
            from groq import Groq
        except ImportError as exc:  # pragma: no cover - installation/configuration path
            raise GroqServiceError("The groq package is not installed.") from exc
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def answer(self, *, question: str, context: str) -> str:
        system_prompt = (
            "You are DevDigest Research Assistant. Answer the user's question using only "
            "the supplied excerpts from uploaded documents. Do not use outside knowledge. "
            "Cite every factual claim with the exact source labels provided, such as [S1] "
            "or [S2]. Never invent a source label or page number. If the excerpts do not "
            "contain enough information, say clearly what cannot be established from the "
            "uploaded documents. You may synthesize across sources, but distinguish direct "
            "evidence from cautious inference. Keep the answer structured and concise."
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_completion_tokens=1200,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"DOCUMENT EXCERPTS:\n{context}\n\nQUESTION:\n{question}",
                    },
                ],
            )
            answer = response.choices[0].message.content or ""
            if not answer.strip():
                raise GroqServiceError("Groq returned an empty answer. Please try again.")
            return answer.strip()
        except GroqServiceError:
            raise
        except Exception as exc:
            raise GroqServiceError(f"Groq request failed: {exc}") from exc
