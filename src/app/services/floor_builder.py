"""
Floor builder service using CadQuery.
"""
import cadquery as cq
from typing import List, Optional
from app.models.building import Flooring
from app.models.floorplan import Dimensions
from app.services.framing_builder import FramingBuilder


class FloorBuilder:
    """Builds floor geometry using CadQuery."""
    
    @staticmethod
    def build(
        flooring: List[Flooring],
        dimensions: Dimensions,
        stories: int,
        ceiling_heights: Optional[List[float]] = None,
        joist_heights: Optional[List[float]] = None
    ) -> cq.Assembly:
        """
        Build floor structures for all stories using individual tongue-and-groove planks.
        
        Args:
            flooring: List of flooring specifications (one per story + attic)
            dimensions: Building dimensions
            stories: Number of stories
            ceiling_heights: Ceiling heights for each story
            joist_heights: Joist heights for each floor
            
        Returns:
            CadQuery Assembly with individual planks as separate components
        """
        # Use defaults if not specified
        if ceiling_heights is None:
            ceiling_heights = [120] * stories  # 10 feet default
        if joist_heights is None:
            joist_heights = [10] * (stories + 1)  # Include foundation floor
        
        # Calculate floor heights using the same method as FramingBuilder
        floor_heights = FramingBuilder.calculate_floor_heights(
            stories,
            joist_heights,
            ceiling_heights
        )
        
        # Create assembly to hold individual planks
        floor_assembly = cq.Assembly()
        
        # If flooring array is empty or insufficient, create default config
        from app.models.building import Flooring as FlooringModel
        default_flooring = FlooringModel(
            flooring_type="tongue-and-groove",
            flooring_species="pine",
            flooring_thickness=1.0,
            flooring_width=10.0,
            flooring_exposure=9.25
        )
        
        # Build floors for each story
        for i in range(stories + 1):  # +1 for foundation floor (first floor)
            # Get flooring config for this floor
            if len(flooring) > 0:
                flooring_config = flooring[i] if i < len(flooring) else flooring[0]
            else:
                flooring_config = default_flooring
            
            # Get floor height from calculated heights
            floor_height = floor_heights[i]
            floor_thickness = flooring_config.flooring_thickness
            floor_center_z = floor_height + (floor_thickness / 2)
            
            # Build individual planks for this floor and add to assembly
            FloorBuilder._build_floor_planks(
                floor_assembly,
                flooring_config,
                dimensions,
                floor_center_z,
                i  # floor index for naming
            )
        
        return floor_assembly
    
    @staticmethod
    def _build_floor_planks(
        assembly: cq.Assembly,
        flooring_config: Flooring,
        dimensions: Dimensions,
        floor_center_z: float,
        floor_index: int
    ) -> None:
        """
        Build individual tongue-and-groove planks for a floor and add to assembly.
        
        Args:
            assembly: Assembly to add planks to
            flooring_config: Flooring configuration
            dimensions: Building dimensions
            floor_center_z: Z position of floor center
            floor_index: Index of the floor (for naming)
        """
        flooring_width = flooring_config.flooring_width
        flooring_exposure = flooring_config.flooring_exposure
        floor_thickness = flooring_config.flooring_thickness
        plank_length = dimensions.left
        
        # Small visual gap between planks (in inches) for visual distinction
        plank_gap = 0.0625  # 0.0625 inches = ~1.59mm - small but visible
        
        # Calculate tongue dimensions
        # Tongue is 1/2 of the difference between width and exposure
        overlap = flooring_width - flooring_exposure
        tongue_width = overlap / 2
        groove_width = overlap / 2
        
        # Calculate number of planks needed
        # Planks are spaced by exposure + gap, starting from one edge
        floor_length = dimensions.front
        spacing = flooring_exposure + plank_gap
        num_planks = int(floor_length / spacing) + 2  # Add extra to ensure coverage
        
        for i in range(num_planks):
            # Calculate plank position (center of plank)
            # First plank starts at flooring_width/2 (left edge at 0)
            # Subsequent planks are spaced by exposure + gap
            plank_x = (flooring_width / 2) + (i * spacing)
            
            # Create plank with tongue-and-groove
            plank = FloorBuilder._create_tongue_groove_plank(
                flooring_width,
                plank_length,  # Plank runs along left dimension (Y axis)
                floor_thickness,
                tongue_width,
                groove_width
            )
            
            # Position plank
            plank = plank.translate((plank_x, plank_length/2, floor_center_z))
            
            # Add plank to assembly as individual component
            plank_name = f"floor_plank_floor{floor_index}_plank{i}"
            assembly.add(plank, name=plank_name)
    
    @staticmethod
    def _create_tongue_groove_plank(
        width: float,
        length: float,
        thickness: float,
        tongue_width: float,
        groove_width: float
    ) -> cq.Workplane:
        """
        Create a single tongue-and-groove plank.
        
        The plank has:
        - A tongue on one edge (extending beyond the main body)
        - A groove on the other edge (recessed into the main body)
        
        Args:
            width: Width of the plank (including tongue/groove)
            length: Length of the plank
            thickness: Thickness of the plank
            tongue_width: Width of the tongue extension
            groove_width: Width of the groove recess
            
        Returns:
            CadQuery Workplane with the plank geometry
        """
        # Main plank body is the exposed width
        # Tongue extends beyond on one side, groove recesses on the other
        main_width = width - tongue_width - groove_width  # This equals flooring_exposure
        
        # Create main body (the visible/exposed part)
        main_body = (
            cq.Workplane("XY")
            .box(main_width, length, thickness)
        )
        
        # Add tongue on one side (positive X direction)
        # Tongue extends outward from the main body
        tongue = (
            cq.Workplane("XY")
            .box(tongue_width, length, thickness)
            .translate((main_width / 2 + tongue_width / 2, 0, 0))
        )
        
        # Create groove by cutting a recess into the main body
        # Groove is on the negative X side (opposite from tongue)
        groove_cutout = (
            cq.Workplane("XY")
            .box(groove_width, length, thickness * 0.6)  # Groove depth (60% of thickness)
            .translate((-(main_width / 2 + groove_width / 2), 0, -thickness * 0.2))
        )
        
        # Combine main body and tongue, then cut groove
        plank = main_body.union(tongue).cut(groove_cutout)
        
        return plank
