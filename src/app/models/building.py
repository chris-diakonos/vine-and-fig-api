"""
Building component models (foundation, roof, sheathing, flooring).
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class Foundation(BaseModel):
    """Foundation specification."""
    foundation_type: Literal["limestone-block", "concrete-block", "brick"] = Field(
        ..., description="Type of foundation material"
    )
    foundation_block_size: Optional[List[float]] = Field(
        None, description="Block dimensions [length, width, height] in inches"
    )
    foundation_courses: int = Field(
        ..., ge=2, le=10, description="Number of foundation courses"
    )
    foundation_block_joint: float = Field(
        ..., ge=0.125, le=0.5, description="Mortar joint thickness in inches"
    )


class Roof(BaseModel):
    """Roof specification."""
    roof_pitch: float = Field(
        ..., ge=30, le=40, description="Roof pitch (rise over 12 inches run)"
    )
    roof_type: Literal["side-gable", "front-gable", "hipped-gable", "side-gable-with-shed"] = Field(
        ..., description="Type of roof configuration"
    )
    roof_panel_type: Literal["ag-panel", "cf-panel", "pbr-panel"] = Field(
        ..., description="Type of roof panel"
    )
    roof_panel_color: Literal[
        "light-gray", "ash-gray", "charcoal-gray", "steel-gray",
        "burnished-slate", "emerald-green", "colony-green",
        "rustic-red", "cocoa-brown"
    ] = Field(..., description="Color of roof panels")
    roof_panel_exposure: int = Field(
        ..., ge=12, le=36, description="Panel exposure width in inches"
    )
    roof_overhang: float = Field(
        default=12, ge=6, le=18, description="Roof overhang in inches"
    )


class Sheathing(BaseModel):
    """Exterior sheathing specification."""
    sheathing_species: Literal["pine", "cypress"] = Field(
        ..., description="Wood species for sheathing"
    )
    sheathing_exposure: int = Field(
        ..., ge=5, le=8, description="Sheathing exposure in inches"
    )
    sheathing_height: float = Field(
        ..., ge=7.25, le=10, description="Sheathing board height in inches"
    )
    sheathing_type: Literal["beaded-weatherboard", "beveled-weatherboard"] = Field(
        ..., description="Type of sheathing profile"
    )


class Flooring(BaseModel):
    """Flooring specification."""
    flooring_type: Literal["tongue-and-groove", "butted-board"] = Field(
        ..., description="Type of flooring joint"
    )
    flooring_species: Literal["pine", "cypress"] = Field(
        ..., description="Wood species for flooring"
    )
    flooring_thickness: float = Field(
        ..., ge=0.75, le=1.5, description="Flooring thickness in inches"
    )
    flooring_width: float = Field(
        ..., ge=9.25, le=12, description="Flooring board width in inches"
    )
    flooring_exposure: float = Field(
        ..., ge=8.75, le=12, description="Flooring exposure in inches"
    )
