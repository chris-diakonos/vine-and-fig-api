"""
Response models for API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class ModelResponse(BaseModel):
    """Response model for generated models and drawings."""
    model_url: str = Field(..., description="URL to access the generated model or drawing")
    gltf_url: Optional[str] = Field(None, description="URL to glTF 3D model (3D view only)")
    image_url: Optional[str] = Field(None, description="URL to image/SVG (2D views only)")
    view_mode: Literal["3d", "plan", "section", "elevation"] = Field(
        ..., description="View mode that was rendered"
    )
    model_id: str = Field(..., description="Unique identifier for this model")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the model was generated"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "unhealthy"] = Field(..., description="Service health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of health check"
    )
