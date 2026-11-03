import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.routes import documents


class FakeEmbeddingService:

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [0.1] * 384
            for _ in texts
        ]


class FakeVectorStore:

    def __init__(self):
        self.deleted_document_ids = []

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

    def delete_document(self, document_id: str) -> None:
        self.deleted_document_ids.append(document_id)


@pytest.fixture
def test_engine():

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def override_database(test_engine):

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False
    )

    def override_get_db():
        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def db_session(test_engine):

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False
    )

    with TestingSessionLocal() as db:
        yield db


@pytest.fixture(autouse=True)
def mock_embedding_service(monkeypatch):

    monkeypatch.setattr(
        documents,
        "get_embedding_service",
        lambda: FakeEmbeddingService()
    )


@pytest.fixture
def fake_vector_store(monkeypatch):

    store = FakeVectorStore()

    monkeypatch.setattr(
        documents,
        "get_vector_store",
        lambda: store
    )

    return store


@pytest.fixture(autouse=True)
def use_fake_vector_store(fake_vector_store):
    pass
