"""
Floor builder service using CadQuery.
"""
import cadquery as cq
from typing import List, Optional
from app.models.building import Flooring
from app.models.floorplan import Dimensions


class FloorBuilder:
    """Builds floor geometry using CadQuery."""
    
    @staticmethod
    def build(
        flooring: List[Flooring],
        dimensions: Dimensions,
        stories: int,
        ceiling_heights: Optional[List[float]] = None,
        joist_heights: Optional[List[float]] = None
    ) -> cq.Workplane:
        """
        Build floor structures for all stories.
        
        Args:
            flooring: List of flooring specifications (one per story + attic)
            dimensions: Building dimensions
            stories: Number of stories
            ceiling_heights: Ceiling heights for each story
            joist_heights: Joist heights for each floor
            
        Returns:
            CadQuery Workplane with floor geometry
        """
        # Use defaults if not specified
        if ceiling_heights is None:
            ceiling_heights = [120] * stories  # 10 feet default
        if joist_heights is None:
            joist_heights = [10] * (stories + 1)  # Include foundation floor
        
        floors = None
        
        # If flooring array is empty or insufficient, create default config
        from app.models.building import Flooring as FlooringModel
        default_flooring = FlooringModel(
            flooring_type="tongue-and-groove",
            flooring_species="pine",
            flooring_thickness=1.0,
            flooring_width=10.0,
            flooring_exposure=9.25
        )
        
        # Calculate floor positions based on joist positions
        # Joists are positioned at previous_ceiling_height and are centered (so extend joist_height/2 above and below)
        # Floors should sit on TOP of the joists
        
        # Match the joist positioning logic from FramingBuilder._add_joists()
        # Story 1: joists at z=0 (sitting on sills)
        # Story 2+: joists at accumulated previous_ceiling_height
        
        for i in range(stories + 1):  # +1 for foundation floor (first floor)
            # Convert floor index to story number (floors are 0-indexed, stories are 1-indexed)
            story = i + 1
            
            # Calculate previous_ceiling_height exactly as in FramingBuilder._add_joists()
            previous_ceiling_height = 0
            if story > 1:
                for p in range(story - 1):
                    previous_ceiling_height += ceiling_heights[p] + (joist_heights[p] / 2)
            
            # Get joist height for this story (story is 1-indexed, so use story-1 as index)
            joist_height_for_floor = joist_heights[story - 1] if (story - 1) < len(joist_heights) else joist_heights[-1]
            
            # Joist is centered at previous_ceiling_height
            # Joist extends from previous_ceiling_height - joist_height/2 to previous_ceiling_height + joist_height/2
            # Joist top = previous_ceiling_height + joist_height/2
            joist_top = previous_ceiling_height + (joist_height_for_floor / 2)
            
            # Floor sits on top of joists
            # Floor bottom = joist top
            # Floor is centered, so floor center = floor bottom + floor_thickness/2
            if len(flooring) > 0:
                flooring_config = flooring[i] if i < len(flooring) else flooring[0]
            else:
                flooring_config = default_flooring
            
            floor_thickness = flooring_config.flooring_thickness
            floor_center_z = joist_top + (floor_thickness / 2)
            
            # Create floor slab
            floor_slab = (
                cq.Workplane("XY")
                .box(dimensions.front, dimensions.left, floor_thickness)
                .translate((0, 0, floor_center_z))
            )
            
            # Add floor to collection
            if floors is None:
                floors = floor_slab
            else:
                floors = floors.union(floor_slab)
        
        return floors
