"""
Doors builder service using CadQuery.
"""
import cadquery as cq
from typing import List, Optional
from app.models.openings import Door
from app.models.floorplan import Dimensions


class DoorsBuilder:
    """Builds door geometry using CadQuery."""
    
    @staticmethod
    def build(doors: List[Door], dimensions: Dimensions) -> Optional[cq.Assembly]:
        """
        Build door openings and frames.
        
        Args:
            doors: List of door specifications
            dimensions: Building dimensions
            
        Returns:
            CadQuery Assembly with door geometry and colors, or None if no doors
        """
        if not doors:
            return None
        
        doors_assembly = cq.Assembly()
        
        for i, door in enumerate(doors):
            # Parse door size
            size_parts = door.size.split('x')
            if len(size_parts) == 2:
                width = float(size_parts[0])
                height = float(size_parts[1])
            else:
                width, height = 36, 80  # Default size
            
            # Create door based on configuration
            if door.configuration == "six-panel" and door.panel_type == "raised-panel":
                door_obj = DoorsBuilder._build_six_panel_raised_door(
                    door, width, height
                )
            else:
                # Fallback to simple box
                door_obj = (
                    cq.Workplane("XY")
                    .box(width, door.thickness, height)
                )
            
            # Position door on appropriate wall
            # Default floor to 1 (ground floor) if not specified
            if door.wall and door.position is not None:
                floor = door.floor if door.floor is not None else 1
                positioned_door = DoorsBuilder._position_door(
                    door_obj,
                    door.wall,
                    door.position,
                    floor,
                    dimensions,
                    height
                )
                
                # Add door to assembly with color
                door_name = f"door_{i}"
                doors_assembly.add(positioned_door, name=door_name, color=cq.Color(0.5, 0.3, 0.2))  # Brown
        
        return doors_assembly if doors_assembly.children else None
    
    @staticmethod
    def _build_six_panel_raised_door(
        door: Door,
        width: float,
        height: float
    ) -> cq.Workplane:
        """
        Build a six-panel raised-panel door.
        
        Args:
            door: Door specification with stile_widths, rail_widths, panel_widths
            width: Door width
            height: Door height
            
        Returns:
            CadQuery Workplane with door geometry
        """
        thickness = door.thickness
        
        # Extract stile and rail dimensions
        left_stile = door.stile_widths[0]
        mid_stile = door.stile_widths[1]
        right_stile = door.stile_widths[2]
        
        top_rail = door.rail_widths[0]
        upper_mid_rail = door.rail_widths[1]
        lower_mid_rail = door.rail_widths[2]
        bottom_rail = door.rail_widths[3]
        
        left_panel_width = door.panel_widths[0]
        right_panel_width = door.panel_widths[1]
        
        # Create base door slab
        door_slab = cq.Workplane("XY").box(width, thickness, height)
        
        # Calculate panel positions and heights
        # Three rows of panels
        panel_depth = 0.25  # Recess depth for panels
        raised_height = 0.125  # Height of raised portion
        
        # Calculate vertical positions for three rows
        top_panel_start = height / 2 - top_rail
        upper_mid_panel_start = top_panel_start - (height - top_rail - upper_mid_rail - lower_mid_rail - bottom_rail) / 3
        lower_mid_panel_start = upper_mid_panel_start - (height - top_rail - upper_mid_rail - lower_mid_rail - bottom_rail) / 3
        
        # Calculate panel heights
        panel_height = (height - top_rail - upper_mid_rail - lower_mid_rail - bottom_rail) / 3
        
        # Create panels for all six positions (3 rows x 2 columns)
        for row in range(3):
            if row == 0:
                panel_z = top_panel_start - panel_height / 2
            elif row == 1:
                panel_z = upper_mid_panel_start - panel_height / 2
            else:
                panel_z = lower_mid_panel_start - panel_height / 2
            
            # Left panel - cut recess and add raised center
            left_panel_x = -width / 2 + left_stile + left_panel_width / 2
            
            # Cut panel recess from door
            panel_recess = (
                cq.Workplane("XY")
                .box(left_panel_width, panel_depth * 2, panel_height)
                .translate((left_panel_x, thickness / 2 - panel_depth, panel_z))
            )
            door_slab = door_slab.cut(panel_recess)
            
            # Add raised panel center
            raised_panel = (
                cq.Workplane("XY")
                .box(left_panel_width - 2, raised_height, panel_height - 2)
                .translate((left_panel_x, thickness / 2 - panel_depth + raised_height / 2, panel_z))
            )
            door_slab = door_slab.union(raised_panel)
            
            # Right panel - cut recess and add raised center
            right_panel_x = width / 2 - right_stile - right_panel_width / 2
            
            # Cut panel recess from door
            panel_recess = (
                cq.Workplane("XY")
                .box(right_panel_width, panel_depth * 2, panel_height)
                .translate((right_panel_x, thickness / 2 - panel_depth, panel_z))
            )
            door_slab = door_slab.cut(panel_recess)
            
            # Add raised panel center
            raised_panel = (
                cq.Workplane("XY")
                .box(right_panel_width - 2, raised_height, panel_height - 2)
                .translate((right_panel_x, thickness / 2 - panel_depth + raised_height / 2, panel_z))
            )
            door_slab = door_slab.union(raised_panel)
        
        return door_slab
    
    @staticmethod
    def _position_door(
        door: cq.Workplane,
        wall: str,
        position: float,
        floor: int,
        dimensions: Dimensions,
        door_height: float
    ) -> cq.Workplane:
        """
        Position a door on a specific wall.
        
        Args:
            door: The door geometry
            wall: Wall identifier (front, rear, left, right)
            position: Position along wall from left
            floor: Floor number (1-indexed)
            dimensions: Building dimensions
            door_height: Height of the door
            
        Returns:
            Positioned door
        """
        # Calculate vertical position
        # Sill sits on finished floor at z=11 (joists 0-10, deck 10-11)
        floor_height = 120  # Default story height
        joist_and_deck_height = 11  # Height of floor structure
        
        # For floor 1, sill starts at z=11, so center is at z=11 + door_height/2
        z_pos = (floor - 1) * floor_height + joist_and_deck_height + door_height / 2
        
        # Door depth for positioning
        door_depth = 1.75  # Standard door thickness
        
        # Position based on wall (matching windows_builder coordinate system)
        if wall == "front":
            x_pos = position
            y_pos = door_depth / 2
            door = door.translate((x_pos, y_pos, z_pos))
        elif wall == "rear":
            x_pos = position
            y_pos = -dimensions.right + door_depth / 2
            door = door.translate((x_pos, y_pos, z_pos))
        elif wall == "left":
            x_pos = door_depth / 2
            y_pos = -position
            door = door.translate((x_pos, y_pos, z_pos))
        elif wall == "right":
            x_pos = dimensions.front + door_depth / 2
            y_pos = -position
            door = door.translate((x_pos, y_pos, z_pos))
        
        return door

