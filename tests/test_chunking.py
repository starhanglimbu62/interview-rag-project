
import pytest

from app.services.chunking_service import (
    fixed_size_chunks,
    recursive_character_chunks
)


def test_fixed_size_chunking():
    text = "A" * 1200

    chunks = fixed_size_chunks(
        text,
        chunk_size=500,
        overlap=50
    )

    assert len(chunks) == 3
    assert all(len(chunk) <= 500 for chunk in chunks)


def test_fixed_size_overlap():
    text = "A" * 600

    chunks = fixed_size_chunks(
        text,
        chunk_size=500,
        overlap=50
    )

    assert chunks[0][-50:] == chunks[1][:50]


def test_empty_text():
    assert fixed_size_chunks("") == []
    assert recursive_character_chunks("") == []


def test_reject_invalid_chunk_size():
    with pytest.raises(ValueError):
        fixed_size_chunks("Hello", chunk_size=0)

    with pytest.raises(ValueError):
        recursive_character_chunks("Hello", chunk_size=0)


def test_reject_invalid_overlap():
    with pytest.raises(ValueError):
        fixed_size_chunks("Hello", chunk_size=100, overlap=100)


def test_recursive_chunk_size():
    text = (
        "First paragraph contains useful information.\n\n"
        "Second paragraph contains more information.\n\n"
        "Third paragraph contains additional information."
    )

    chunks = recursive_character_chunks(
        text,
        chunk_size=60,
        overlap=10
    )

    assert len(chunks) > 1
    assert all(len(chunk) <= 60 for chunk in chunks)


def test_recursive_chunking_long_text():
    text = "word " * 1000

    chunks = recursive_character_chunks(
        text,
        chunk_size=100,
        overlap=20
    )

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_whitespace_only_text():
    assert fixed_size_chunks("   \n  ") == []
    assert recursive_character_chunks("   \n  ") == []
