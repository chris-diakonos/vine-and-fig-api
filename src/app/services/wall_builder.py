"""
Wall builder service using CadQuery.
"""
import cadquery as cq
from typing import List, Optional
from app.models.building import Sheathing
from app.models.floorplan import Dimensions


class WallBuilder:
    """Builds wall and sheathing geometry using CadQuery."""
    
    @staticmethod
    def build(
        sheathing: Sheathing,
        dimensions: Dimensions,
        stories: int,
        ceiling_heights: Optional[List[float]] = None
    ) -> cq.Workplane:
        """
        Build exterior walls with sheathing.
        
        Args:
            sheathing: Sheathing specification
            dimensions: Building dimensions
            stories: Number of stories
            ceiling_heights: Ceiling heights for each story
            
        Returns:
            CadQuery Workplane with wall geometry
        """
        # Use default ceiling heights if not specified
        if ceiling_heights is None:
            ceiling_heights = [120] * stories  # 10 feet default
        
        total_wall_height = sum(ceiling_heights)
        wall_thickness = 6  # Typical wall thickness in inches
        
        # Create four walls as hollow box
        # Front wall
        front_wall = (
            cq.Workplane("XZ")
            .rect(dimensions.front, total_wall_height)
            .extrude(wall_thickness)
            .translate((0, -dimensions.left / 2, total_wall_height / 2))
        )
        
        # Rear wall
        rear_wall = (
            cq.Workplane("XZ")
            .rect(dimensions.rear, total_wall_height)
            .extrude(wall_thickness)
            .translate((0, dimensions.left / 2 - wall_thickness, total_wall_height / 2))
        )
        
        # Left wall
        left_wall = (
            cq.Workplane("YZ")
            .rect(dimensions.left, total_wall_height)
            .extrude(wall_thickness)
            .translate((-dimensions.front / 2, 0, total_wall_height / 2))
        )
        
        # Right wall
        right_wall = (
            cq.Workplane("YZ")
            .rect(dimensions.right, total_wall_height)
            .extrude(wall_thickness)
            .translate((dimensions.front / 2 - wall_thickness, 0, total_wall_height / 2))
        )
        
        # Combine all walls
        walls = front_wall.union(rear_wall).union(left_wall).union(right_wall)
        
        # Add sheathing texture representation
        # In production, you could add individual boards with proper exposure
        
        return walls
