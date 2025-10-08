"""
Health check endpoints.
"""
from fastapi import APIRouter
from app.models.responses import HealthResponse
from app.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns the health status of the API service.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version
    )


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check endpoint.
    
    Returns whether the service is ready to handle requests.
    Useful for Kubernetes readiness probes.
    """
    # Could add checks for dependencies here (database, file system, etc.)
    return {"ready": True}


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check endpoint.
    
    Returns whether the service is alive.
    Useful for Kubernetes liveness probes.
    """
    return {"alive": True}
