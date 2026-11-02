from fastapi import FastAPI

app = FastAPI(
    title = "Rag Backend",
    description = "Document ingestion and conversational RAG API",
    version = "0.1.0"
)

@app.get("/")
async def root() -> dict[str,str]:
    return{
        "message":"Welcome to the Document Rag Backend"
    }
    
@app.get("/health")
async def health_check() -> dict[str,str]:
    return{
        "status": "healthy"
    }