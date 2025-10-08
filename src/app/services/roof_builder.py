"""
Roof builder service using CadQuery.
"""
import cadquery as cq
from typing import List, Optional
from app.models.building import Roof
from app.models.floorplan import Dimensions


class RoofBuilder:
    """Builds roof geometry using CadQuery."""
    
    @staticmethod
    def build(
        roof: Roof,
        dimensions: Dimensions,
        stories: int,
        ceiling_heights: Optional[List[float]] = None
    ) -> cq.Workplane:
        """
        Build roof structure based on roof type and pitch.
        
        Args:
            roof: Roof specification
            dimensions: Building dimensions
            stories: Number of stories
            ceiling_heights: Ceiling heights for each story
            
        Returns:
            CadQuery Workplane with roof geometry
        """
        # Use default ceiling heights if not specified
        if ceiling_heights is None:
            ceiling_heights = [120] * stories  # 10 feet default
        
        # Calculate roof base elevation
        total_wall_height = sum(ceiling_heights)
        
        # Calculate roof height based on pitch (rise over 12 inches run)
        if roof.roof_type == "side-gable":
            # Pitch applies to the depth dimension
            run = dimensions.left / 2
            roof_height = (run / 12) * roof.roof_pitch
            
            # Create gable roof using loft
            roof_obj = RoofBuilder._build_gable_roof(
                dimensions.front,
                dimensions.left,
                roof_height,
                total_wall_height,
                "side"
            )
        
        elif roof.roof_type == "front-gable":
            # Pitch applies to the front dimension
            run = dimensions.front / 2
            roof_height = (run / 12) * roof.roof_pitch
            
            roof_obj = RoofBuilder._build_gable_roof(
                dimensions.front,
                dimensions.left,
                roof_height,
                total_wall_height,
                "front"
            )
        
        elif roof.roof_type == "hipped-gable":
            # More complex - simplified for now
            run = min(dimensions.front, dimensions.left) / 2
            roof_height = (run / 12) * roof.roof_pitch
            
            roof_obj = RoofBuilder._build_hipped_roof(
                dimensions.front,
                dimensions.left,
                roof_height,
                total_wall_height
            )
        
        else:
            # Default to simple gable
            run = dimensions.left / 2
            roof_height = (run / 12) * roof.roof_pitch
            roof_obj = RoofBuilder._build_gable_roof(
                dimensions.front,
                dimensions.left,
                roof_height,
                total_wall_height,
                "side"
            )
        
        return roof_obj
    
    @staticmethod
    def _build_gable_roof(
        width: float,
        depth: float,
        height: float,
        base_elevation: float,
        gable_direction: str
    ) -> cq.Workplane:
        """Build a gable roof."""
        roof_thickness = 6  # inches
        
        if gable_direction == "side":
            # Ridge runs along the front-back direction (X-axis)
            # Create two roof planes
            roof_plane = (
                cq.Workplane("XY")
                .sketch()
                .polygon([
                    (-width/2, -depth/2),
                    (width/2, -depth/2),
                    (width/2, 0),
                    (-width/2, 0)
                ])
                .finalize()
                .extrude(height)
                .translate((0, depth/4, base_elevation + height/2))
            )
            
            # Mirror for other side
            other_side = (
                cq.Workplane("XY")
                .sketch()
                .polygon([
                    (-width/2, 0),
                    (width/2, 0),
                    (width/2, depth/2),
                    (-width/2, depth/2)
                ])
                .finalize()
                .extrude(height)
                .translate((0, -depth/4, base_elevation + height/2))
            )
            
            roof = roof_plane.union(other_side)
        else:
            # Ridge runs along the left-right direction (Y-axis)
            roof_plane = (
                cq.Workplane("XY")
                .sketch()
                .polygon([
                    (-width/2, -depth/2),
                    (0, -depth/2),
                    (0, depth/2),
                    (-width/2, depth/2)
                ])
                .finalize()
                .extrude(height)
                .translate((-width/4, 0, base_elevation + height/2))
            )
            
            other_side = (
                cq.Workplane("XY")
                .sketch()
                .polygon([
                    (0, -depth/2),
                    (width/2, -depth/2),
                    (width/2, depth/2),
                    (0, depth/2)
                ])
                .finalize()
                .extrude(height)
                .translate((width/4, 0, base_elevation + height/2))
            )
            
            roof = roof_plane.union(other_side)
        
        return roof
    
    @staticmethod
    def _build_hipped_roof(
        width: float,
        depth: float,
        height: float,
        base_elevation: float
    ) -> cq.Workplane:
        """Build a hipped roof (simplified pyramid)."""
        # Create a pyramid shape for simplified hipped roof
        roof = (
            cq.Workplane("XY")
            .rect(width, depth)
            .workplane(offset=height)
            .rect(width * 0.3, depth * 0.3)
            .loft()
            .translate((0, 0, base_elevation))
        )
        
        return roof
