"""
Response models for API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class ModelResponse(BaseModel):
    """Response model for generated models and drawings."""
    model_url: str = Field(..., description="URL to access the generated model or drawing", alias="modelUrl")
    gltf_url: Optional[str] = Field(None, description="URL to glTF 3D model (3D view only)", alias="gltfUrl")
    image_url: Optional[str] = Field(None, description="URL to image/SVG (2D views only)", alias="imageUrl")
    view_mode: Literal["3d", "plan", "section", "elevation"] = Field(
        ..., description="View mode that was rendered", alias="viewMode"
    )
    model_id: str = Field(..., description="Unique identifier for this model", alias="modelId")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the model was generated"
    )
    
    class Config:
        populate_by_name = True
        by_alias = True


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


class BOMDataResponse(BaseModel):
    """Response model for BOM data retrieval."""
    structure_hash: str = Field(..., description="Structure hash identifier", alias="structureHash")
    materials: list = Field(..., description="List of materials")
    bom_components: dict = Field(..., description="BOM component relationships", alias="bomComponents")
    bom_quantities: dict = Field(..., description="BOM quantities", alias="bomQuantities")
    bom_levels: dict = Field(..., description="BOM levels", alias="bomLevels")
    created_at: Optional[str] = Field(None, description="Creation timestamp", alias="createdAt")
    updated_at: Optional[str] = Field(None, description="Last update timestamp", alias="updatedAt")
    
    class Config:
        populate_by_name = True
        by_alias = True


class BOMSubmissionResponse(BaseModel):
    """Response model for BOM submission to MRP."""
    structure_hash: str = Field(..., description="Structure hash identifier", alias="structureHash")
    success: bool = Field(..., description="Whether submission was successful")
    materials: dict = Field(..., description="Materials creation results")
    production_boms: dict = Field(..., description="Production BOM creation results", alias="productionBoms")
    sales_bom: dict = Field(..., description="Sales BOM creation results", alias="salesBom")
    errors: list = Field(default_factory=list, description="List of errors if any")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of submission"
    )
    
    class Config:
        populate_by_name = True
        by_alias = True