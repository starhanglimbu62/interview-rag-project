import pytest

from app.routes import documents


class FakeEmbeddingService:

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [0.1] * 384
            for _ in texts
        ]


class FakeVectorStore:

    def create_collection(self) -> None:
        pass

    def store_chunks(
        self,
        document_id: str,
        filename: str,
        chunks: list[str],
        embeddings: list[list[float]]
    ) -> int:
        return len(chunks)


@pytest.fixture(autouse=True)
def mock_embedding_service(monkeypatch):

    monkeypatch.setattr(
        documents,
        "get_embedding_service",
        lambda: FakeEmbeddingService()
    )


@pytest.fixture(autouse=True)
def mock_vector_store(monkeypatch):

    monkeypatch.setattr(
        documents,
        "get_vector_store",
        lambda: FakeVectorStore()
    )
