"""
Main building builder that combines all components.
"""
import cadquery as cq
from app.models.structure import Structure
from app.services.foundation_builder import FoundationBuilder
from app.services.floor_builder import FloorBuilder
from app.services.wall_builder import WallBuilder
from app.services.roof_builder import RoofBuilder
from app.services.openings_builder import OpeningsBuilder


class BuildingBuilder:
    """Orchestrates the construction of complete building model."""
    
    @staticmethod
    def build(structure: Structure) -> cq.Workplane:
        """
        Build a complete building from structure specification.
        
        Args:
            structure: Complete structure specification
            
        Returns:
            CadQuery Workplane with complete building geometry
        """
        floorplan = structure.floorplan
        dimensions = floorplan.dimensions
        
        # Build foundation
        foundation = FoundationBuilder.build(
            structure.foundation,
            dimensions
        )
        
        # Build floors
        floors = FloorBuilder.build(
            structure.flooring,
            dimensions,
            floorplan.stories,
            floorplan.ceiling_heights,
            floorplan.joist_heights
        )
        
        # Build walls
        walls = WallBuilder.build(
            structure.sheathing,
            dimensions,
            floorplan.stories,
            floorplan.ceiling_heights
        )
        
        # Build roof
        roof = RoofBuilder.build(
            structure.roof,
            dimensions,
            floorplan.stories,
            floorplan.ceiling_heights
        )
        
        # Combine all components
        building = foundation.union(floors).union(walls).union(roof)
        
        # Add windows if specified
        if structure.windows:
            windows = OpeningsBuilder.build_windows(structure.windows, dimensions)
            if windows is not None:
                building = building.union(windows)
        
        # Add doors if specified
        if structure.doors:
            doors = OpeningsBuilder.build_doors(structure.doors, dimensions)
            if doors is not None:
                building = building.union(doors)
        
        return building
