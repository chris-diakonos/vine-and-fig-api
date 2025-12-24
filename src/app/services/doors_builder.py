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
            
            # Create door (simplified)
            door_depth = door.thickness
            
            door_obj = (
                cq.Workplane("XY")
                .box(width, door_depth, height)
            )
            
            # Position door on appropriate wall
            if door.wall and door.position is not None and door.floor:
                positioned_door = DoorsBuilder._position_door(
                    door_obj,
                    door.wall,
                    door.position,
                    door.floor,
                    dimensions,
                    height
                )
                
                # Add door to assembly with color
                door_name = f"door_{i}"
                doors_assembly.add(positioned_door, name=door_name, color=cq.Color(0.5, 0.3, 0.2))  # Brown
        
        return doors_assembly if doors_assembly.children else None
    
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
        # Calculate vertical position (doors sit on the floor)
        floor_height = 120  # Default story height
        z_pos = (floor - 1) * floor_height + door_height / 2
        
        # Position based on wall
        if wall == "front":
            x_pos = position - dimensions.front / 2
            y_pos = -dimensions.left / 2
            door = door.translate((x_pos, y_pos, z_pos))
        elif wall == "rear":
            x_pos = position - dimensions.rear / 2
            y_pos = dimensions.left / 2
            door = door.translate((x_pos, y_pos, z_pos))
        elif wall == "left":
            x_pos = -dimensions.front / 2
            y_pos = position - dimensions.left / 2
            door = door.translate((x_pos, y_pos, z_pos))
        elif wall == "right":
            x_pos = dimensions.front / 2
            y_pos = position - dimensions.right / 2
            door = door.translate((x_pos, y_pos, z_pos))
        
        return door

