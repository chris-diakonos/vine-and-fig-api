"""
Main structure and request models.
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from app.models.customer import Customer
from app.models.floorplan import Floorplan
from app.models.building import Foundation, Roof, Sheathing, Flooring
from app.models.openings import Window, Door


class Structure(BaseModel):
    """Complete building structure specification."""
    floorplan: Floorplan = Field(..., description="Floorplan configuration")
    foundation: Foundation = Field(..., description="Foundation specification")
    roof: Roof = Field(..., description="Roof specification")
    sheathing: Sheathing = Field(..., description="Exterior sheathing specification")
    flooring: List[Flooring] = Field(default_factory=list, description="Flooring specifications (one per story + attic)")
    windows: List[Window] = Field(default_factory=list, description="Window specifications (one per story + dormers)")
    doors: List[Door] = Field(default_factory=list, description="Door specifications")


class BuildingRequest(BaseModel):
    """Request model for generating building models and drawings."""
    customer: Customer = Field(..., description="Customer information")
    structure: Structure = Field(..., description="Building structure specification")
    structure_hash: Optional[str] = Field(None, description="SHA-256 hash of the structure data")
    view_mode: Literal["3d", "plan", "section", "elevation"] = Field(
        default="3d",
        description="View mode for the generated output"
    )
