"""Health check endpoint."""

from fastapi import APIRouter
from models.api_models import HealthResponse

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", version="0.2.0")
