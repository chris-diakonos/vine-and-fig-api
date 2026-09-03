"""
Main building builder that combines all components.
"""
import cadquery as cq
from typing import Tuple, Dict, Any, Optional, List
from app.models.structure import Structure, ComponentVisibility
from app.services.foundation_builder import FoundationBuilder
from app.services.floor_builder import FloorBuilder
from app.services.sheathing_builder import SheathingBuilder
from app.services.roof_builder import RoofBuilder
from app.services.windows_builder import WindowsBuilder
from app.services.doors_builder import DoorsBuilder
from app.services.framing_builder import FramingBuilder
from app.services.cornice_builder import CorniceBuilder


class BuildingBuilder:
    """Orchestrates the construction of complete building model."""
    
    @staticmethod
    def calculate_ceiling_heights(
        stories: int,
        joist_heights: List[float],
        ceiling_heights: List[float]
    ) -> List[float]:
        """
        Calculate ceiling heights for each story.
        
        Args:
            stories: Number of stories
            joist_heights: List of joist heights for each floor
            ceiling_heights: List of ceiling heights for each story
            
        Returns:
            List of ceiling heights (cumulative z positions)
        """
        heights = []
        height = 0
        sill_height = joist_heights[0] if joist_heights else 10

        for story in range(1, stories + 1):
            
            if story == 1:
                height = sill_height + ceiling_heights[0]
            else:
                height = height + joist_heights[story - 1] + ceiling_heights[story - 1]
            
            heights.append(height)
        
        return heights
    
    @staticmethod
    def calculate_floor_heights(
        stories: int,
        joist_heights: List[float],
        ceiling_heights: List[float]
    ) -> List[float]:
        """
        Calculate floor heights for each story (static method for reuse).
        
        Args:
            stories: Number of stories
            joist_heights: List of joist heights for each floor
            ceiling_heights: List of ceiling heights for each story
            
        Returns:
            List of floor heights
        """
        heights = []
        height = 0
        sill_height = joist_heights[0] if joist_heights else 10

        for story in range(1, stories + 2):
            
            if story == 1:
                height = sill_height
            else:
                height = height + ceiling_heights[story - 2] + joist_heights[story - 1]
            
            heights.append(height)
        
        return heights
    
    @staticmethod
    def build(
        structure: Structure, 
        structure_hash: Optional[str] = None,
        component_visibility: Optional[ComponentVisibility] = None
    ) -> Tuple[cq.Assembly, Optional[Dict[str, Any]]]:
        """
        Build a complete building from structure specification.
        
        All components are added to a single assembly to ensure proper alignment
        and enable proper glTF export with component separation.
        
        Args:
            structure: Complete structure specification
            structure_hash: Optional structure hash for BOM tracking
            component_visibility: Optional visibility flags for each component (defaults to all visible)
            
        Returns:
            Tuple of (CadQuery Assembly with complete building geometry, BOM data dictionary)
        """
        # Default to all components visible if not specified
        if component_visibility is None:
            component_visibility = ComponentVisibility()
        
        floorplan = structure.floorplan
        dimensions = floorplan.dimensions
        
        
        # Get floorplan values with defaults
        stories = floorplan.stories
        raw_ceiling_heights = floorplan.ceiling_heights
        joist_heights = floorplan.joist_heights
        
        # Calculate ceiling and floor heights once
        calculated_ceiling_heights = BuildingBuilder.calculate_ceiling_heights(
            stories,
            joist_heights,
            raw_ceiling_heights
        )

        calculated_floor_heights = BuildingBuilder.calculate_floor_heights(
            stories,
            joist_heights,
            raw_ceiling_heights
        )

        # Calculate chair rail heights
        calculated_chair_rail_heights = []
        calculated_bay_heights = []
        calculated_bay_widths = []

        for idx, floor_height in enumerate(calculated_floor_heights):
            chair_rail_height = 30
            bay_height = chair_rail_height + 72
            bay_width = structure.windows[idx].bay_width
            calculated_chair_rail_heights.append(floor_height + chair_rail_height)
            calculated_bay_heights.append(floor_height + bay_height)
            calculated_bay_widths.append(bay_width)

        # Collect all opening locations (doors and windows) for framing and sheathing
        openings = []
        
        # Collect door openings
        if structure.doors:
            for door in structure.doors:
                if door.wall and door.position is not None:
                    floor = door.floor if door.floor is not None else 1
                    # Parse door size
                    size_parts = door.size.split('x')
                    width = float(size_parts[0]) if len(size_parts) == 2 else 36
                    height = float(size_parts[1]) if len(size_parts) == 2 else 80
                    openings.append({
                        'wall': door.wall,
                        'position': door.position,
                        'floor': floor,
                        'type': 'door',
                        'width': width,
                        'height': height
                    })
        
        # Collect window openings
        if structure.windows:
            # Check if windows have explicit locations
            has_explicit_locations = any(w.wall and w.position is not None and w.floor is not None for w in structure.windows)
            
            if has_explicit_locations:
                # Add explicitly located windows
                for window in structure.windows:
                    if window.wall and window.position is not None and window.floor is not None:
                        # Parse window size
                        size_parts = window.size.split('x')
                        width = float(size_parts[0]) if len(size_parts) == 2 else 24
                        height = float(size_parts[1]) if len(size_parts) == 2 else 36
                        openings.append({
                            'wall': window.wall,
                            'position': window.position,
                            'floor': window.floor,
                            'type': 'window',
                            'width': width,
                            'height': height
                        })
            else:
                # Add windows at all bays except door bays
                door_locations = {(d['wall'], d['position'], d['floor']) for d in openings}
                
                for story_idx in range(stories):
                    if story_idx >= len(structure.windows):
                        break
                    window = structure.windows[story_idx]
                    floor_number = story_idx + 1
                    
                    # Parse window size
                    size_parts = window.size.split('x')
                    width = float(size_parts[0]) if len(size_parts) == 2 else 24
                    height = float(size_parts[1]) if len(size_parts) == 2 else 36
                    
                    # Add window at each bay on each face (except door bays)
                    for face in ["front", "rear", "left", "right"]:
                        bays = getattr(floorplan.bays, face, []) if floorplan.bays else []
                        for bay_position in bays:
                            if (face, bay_position, floor_number) not in door_locations:
                                openings.append({
                                    'wall': face,
                                    'position': bay_position,
                                    'floor': floor_number,
                                    'type': 'window',
                                    'width': width,
                                    'height': height
                                })

        # Create main building assembly
        building_assembly = cq.Assembly()
        
        # Build foundation first
        # Foundation top is at z=0, foundation extends downward
        if component_visibility.foundation:
            foundation_assembly = FoundationBuilder.build(
                structure.foundation,
                dimensions
            )
            # Add all foundation components to the main assembly (colors are already set in foundation_builder)
            for name, obj_data in foundation_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    component_name = name if name else f"foundation_{len(building_assembly.children)}"
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.7, 0.7, 0.7))
        
        # Build framing (returns assembly and BOM data)
        # Framing starts at z=0 (sills sit on foundation top)
        bom_data = None
        if component_visibility.framing and structure_hash:
            try:
                framing_builder = FramingBuilder(structure, structure_hash, openings)
                framing_assembly, bom_data = framing_builder.build(
                    calculated_ceiling_heights,
                    calculated_floor_heights
                )
                
                # Add all framing components to the main assembly
                # Traverse the framing assembly and add each component (colors are already set in framing_builder)
                for name, obj_data in framing_assembly.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        # Use the original name from framing assembly or generate one
                        component_name = name if name else f"framing_{len(building_assembly.children)}"
                        building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.55, 0.45, 0.33))
                        
            except Exception as e:
                # If framing fails, continue without it but log the error
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Framing construction failed: {e}")
        
        # Build floors
        # Floors sit on top of joists (which sit on sills/girts)
        # Floor positions are calculated based on joist positions
        if component_visibility.floors:
            floor_assembly = FloorBuilder.build(
                structure.flooring,
                dimensions,
                stories,
                calculated_floor_heights
            )
            
            # Add all floor planks to the main assembly as individual components
            # Traverse the floor assembly and add each plank (colors are already set in floor_builder)
            for name, obj_data in floor_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    # Use the original name from floor assembly or generate one
                    component_name = name if name else f"floor_{len(building_assembly.children)}"
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.8, 0.7, 0.6))
        
        # Build sheathing
        # Sheathing boards positioned on exterior of studs
        if component_visibility.sheathing:
            sheathing_assembly = SheathingBuilder.build(
                structure.sheathing,
                dimensions,
                stories,
                calculated_floor_heights,
                calculated_chair_rail_heights,
                calculated_bay_heights,
                calculated_bay_widths,
                floorplan,
                openings=openings
            )
            
            # Add all sheathing boards to the main assembly as individual components
            # Traverse the sheathing assembly and add each board (colors are already set in sheathing_builder)
            for name, obj_data in sheathing_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    # Use the original name from sheathing assembly or generate one
                    component_name = name if name else f"sheathing_{len(building_assembly.children)}"
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.9, 0.85, 0.75))
        
        # Build roof
        if component_visibility.roof:
            roof_assembly = RoofBuilder.build(
                structure.roof,
                dimensions,
                stories,
                calculated_floor_heights
            )
            
            # Add all roof panels to the main assembly as individual components
            # Traverse the roof assembly and add each panel (colors are already set in roof_builder)
            for name, obj_data in roof_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    # Use the original name from roof assembly or generate one
                    component_name = name if name else f"roof_{len(building_assembly.children)}"
                    # Color is already set in roof_builder, preserve it from the assembly
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.3, 0.3, 0.3))
        
        # Add windows if specified
        if component_visibility.windows and structure.windows:
            # Collect door openings to avoid placing windows at door bays
            door_openings = []
            if structure.doors:
                for door in structure.doors:
                    if door.wall and door.position is not None:
                        floor = door.floor if door.floor is not None else 1
                        door_openings.append({
                            'wall': door.wall,
                            'position': door.position,
                            'floor': floor
                        })
            
            windows_assembly = WindowsBuilder.build(
                structure.windows,
                dimensions,
                stories,
                calculated_floor_heights,
                calculated_chair_rail_heights,
                floorplan,
                door_openings=door_openings
            )
            if windows_assembly is not None:
                # Add all windows to the main assembly (colors are already set in windows_builder)
                for name, obj_data in windows_assembly.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        component_name = name if name else f"window_{len(building_assembly.children)}"
                        building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.7, 0.9, 1.0))
        
        # Add doors if specified
        if component_visibility.doors and structure.doors:
            doors_assembly = DoorsBuilder.build(structure.doors, dimensions)
            if doors_assembly is not None:
                # Add all doors to the main assembly (colors are already set in doors_builder)
                for name, obj_data in doors_assembly.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        component_name = name if name else f"door_{len(building_assembly.children)}"
                        building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.5, 0.3, 0.2))
        
        # Build cornice at the top of the building
        cornice_assembly = CorniceBuilder.build(dimensions, dimensions.building_height, structure.roof.roof_type)
        if cornice_assembly is not None:
            # Add all cornice components to the main assembly (colors are already set in cornice_builder)
            for name, obj_data in cornice_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    component_name = name if name else f"cornice_{len(building_assembly.children)}"
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.8, 0.7, 0.6))
        
        return building_assembly, bom_data
