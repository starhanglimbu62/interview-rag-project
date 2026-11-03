from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.database import get_db
from app.models import Document
from app.routes import documents

client = TestClient(app)


def test_upload_saves_document_metadata(db_session):

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample.txt",
                b"This is a sample document for metadata persistence testing.",
                "text/plain"
            )
        }
    )

    assert response.status_code == 200

    response_data = response.json()
    document_id = response_data["document"]["document_id"]

    saved_document = db_session.get(Document, document_id)

    assert saved_document is not None
    assert saved_document.filename == "sample.txt"
    assert saved_document.file_type == "txt"
    assert saved_document.character_count > 0
    assert saved_document.chunk_count == response_data["chunking"]["chunk_count"]
    assert saved_document.chunking_strategy == "fixed_size"
    assert saved_document.status == "ready"
    assert saved_document.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert saved_document.vector_database == "Qdrant"


def test_database_failure_rolls_back_and_deletes_vectors(
    monkeypatch,
    fake_vector_store
):

    class FailingSession:

        def __init__(self):
            self.rolled_back = False

        def add(self, document):
            pass

        def commit(self):
            raise SQLAlchemyError("Simulated database failure")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            pass

    failing_session = FailingSession()

    def override_get_db():
        yield failing_session

    app.dependency_overrides[get_db] = override_get_db

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample.txt",
                b"This document will trigger a simulated database failure.",
                "text/plain"
            )
        }
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Unable to save document metadata"

    assert failing_session.rolled_back is True
    assert len(fake_vector_store.deleted_document_ids) == 1

    app.dependency_overrides.pop(get_db, None)
