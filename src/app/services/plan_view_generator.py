"""
Plan view generator for creating architectural-style 2D floor plans.
Uses CadQuery 2D for precise geometric drawings.
"""
from pathlib import Path
from typing import List, Optional
import logging
import cadquery as cq

from app.services.cadquery_drawing_components import CadQueryDrawingComponents

logger = logging.getLogger(__name__)


class PlanViewGenerator:
    """Generates architectural-style 2D floor plan drawings."""
    
    @staticmethod
    def generate_plan_svg(
        floorplan_type: str,
        dimensions: dict,
        hall_width: float,
        hall_offset: float,
        stories: int,
        bays: Optional[dict] = None,
        windows: Optional[List] = None,
        doors: Optional[List] = None,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate an architectural floor plan in SVG format using CadQuery 2D.
        
        Args:
            floorplan_type: 'center-hall' or 'side-hall'
            dimensions: Building dimensions (front, rear, left, right)
            hall_width: Width of the center hall
            hall_offset: Offset of hall from center
            stories: Number of stories (for labeling)
            bays: Bay centerlines for window placement
            windows: Window configurations (with bay_width)
            doors: Door specifications (with bay_width and location)
            output_path: Path to save the SVG file
            
        Returns:
            SVG content as string
        """
        # Building dimensions (nominal/overall)
        front = dimensions['front']
        rear = dimensions['rear']
        left = dimensions['left']
        right = dimensions['right']
        
        # Wall thickness (full 4" timber frame wall)
        wall_thickness = 4
        
        # Debug logging
        logger.info(f"Generating plan view for {floorplan_type}")
        logger.info(f"Dimensions: front={front}, rear={rear}, left={left}, right={right}")
        logger.info(f"Hall: width={hall_width}, offset={hall_offset}")
        logger.info(f"Bays data: {bays}")
        logger.info(f"Windows count: {len(windows) if windows else 0}")
        logger.info(f"Doors count: {len(doors) if doors else 0}")
        
        # Calculate view dimensions with margins
        margin = 40
        view_width = front + (2 * margin)
        view_height = left + (2 * margin)
        
        # Start with a 2D workplane
        wp = cq.Workplane("XY")
        
        # Offset for margins
        offset_x = margin
        offset_y = margin
        
        # === EXTERIOR WALLS ===
        
        # Front wall (bottom)
        front_wall = CadQueryDrawingComponents.create_wall_2d(
            x=offset_x,
            y=offset_y + left - wall_thickness,
            width=front,
            height=wall_thickness,
            wall_thickness=wall_thickness
        )
        wp = wp.union(front_wall)
        
        # Rear wall (top)
        rear_wall = CadQueryDrawingComponents.create_wall_2d(
            x=offset_x,
            y=offset_y,
            width=rear,
            height=wall_thickness,
            wall_thickness=wall_thickness
        )
        wp = wp.union(rear_wall)
        
        # Left wall
        left_wall = CadQueryDrawingComponents.create_wall_2d(
            x=offset_x,
            y=offset_y,
            width=wall_thickness,
            height=left,
            wall_thickness=wall_thickness
        )
        wp = wp.union(left_wall)
        
        # Right wall
        right_wall = CadQueryDrawingComponents.create_wall_2d(
            x=offset_x + front - wall_thickness,
            y=offset_y,
            width=wall_thickness,
            height=right,
            wall_thickness=wall_thickness
        )
        wp = wp.union(right_wall)
        
        # === CENTER HALL WALLS ===
        if floorplan_type == 'center-hall':
            # Calculate hall position
            building_center_x = front / 2
            hall_left_x = building_center_x - (hall_width / 2) + hall_offset
            hall_right_x = building_center_x + (hall_width / 2) + hall_offset
            
            # Left hall wall (vertical wall running from front to rear)
            left_hall_wall = CadQueryDrawingComponents.create_wall_2d(
                x=offset_x + hall_left_x,
                y=offset_y + wall_thickness,
                width=wall_thickness,
                height=left - 2 * wall_thickness,
                wall_thickness=wall_thickness
            )
            wp = wp.union(left_hall_wall)
            
            # Right hall wall (vertical wall running from front to rear)
            right_hall_wall = CadQueryDrawingComponents.create_wall_2d(
                x=offset_x + hall_right_x - wall_thickness,
                y=offset_y + wall_thickness,
                width=wall_thickness,
                height=left - 2 * wall_thickness,
                wall_thickness=wall_thickness
            )
            wp = wp.union(right_hall_wall)
        
        elif floorplan_type == 'side-hall':
            # For side-hall, the hall runs along one side
            hall_wall_x = hall_width
            
            # Hall wall separates the hall from the main rooms
            hall_wall = CadQueryDrawingComponents.create_wall_2d(
                x=offset_x + hall_wall_x,
                y=offset_y + wall_thickness,
                width=wall_thickness,
                height=left - 2 * wall_thickness,
                wall_thickness=wall_thickness
            )
            wp = wp.union(hall_wall)
        
        # === WINDOW OPENINGS ===
        # Use first story window config if available (windows[0])
        window_bay_width = 29.25  # Default window bay width
        if windows and len(windows) > 0:
            first_story_window = windows[0]
            if isinstance(first_story_window, dict) and 'bay_width' in first_story_window:
                window_bay_width = first_story_window['bay_width']
        
        # Draw window openings on each wall using bay centerlines
        if bays and isinstance(bays, dict):
            # Front wall windows
            if 'front' in bays and len(bays['front']) > 1:
                for bay_x in bays['front'][1:]:  # Skip first element (count)
                    window_x = offset_x + bay_x - (window_bay_width / 2)
                    window_y = offset_y + left - wall_thickness
                    # Create window opening (white rectangle)
                    window_opening = cq.Workplane("XY").rect(window_bay_width, wall_thickness).translate((window_x + window_bay_width/2, window_y + wall_thickness/2))
                    wp = wp.cut(window_opening)
            
            # Rear wall windows
            if 'rear' in bays and len(bays['rear']) > 1:
                for bay_x in bays['rear'][1:]:
                    window_x = offset_x + bay_x - (window_bay_width / 2)
                    window_y = offset_y
                    window_opening = cq.Workplane("XY").rect(window_bay_width, wall_thickness).translate((window_x + window_bay_width/2, window_y + wall_thickness/2))
                    wp = wp.cut(window_opening)
            
            # Left wall windows
            if 'left' in bays and len(bays['left']) > 1:
                for bay_y in bays['left'][1:]:
                    window_x = offset_x
                    window_y = offset_y + bay_y - (window_bay_width / 2)
                    window_opening = cq.Workplane("XY").rect(wall_thickness, window_bay_width).translate((window_x + wall_thickness/2, window_y + window_bay_width/2))
                    wp = wp.cut(window_opening)
            
            # Right wall windows
            if 'right' in bays and len(bays['right']) > 1:
                for bay_y in bays['right'][1:]:
                    window_x = offset_x + front - wall_thickness
                    window_y = offset_y + bay_y - (window_bay_width / 2)
                    window_opening = cq.Workplane("XY").rect(wall_thickness, window_bay_width).translate((window_x + wall_thickness/2, window_y + window_bay_width/2))
                    wp = wp.cut(window_opening)
        
        # === DOOR OPENINGS ===
        if doors and len(doors) > 0:
            for door in doors:
                if not isinstance(door, dict):
                    continue
                
                wall = door.get('wall')
                position = door.get('position', 0)
                door_bay_width = door.get('bay_width', 36.5)  # Default door bay width
                
                # Draw door opening based on wall location
                if wall == 'front':
                    door_x = offset_x + position - (door_bay_width / 2)
                    door_y = offset_y + left - wall_thickness
                    door_opening = cq.Workplane("XY").rect(door_bay_width, wall_thickness).translate((door_x + door_bay_width/2, door_y + wall_thickness/2))
                    wp = wp.cut(door_opening)
                elif wall == 'rear':
                    door_x = offset_x + position - (door_bay_width / 2)
                    door_y = offset_y
                    door_opening = cq.Workplane("XY").rect(door_bay_width, wall_thickness).translate((door_x + door_bay_width/2, door_y + wall_thickness/2))
                    wp = wp.cut(door_opening)
                elif wall == 'left':
                    door_x = offset_x
                    door_y = offset_y + position - (door_bay_width / 2)
                    door_opening = cq.Workplane("XY").rect(wall_thickness, door_bay_width).translate((door_x + wall_thickness/2, door_y + door_bay_width/2))
                    wp = wp.cut(door_opening)
                elif wall == 'right':
                    door_x = offset_x + front - wall_thickness
                    door_y = offset_y + position - (door_bay_width / 2)
                    door_opening = cq.Workplane("XY").rect(wall_thickness, door_bay_width).translate((door_x + wall_thickness/2, door_y + door_bay_width/2))
                    wp = wp.cut(door_opening)
        
        # Export to SVG
        svg_content = CadQueryDrawingComponents.export_to_svg(wp, str(output_path) if output_path else None)
        
        # Add SVG wrapper with proper dimensions and background
        svg_wrapper = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{view_width}" height="{view_height}" viewBox="0 0 {view_width} {view_height}">
  <!-- Generated Floor Plan - {floorplan_type} -->
  <rect width="{view_width}" height="{view_height}" fill="#f8f8f0"/>
  {svg_content}
  <!-- Labels -->
  <text x="{view_width / 2}" y="{view_height - 10}" text-anchor="middle" font-family="serif" font-size="12" fill="black">
    Floor Plan - {floorplan_type.replace("-", " ").title()}
  </text>
  <text x="{view_width / 2}" y="15" text-anchor="middle" font-family="sans-serif" font-size="10" fill="gray">
    {front / 12:.1f}\' × {left / 12:.1f}\'
  </text>
</svg>'''
        
        # Save to file if path provided
        if output_path:
            output_path.write_text(svg_wrapper, encoding='utf-8')
            logger.info(f"Generated plan view SVG: {output_path}")
        
        return svg_wrapper
    
    @staticmethod
    def generate_plan_with_windows(
        floorplan_type: str,
        dimensions: dict,
        hall_width: float,
        hall_offset: float,
        stories: int,
        bays: Optional[dict] = None,
        windows: Optional[List] = None,
        doors: Optional[List] = None,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate floor plan with window and door openings marked.
        
        (Deprecated: This method is now just an alias to generate_plan_svg)
        """
        return PlanViewGenerator.generate_plan_svg(
            floorplan_type,
            dimensions,
            hall_width,
            hall_offset,
            stories,
            bays,
            windows,
            doors,
            output_path
        )

