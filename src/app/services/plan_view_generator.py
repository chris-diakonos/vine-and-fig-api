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
        
        # Offset for margins
        offset_x = margin
        offset_y = margin
        
        # Collect all drawing elements
        elements = []
        
        # === EXTERIOR WALLS ===
        
        # Front wall (bottom)
        front_wall = cq.Workplane("XY").rect(front, wall_thickness).translate((offset_x + front/2, offset_y + left - wall_thickness/2))
        elements.append(front_wall)
        
        # Rear wall (top)
        rear_wall = cq.Workplane("XY").rect(rear, wall_thickness).translate((offset_x + rear/2, offset_y + wall_thickness/2))
        elements.append(rear_wall)
        
        # Left wall
        left_wall = cq.Workplane("XY").rect(wall_thickness, left).translate((offset_x + wall_thickness/2, offset_y + left/2))
        elements.append(left_wall)
        
        # Right wall
        right_wall = cq.Workplane("XY").rect(wall_thickness, right).translate((offset_x + front - wall_thickness/2, offset_y + right/2))
        elements.append(right_wall)
        
        # === CENTER HALL WALLS ===
        if floorplan_type == 'center-hall':
            # Calculate hall position
            building_center_x = front / 2
            hall_left_x = building_center_x - (hall_width / 2) + hall_offset
            hall_right_x = building_center_x + (hall_width / 2) + hall_offset
            
            # Left hall wall (vertical wall running from front to rear)
            left_hall_wall = cq.Workplane("XY").rect(wall_thickness, left - 2 * wall_thickness).translate((offset_x + hall_left_x + wall_thickness/2, offset_y + left/2))
            elements.append(left_hall_wall)
            
            # Right hall wall (vertical wall running from front to rear)
            right_hall_wall = cq.Workplane("XY").rect(wall_thickness, left - 2 * wall_thickness).translate((offset_x + hall_right_x - wall_thickness/2, offset_y + left/2))
            elements.append(right_hall_wall)
        
        elif floorplan_type == 'side-hall':
            # For side-hall, the hall runs along one side
            hall_wall_x = hall_width
            
            # Hall wall separates the hall from the main rooms
            hall_wall = cq.Workplane("XY").rect(wall_thickness, left - 2 * wall_thickness).translate((offset_x + hall_wall_x + wall_thickness/2, offset_y + left/2))
            elements.append(hall_wall)
        
        # === WINDOW AND DOOR OPENINGS ===
        # Note: For now, we'll show the walls without openings to avoid CadQuery 2D boolean operation issues
        # In a future version, we can implement proper window and door opening visualization
        
        # Create final workplane by unioning all elements
        if elements:
            wp = elements[0]
            for element in elements[1:]:
                wp = wp.union(element)
        else:
            wp = cq.Workplane("XY")
        
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

