"""
Section view generator for creating architectural-style 2D section drawings.
Uses CadQuery 2D for precise geometric drawings.
"""
from pathlib import Path
from typing import List, Optional
import logging
import math
import cadquery as cq

from app.services.cadquery_drawing_components import CadQueryDrawingComponents

logger = logging.getLogger(__name__)


class SectionViewGenerator:
    """Generates architectural-style 2D section drawings."""
    
    @staticmethod
    def generate_section_svg(
        dimensions: dict,
        stories: int,
        ceiling_heights: List[float],
        joist_heights: List[float],
        foundation_courses: int,
        foundation_block_height: float,
        foundation_block_joint: float,
        roof_pitch: float,
        roof_type: str,
        roof_shed_length: float = 0,
        floorplan_type: str = 'center-hall',
        hall_width: float = 60,
        hall_offset: float = 0,
        windows: Optional[List] = None,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate an architectural section drawing in SVG format.
        
        Args:
            dimensions: Building dimensions (front, left, building_height)
            stories: Number of stories
            ceiling_heights: List of ceiling heights per story
            joist_heights: List of joist heights per floor
            foundation_courses: Number of foundation block courses
            foundation_block_height: Height of each foundation block
            foundation_block_joint: Mortar joint thickness
            roof_pitch: Roof pitch (rise over 12" run)
            roof_type: Type of roof (side-gable, front-gable, etc.)
            floorplan_type: Type of floorplan (center-hall, side-hall)
            hall_width: Width of the hall
            hall_offset: Offset of hall from center
            windows: Window configurations (with size info)
            output_path: Path to save the SVG file
            
        Returns:
            SVG content as string
        """
        # Get building dimensions
        building_width = dimensions['front']
        building_depth = dimensions['left']
        total_height = dimensions['building_height']
        
        # Wall and sill dimensions
        wall_thickness = 4
        window_sill_height = 36  # Height from floor to window sill (typical)
        
        # Calculate foundation height
        foundation_height = foundation_courses * (foundation_block_height + foundation_block_joint)
        
        # Calculate view dimensions with margins
        margin = 60
        view_width = building_width + (2 * margin)
        view_height = total_height + foundation_height + 80 + (2 * margin)
        
        # Offset for margins
        offset_x = margin
        offset_y = margin + 40  # Extra top margin for roof
        
        # Collect all drawing elements
        elements = []
        
        # Ground line (create as a thin rectangle instead of a line)
        ground_y = offset_y + total_height + foundation_height
        ground_line = cq.Workplane("XY").rect(view_width, 2).translate((view_width/2, ground_y))
        elements.append(ground_line)
        
        # === FOUNDATION ===
        foundation_y = offset_y + total_height
        foundation = cq.Workplane("XY").rect(building_width, foundation_height).translate((offset_x + building_width/2, foundation_y + foundation_height/2))
        elements.append(foundation)
        
        # === FLOOR LEVELS ===
        
        current_z = 0  # Start from bottom of first floor
        floor_positions = []
        
        for i in range(stories):
            floor_y = offset_y + total_height - current_z
            floor_positions.append(floor_y)
            
            # Floor joist (thick line)
            joist_height = joist_heights[i] if i < len(joist_heights) else 10
            floor_joist = cq.Workplane("XY").rect(building_width, joist_height).translate((offset_x + building_width/2, floor_y - joist_height/2))
            elements.append(floor_joist)
            
            # Move up by joist height + ceiling height
            current_z += joist_height + ceiling_heights[i]
        
        # Add ceiling joists at top
        ceiling_joist_y = offset_y + total_height - current_z
        ceiling_joist_height = joist_heights[-1] if len(joist_heights) > stories else 8
        ceiling_joist = cq.Workplane("XY").rect(building_width, ceiling_joist_height).translate((offset_x + building_width/2, ceiling_joist_y - ceiling_joist_height/2))
        elements.append(ceiling_joist)
        
        # === EXTERIOR WALLS ===
        
        # Left wall
        left_wall = cq.Workplane("XY").rect(wall_thickness, total_height).translate((offset_x + wall_thickness/2, offset_y + total_height/2))
        elements.append(left_wall)
        
        # Right wall
        right_wall = cq.Workplane("XY").rect(wall_thickness, total_height).translate((offset_x + building_width - wall_thickness/2, offset_y + total_height/2))
        elements.append(right_wall)
        
        # === INTERIOR WALLS (HALL) ===
        
        if floorplan_type == 'center-hall':
            # Calculate hall positions (same as plan view)
            building_center_x = building_width / 2
            hall_center_x = building_center_x + hall_offset
            hall_left_x = hall_center_x - (hall_width / 2)
            hall_right_x = hall_center_x + (hall_width / 2)
            
            # Draw hall walls for each story
            for story_idx in range(stories):
                if story_idx < len(floor_positions):
                    # Get floor and ceiling positions for this story
                    floor_y = floor_positions[story_idx]  # Top of floor joist
                    joist_height = joist_heights[story_idx] if story_idx < len(joist_heights) else 10
                    ceiling_height = ceiling_heights[story_idx]
                    
                    # Wall runs from floor joist bottom to ceiling joist bottom
                    wall_bottom_y = floor_y  # Bottom of floor joist
                    wall_height = joist_height + ceiling_height
                    wall_top_y = wall_bottom_y - wall_height
                    
                    # Left hall wall
                    left_hall_wall = cq.Workplane("XY").rect(wall_thickness, wall_height).translate((offset_x + hall_left_x + wall_thickness/2, wall_top_y + wall_height/2))
                    elements.append(left_hall_wall)
                    
                    # Right hall wall
                    right_hall_wall = cq.Workplane("XY").rect(wall_thickness, wall_height).translate((offset_x + hall_right_x - wall_thickness/2, wall_top_y + wall_height/2))
                    elements.append(right_hall_wall)
        
        elif floorplan_type == 'side-hall':
            # Side hall wall position
            hall_wall_x = hall_width
            
            # Draw hall wall for each story
            for story_idx in range(stories):
                if story_idx < len(floor_positions):
                    floor_y = floor_positions[story_idx]
                    joist_height = joist_heights[story_idx] if story_idx < len(joist_heights) else 10
                    ceiling_height = ceiling_heights[story_idx]
                    
                    # Wall runs from floor joist bottom to ceiling joist bottom
                    wall_height = joist_height + ceiling_height
                    wall_top_y = floor_y - wall_height
                    
                    # Hall dividing wall
                    hall_wall = cq.Workplane("XY").rect(wall_thickness, wall_height).translate((offset_x + hall_wall_x + wall_thickness/2, wall_top_y + wall_height/2))
                    elements.append(hall_wall)
        
        # === WINDOWS ===
        
        logger.info(f"Drawing windows: stories={stories}, windows_available={len(windows) if windows else 0}")
        logger.info(f"Floor positions: {floor_positions}")
        
        # Draw windows on each story
        for story_idx in range(stories):
            if windows and story_idx < len(windows):
                window_config = windows[story_idx]
                logger.info(f"Story {story_idx}: window_config type={type(window_config)}, data={window_config}")
                if isinstance(window_config, dict):
                    # Parse window size (e.g., "8x10" -> width=8, height=10)
                    size = window_config.get('size', '8x10')
                    window_width, window_height = [float(x) for x in size.split('x')]
                    
                    # Get window operation and configuration
                    operation = window_config.get('operation', 'single-hung')
                    configuration = window_config.get('configuration', '6/6')
                    
                    # Get chair_rail_height (window sill height) from config
                    window_sill_height = window_config.get('chair_rail_height', 28)
                    
                    # Window position on this floor
                    floor_base_y = floor_positions[story_idx]
                    window_y = floor_base_y - window_sill_height - window_height
                    
                    logger.info(f"Window {story_idx}: size={window_width}x{window_height}, floor_y={floor_base_y}, window_y={window_y}, sill_height={window_sill_height}")
                    
                    # Left wall window (in section, window shows as wall thickness)
                    window_x_left = offset_x
                    window_left = cq.Workplane("XY").rect(wall_thickness, window_height).translate((window_x_left + wall_thickness/2, window_y + window_height/2))
                    elements.append(window_left)
                    logger.info(f"Drew left window at x={window_x_left}, y={window_y}")
                    
                    # Right wall window
                    window_x_right = offset_x + building_width - wall_thickness
                    window_right = cq.Workplane("XY").rect(wall_thickness, window_height).translate((window_x_right + wall_thickness/2, window_y + window_height/2))
                    elements.append(window_right)
        
        # === ROOF ===
        
        roof_base_y = offset_y
        
        # Create roof using CadQuery
        roof_2d = CadQueryDrawingComponents.create_roof_2d(
            x=offset_x,
            y=roof_base_y,
            width=building_width,
            roof_type=roof_type,
            roof_pitch=roof_pitch,
            roof_overhang=0,  # No overhang in section view
            roof_shed_length=roof_shed_length
        )
        elements.append(roof_2d)
        
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
  <!-- Generated Section View -->
  <rect width="{view_width}" height="{view_height}" fill="#f8f8f0"/>
  {svg_content}
  <!-- Labels -->
  <text x="{view_width / 2}" y="{view_height - 10}" text-anchor="middle" font-family="serif" font-size="12" fill="black">
    Section View - {stories} Story Building
  </text>
</svg>'''
        
        # Save to file if path provided
        if output_path:
            output_path.write_text(svg_wrapper, encoding='utf-8')
            logger.info(f"Generated section view SVG: {output_path}")
        
        return svg_wrapper

