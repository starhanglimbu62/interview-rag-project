from functools import lru_cache

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Form
)

from app.services.document_service import extract_text
from app.services.chunking_service import (
    fixed_size_chunks,
    recursive_character_chunks
)
from app.services.embedding_service import (
    EmbeddingService,
    VECTOR_SIZE
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

MAX_FILE_SIZE = 10 * 1024 * 1024


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """
    Load the embedding model once and reuse it.
    """
    return EmbeddingService()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    chunking_strategy: str = Form("fixed_size"),
    chunk_size: int = Form(500),
    overlap: int = Form(50)
) -> dict[str, object]:

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    extension = file.filename.lower().rsplit(".", 1)[-1]

    if extension not in {"pdf", "txt"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported"
        )

    if chunking_strategy not in {"fixed_size", "recursive"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid chunking strategy"
        )

    if chunk_size <= 0:
        raise HTTPException(
            status_code=400,
            detail="Chunk size must be greater than zero"
        )

    if overlap < 0 or overlap >= chunk_size:
        raise HTTPException(
            status_code=400,
            detail="Overlap must be between 0 and chunk_size"
        )

    try:
        content = await file.read(MAX_FILE_SIZE + 1)

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Maximum file size is 10 MB"
            )

        try:
            result = extract_text(file.filename, content)

            if chunking_strategy == "fixed_size":
                chunks = fixed_size_chunks(
                    result["extracted_text"],
                    chunk_size,
                    overlap
                )
            else:
                chunks = recursive_character_chunks(
                    result["extracted_text"],
                    chunk_size,
                    overlap
                )

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc)
            ) from exc

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="Document produced no chunks"
            )

        embedding_service = get_embedding_service()

        embeddings = embedding_service.embed_texts(chunks)

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "Embedding count does not match chunk count"
            )

        return {
            "status": "success",
            "message": "Document processed successfully",
            "document": {
                "filename": result["filename"],
                "file_type": result["file_type"],
                "character_count": result["character_count"],
                "page_count": result["page_count"]
            },
            "chunking": {
                "strategy": chunking_strategy,
                "chunk_size": chunk_size,
                "overlap": overlap,
                "chunk_count": len(chunks)
            },
            "embedding": {
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "dimensions": VECTOR_SIZE,
                "embedded_chunk_count": len(embeddings)
            },
            "chunks": [
                {
                    "index": index,
                    "character_count": len(chunk),
                    "preview": chunk[:100]
                }
                for index, chunk in enumerate(chunks)
            ]
        }

    finally:
        await file.close()