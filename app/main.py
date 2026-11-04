from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.routes.documents import router as document_router
from app.routes.chat import router as chat_router
from app.routes.bookings import router as booking_router
from app.security import require_api_key
from app.services.health_service import check_readiness


app = FastAPI(
    title="Document RAG Backend",
    description="Document ingestion, conversational RAG, and interview booking API",
    version="0.8.3",
)

app.include_router(
    document_router,
    prefix="/api/v1",
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    chat_router,
    prefix="/api/v1",
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    booking_router,
    prefix="/api/v1",
    dependencies=[Depends(require_api_key)],
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


@app.get("/health/live")
async def liveness_check() -> dict[str, str]:
    return {
        "status": "alive"
    }


@app.get("/health/ready")
async def readiness_check() -> JSONResponse:
    result = await check_readiness()
    status_code = 200 if result["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=result)
