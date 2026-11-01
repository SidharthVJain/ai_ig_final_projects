from backend.app.services.github_service import GitHubService


def get_github_service() -> GitHubService:
    return GitHubService()


def get_rag_service():
    from backend.app.services.rag_service import RAGService

    return RAGService()
