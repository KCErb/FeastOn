"""
Health check endpoint.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    data_dir: str


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    """Health check"""
    config = request.app.state.config
    return HealthResponse(
        status="ok",
        version="0.1.0",
        data_dir=str(config.data_dir)
    )
