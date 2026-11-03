from fastapi import FastAPI

from app.routes.documents import router as document_router
from app.routes.chat import router as chat_router


app = FastAPI(
    title="Document RAG Backend",
    description="Document ingestion and conversational RAG API",
    version="0.6.3"
)


app.include_router(
    document_router,
    prefix="/api/v1"
)

app.include_router(
    chat_router,
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
