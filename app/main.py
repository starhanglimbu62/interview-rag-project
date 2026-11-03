from fastapi import FastAPI

from app.routes.documents import router as document_router


app = FastAPI(
    title="Document RAG Backend",
    description="Document ingestion and conversational RAG API",
    version="0.4.2"
)


app.include_router(
    document_router,
    prefix="/api/v1"
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Welcome to Document RAG Backend"
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy"
    }
