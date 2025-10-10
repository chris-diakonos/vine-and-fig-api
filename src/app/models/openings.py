"""
Window and door models.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional, List


class Window(BaseModel):
    """Window specification."""
    configuration: Literal["6/6", "6/9", "9/9"] = Field(
        ..., description="Window pane configuration (upper/lower)"
    )
    operation: Literal["single-hung", "double-hung"] = Field(
        ..., description="Window operation type"
    )
    window_species: Literal["pine", "cypress"] = Field(
        ..., description="Wood species for window"
    )
    size: Literal["8x10", "10x12", "11x14", "12x16", "14x18"] = Field(
        ..., description="Window size (width x height in inches)"
    )
    profile: Literal["ovolo"] = Field(
        ..., description="Molding profile type"
    )
    thickness: Literal[1.0, 1.375, 1.75] = Field(
        ..., description="Frame thickness in inches"
    )
    stile_width: float = Field(
        ..., ge=2, le=2.5, description="Stile width in inches"
    )
    rail_width: float = Field(
        ..., ge=3, le=4, description="Rail width in inches"
    )
    muntin_width: float = Field(
        ..., ge=0.75, le=1.5, description="Muntin width in inches"
    )
    meeting_rail_width: float = Field(
        ..., ge=1.0, le=2.0, description="Meeting rail width in inches"
    )
    bay_width: float = Field(
        ..., ge=20, le=60, description="Calculated bay width in inches"
    )
    chair_rail_height: float = Field(
        ..., ge=24, le=36, description="Height from floor to window sill in inches"
    )
    # Location information (not in original schema, but useful for placement)
    wall: Optional[Literal["front", "rear", "left", "right"]] = None
    position: Optional[float] = Field(
        None, description="Position along wall in inches from left"
    )
    floor: Optional[int] = Field(None, ge=1, le=3, description="Floor number")


class Door(BaseModel):
    """Door specification."""
    configuration: Literal["four-panel", "six-panel"] = Field(
        ..., description="Door panel configuration"
    )
    panel_type: Literal["raised-panel", "flat-panel"] = Field(
        ..., description="Type of door panels"
    )
    operation: Literal[
        "right-outswing", "left-outswing", "right-inswing", "left-inswing"
    ] = Field(..., description="Door swing direction")
    door_species: Literal["pine"] = Field(
        ..., description="Wood species for door"
    )
    size: Literal["30x96", "32x96", "30x80", "32x80", "36x80", "36x96"] = Field(
        ..., description="Door size (width x height in inches)"
    )
    profile: Literal["ovolo"] = Field(
        ..., description="Molding profile type"
    )
    thickness: Literal[1.0, 1.375, 1.75] = Field(
        ..., description="Door thickness in inches"
    )
    bay_width: float = Field(
        ..., ge=20, le=60, description="Calculated bay width in inches"
    )
    stile_widths: List[float] = Field(
        default_factory=list, description="Array of 3 stile widths [left, center, right] in inches"
    )
    rail_widths: List[float] = Field(
        default_factory=list, description="Array of rail widths [top to bottom] in inches (3 for 4-panel, 4 for 6-panel)"
    )
    panel_widths: List[float] = Field(
        default_factory=list, description="Array of 2 panel widths [left, right] in inches"
    )
    # Location information (not in original schema, but useful for placement)
    wall: Optional[Literal["front", "rear", "left", "right"]] = None
    position: Optional[float] = Field(
        None, description="Position along wall in inches from left"
    )
    floor: Optional[int] = Field(None, ge=1, le=3, description="Floor number")
