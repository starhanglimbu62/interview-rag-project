from fastapi import FastAPI
from app.routes import documents

app = FastAPI(
     title="Document RAG Backend",
     description="Document ingestion and conversational RAG API",
    version="0.2.0"
 )

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Document RAG Backend"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}

app.include_router(documents.router, prefix="/api/v1")