"""
Windows and doors builder service using CadQuery.
"""
import cadquery as cq
from typing import List, Optional
from app.models.openings import Window, Door
from app.models.floorplan import Dimensions


class OpeningsBuilder:
    """Builds window and door geometry using CadQuery."""
    
    @staticmethod
    def build_windows(windows: List[Window], dimensions: Dimensions) -> Optional[cq.Workplane]:
        """
        Build window openings and frames.
        
        Args:
            windows: List of window specifications
            dimensions: Building dimensions
            
        Returns:
            CadQuery Workplane with window geometry, or None if no windows
        """
        if not windows:
            return None
        
        all_windows = None
        
        for window in windows:
            # Parse window size
            size_parts = window.size.split('x')
            if len(size_parts) == 2:
                width = float(size_parts[0])
                height = float(size_parts[1])
            else:
                width, height = 24, 36  # Default size
            
            # Create window frame (simplified)
            window_depth = window.thickness
            
            window_obj = (
                cq.Workplane("XY")
                .box(width, window_depth, height)
            )
            
            # Position window on appropriate wall
            if window.wall and window.position is not None and window.floor:
                positioned_window = OpeningsBuilder._position_opening(
                    window_obj,
                    window.wall,
                    window.position,
                    window.floor,
                    dimensions,
                    height
                )
                
                if all_windows is None:
                    all_windows = positioned_window
                else:
                    all_windows = all_windows.union(positioned_window)
        
        return all_windows
    
    @staticmethod
    def build_doors(doors: List[Door], dimensions: Dimensions) -> Optional[cq.Workplane]:
        """
        Build door openings and frames.
        
        Args:
            doors: List of door specifications
            dimensions: Building dimensions
            
        Returns:
            CadQuery Workplane with door geometry, or None if no doors
        """
        if not doors:
            return None
        
        all_doors = None
        
        for door in doors:
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
                positioned_door = OpeningsBuilder._position_opening(
                    door_obj,
                    door.wall,
                    door.position,
                    door.floor,
                    dimensions,
                    height
                )
                
                if all_doors is None:
                    all_doors = positioned_door
                else:
                    all_doors = all_doors.union(positioned_door)
        
        return all_doors
    
    @staticmethod
    def _position_opening(
        opening: cq.Workplane,
        wall: str,
        position: float,
        floor: int,
        dimensions: Dimensions,
        opening_height: float
    ) -> cq.Workplane:
        """
        Position an opening (window or door) on a specific wall.
        
        Args:
            opening: The opening geometry
            wall: Wall identifier (front, rear, left, right)
            position: Position along wall from left
            floor: Floor number (1-indexed)
            dimensions: Building dimensions
            opening_height: Height of the opening
            
        Returns:
            Positioned opening
        """
        # Calculate vertical position (simplified - assume 12" above floor)
        floor_height = 120  # Default story height
        z_pos = (floor - 1) * floor_height + opening_height / 2 + 12
        
        # Position based on wall
        if wall == "front":
            x_pos = position - dimensions.front / 2
            y_pos = -dimensions.left / 2
            opening = opening.translate((x_pos, y_pos, z_pos))
        elif wall == "rear":
            x_pos = position - dimensions.rear / 2
            y_pos = dimensions.left / 2
            opening = opening.translate((x_pos, y_pos, z_pos))
        elif wall == "left":
            x_pos = -dimensions.front / 2
            y_pos = position - dimensions.left / 2
            opening = opening.translate((x_pos, y_pos, z_pos))
        elif wall == "right":
            x_pos = dimensions.front / 2
            y_pos = position - dimensions.right / 2
            opening = opening.translate((x_pos, y_pos, z_pos))
        
        return opening
