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
        current_z = 0  # Start at foundation level
        
        # If flooring array is empty or insufficient, create default config
        from app.models.building import Flooring as FlooringModel
        default_flooring = FlooringModel(
            flooring_type="tongue-and-groove",
            flooring_species="pine",
            flooring_thickness=1.0,
            flooring_width=10.0,
            flooring_exposure=9.25
        )
        
        # Build each floor
        for i in range(stories + 1):  # +1 for foundation floor
            # Get the flooring config for this level
            # Use the corresponding flooring config, or default if array is empty/short
            if len(flooring) > 0:
                flooring_config = flooring[i] if i < len(flooring) else flooring[0]
            else:
                flooring_config = default_flooring
            
            # Create floor slab
            floor_thickness = flooring_config.flooring_thickness
            
            floor_slab = (
                cq.Workplane("XY")
                .box(dimensions.front, dimensions.left, floor_thickness)
                .translate((0, 0, current_z))
            )
            
            # Add floor to collection
            if floors is None:
                floors = floor_slab
            else:
                floors = floors.union(floor_slab)
            
            # Move up by joist height + floor thickness + ceiling height for next floor
            if i < stories:
                current_z += joist_heights[i] + floor_thickness + ceiling_heights[i]
        
        return floors
