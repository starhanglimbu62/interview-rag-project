from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)
from app.services.document_service import extract_text

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
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

        result = extract_text(file.filename, content)

        return {
            "status": "success",
            "message": "Document extracted successfully",
            "document": {
                "filename": result["filename"],
                "file_type": result["file_type"],
                "character_count": result["character_count"],
                "page_count": result["page_count"]
            }
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    finally:
        await file.close()