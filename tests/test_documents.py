from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_valid_txt():
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample.txt",
                b"FastAPI is a Python framework.",
                "text/plain"
            )
        }
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_reject_unsupported_file():
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample.docx",
                b"some content",
                "application/octet-stream"
            )
        }
    )

    assert response.status_code == 400


def test_reject_empty_file():
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "empty.txt",
                b"",
                "text/plain"
            )
        }
    )

    assert response.status_code == 400


def test_reject_invalid_pdf():
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "fake.pdf",
                b"This is not a PDF",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 400


def test_reject_oversized_file():
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "large.txt",
                b"a" * (10 * 1024 * 1024 + 1),
                "text/plain"
            )
        }
    )

    assert response.status_code == 413