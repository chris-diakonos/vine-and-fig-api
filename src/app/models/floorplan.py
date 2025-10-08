"""
Floorplan-related models.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class Dimensions(BaseModel):
    """Building dimensions in inches."""
    front: float = Field(..., ge=240, le=528, description="Front dimension in inches")
    rear: float = Field(..., ge=240, le=528, description="Rear dimension in inches")
    left: float = Field(..., ge=240, le=480, description="Left dimension in inches")
    right: float = Field(..., ge=240, le=480, description="Right dimension in inches")
    building_height: float = Field(..., ge=120, le=480, description="Building height in inches")


class Spacing(BaseModel):
    """Structural spacing parameters in inches."""
    stud_spacing: float = Field(..., ge=21, le=24, description="Stud spacing in inches")
    joist_spacing: float = Field(..., ge=21, le=24, description="Joist spacing in inches")
    rafter_spacing: float = Field(..., ge=21, le=24, description="Rafter spacing in inches")
    bay_width: float = Field(..., ge=30, le=48, description="Bay width in inches")
    pile_width: float = Field(..., ge=192, le=240, description="Pile width in inches")


class Bays(BaseModel):
    """Bay configurations for each side of the building."""
    front: List[float] = Field(default_factory=list, description="Front bay widths")
    rear: List[float] = Field(default_factory=list, description="Rear bay widths")
    left: List[float] = Field(default_factory=list, description="Left bay widths")
    right: List[float] = Field(default_factory=list, description="Right bay widths")


class Floorplan(BaseModel):
    """Complete floorplan specification."""
    floorplan_type: Literal["center-hall", "side-hall"] = Field(
        ..., description="Type of floorplan layout"
    )
    depth: Literal["single-pile", "double-pile"] = Field(
        ..., description="Building depth configuration"
    )
    stories: int = Field(..., ge=1, le=3, description="Number of stories")
    hall_offset: Optional[float] = Field(
        0, ge=-96, le=96, description="Hall offset from center in inches"
    )
    hall_width: float = Field(..., ge=72, le=120, description="Hall width in inches")
    ceiling_heights: Optional[List[float]] = Field(
        None, description="Ceiling heights for each story (96-144 inches)"
    )
    joist_heights: Optional[List[float]] = Field(
        None, description="Joist heights for each floor (6-12 inches)"
    )
    dimensions: Dimensions = Field(..., description="Building dimensions")
    spacing: Spacing = Field(..., description="Structural spacing parameters")
    bays: Optional[Bays] = Field(None, description="Bay configurations")
