"""
Section view generator for creating architectural-style 2D section drawings.
Shows the building cut vertically to reveal interior structure.
"""
from pathlib import Path
from typing import List, Optional
import logging
import math

from app.services.drawing_components import DrawingComponents

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
        
        # SVG setup
        svg_lines = []
        svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{view_width}" height="{view_height}" viewBox="0 0 {view_width} {view_height}">')
        svg_lines.append(f'  <!-- Generated Section View -->')
        
        # Background
        svg_lines.append(f'  <rect width="{view_width}" height="{view_height}" fill="#f8f8f0"/>')
        
        # Ground line
        ground_y = offset_y + total_height + foundation_height
        svg_lines.append(f'  <line x1="0" y1="{ground_y}" x2="{view_width}" y2="{ground_y}" stroke="#8b7355" stroke-width="2"/>')
        
        # === FOUNDATION ===
        svg_lines.append(f'  <!-- Foundation -->')
        foundation_y = offset_y + total_height
        svg_lines.append(f'  <rect x="{offset_x}" y="{foundation_y}" width="{building_width}" height="{foundation_height}" fill="black"/>')
        
        # === FLOOR LEVELS ===
        svg_lines.append(f'  <!-- Floor Levels and Joists -->')
        
        current_z = 0  # Start from bottom of first floor
        floor_positions = []
        
        for i in range(stories):
            floor_y = offset_y + total_height - current_z
            floor_positions.append(floor_y)
            
            # Floor joist (thick line)
            joist_height = joist_heights[i] if i < len(joist_heights) else 10
            svg_lines.append(f'  <rect x="{offset_x}" y="{floor_y - joist_height}" width="{building_width}" height="{joist_height}" fill="black"/>')
            
            # Move up by joist height + ceiling height
            current_z += joist_height + ceiling_heights[i]
        
        # Add ceiling joists at top
        ceiling_joist_y = offset_y + total_height - current_z
        ceiling_joist_height = joist_heights[-1] if len(joist_heights) > stories else 8
        svg_lines.append(f'  <rect x="{offset_x}" y="{ceiling_joist_y - ceiling_joist_height}" width="{building_width}" height="{ceiling_joist_height}" fill="black"/>')
        
        # === EXTERIOR WALLS ===
        svg_lines.append(f'  <!-- Exterior Walls -->')
        
        # Left wall
        svg_lines.append(f'  <rect x="{offset_x}" y="{offset_y}" width="{wall_thickness}" height="{total_height}" fill="black"/>')
        
        # Right wall
        svg_lines.append(f'  <rect x="{offset_x + building_width - wall_thickness}" y="{offset_y}" width="{wall_thickness}" height="{total_height}" fill="black"/>')
        
        # === INTERIOR WALLS (HALL) ===
        svg_lines.append(f'  <!-- Interior Hall Walls -->')
        
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
                    svg_lines.append(f'  <rect x="{offset_x + hall_left_x}" y="{wall_top_y}" width="{wall_thickness}" height="{wall_height}" fill="black"/>')
                    
                    # Right hall wall
                    svg_lines.append(f'  <rect x="{offset_x + hall_right_x - wall_thickness}" y="{wall_top_y}" width="{wall_thickness}" height="{wall_height}" fill="black"/>')
        
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
                    svg_lines.append(f'  <rect x="{offset_x + hall_wall_x}" y="{wall_top_y}" width="{wall_thickness}" height="{wall_height}" fill="black"/>')
        
        # === WINDOWS ===
        svg_lines.append(f'  <!-- Windows -->')
        
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
                    window_svg_left = DrawingComponents.draw_window_section(
                        x=window_x_left,
                        y=window_y,
                        width=wall_thickness,
                        height=window_height,
                        operation=operation,
                        configuration=configuration
                    )
                    svg_lines.append(window_svg_left)
                    logger.info(f"Drew left window at x={window_x_left}, y={window_y}")
                    
                    # Right wall window
                    window_x_right = offset_x + building_width - wall_thickness
                    window_svg_right = DrawingComponents.draw_window_section(
                        x=window_x_right,
                        y=window_y,
                        width=wall_thickness,
                        height=window_height,
                        operation=operation,
                        configuration=configuration
                    )
                    svg_lines.append(window_svg_right)
        
        # === ROOF ===
        svg_lines.append(f'  <!-- Roof -->')
        
        roof_base_y = offset_y
        
        if roof_type == 'side-gable':
            # Side-gable: gable ends on sides, ridge runs front-to-back
            # Section through the front shows sloped roof lines (not a triangle)
            # Calculate roof slope based on building depth
            roof_run = building_depth / 2  # Use depth, not width
            roof_pitch_radians = math.radians(roof_pitch)
            roof_rise = math.tan(roof_pitch_radians) * roof_run
            roof_peak_y = roof_base_y - roof_rise
            
            logger.info(f"Side-gable roof: pitch={roof_pitch}°, run={roof_run}\" (depth/2), rise={roof_rise:.2f}\"")
            
            # Draw sloped roof lines from left and right walls up to peak (off-screen center)
            # Left slope
            svg_lines.append(f'  <line x1="{offset_x}" y1="{roof_base_y}" x2="{offset_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
            # Right slope  
            svg_lines.append(f'  <line x1="{offset_x + building_width}" y1="{roof_base_y}" x2="{offset_x + building_width}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
            # Peak line (connecting the two slopes)
            svg_lines.append(f'  <line x1="{offset_x}" y1="{roof_peak_y}" x2="{offset_x + building_width}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
        
        elif roof_type == 'front-gable':
            # Front-gable: gable end on front, ridge runs left-to-right
            # Section through the front shows the gable triangle
            roof_run = building_width / 2
            roof_pitch_radians = math.radians(roof_pitch)
            roof_rise = math.tan(roof_pitch_radians) * roof_run
            roof_peak_y = roof_base_y - roof_rise
            
            logger.info(f"Front-gable roof: pitch={roof_pitch}°, run={roof_run}\" (width/2), rise={roof_rise:.2f}\"")
            
            # Draw roof as triangle
            roof_points = f"{offset_x},{roof_base_y} {offset_x + building_width/2},{roof_peak_y} {offset_x + building_width},{roof_base_y}"
            svg_lines.append(f'  <polygon points="{roof_points}" fill="#e5e5e5" stroke="black" stroke-width="2"/>')
        
        elif roof_type == 'side-gable-with-shed':
            # Side-gable-with-shed: normal side-gable in front, shed extension in rear
            shed_length = roof_shed_length
            gable_length = building_depth - shed_length
            
            # Calculate gable roof slope based on gable length
            roof_run = gable_length / 2  # Half the gable length
            roof_pitch_radians = math.radians(roof_pitch)
            roof_rise = math.tan(roof_pitch_radians) * roof_run
            roof_peak_y = roof_base_y - roof_rise
            
            # Calculate the position where gable ends and shed begins
            gable_end_x = offset_x + gable_length
            shed_start_x = gable_end_x
            
            logger.info(f"Side-gable-with-shed roof: pitch={roof_pitch}°, gable_length={gable_length}\", shed_length={shed_length}\", rise={roof_rise:.2f}\"")
            logger.info(f"Gable ends at x={gable_end_x}, shed starts at x={shed_start_x}")
            
            # Draw gable portion (front) - triangular roof section
            # Left wall to peak
            svg_lines.append(f'  <line x1="{offset_x}" y1="{roof_base_y}" x2="{gable_end_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
            # Peak to right wall (only up to where gable ends)
            svg_lines.append(f'  <line x1="{gable_end_x}" y1="{roof_peak_y}" x2="{offset_x + building_width}" y2="{roof_base_y}" stroke="black" stroke-width="2"/>')
            # Peak line (horizontal at peak level)
            svg_lines.append(f'  <line x1="{offset_x}" y1="{roof_peak_y}" x2="{gable_end_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
            
            # Draw shed portion (rear) - flat slope extending from gable peak
            if shed_length > 0:
                # Shed has a lower pitch (typically 3:12 or 4:12)
                shed_pitch_ratio = 0.25  # 3:12 pitch for shed
                shed_rise = (shed_pitch_ratio * shed_length)
                shed_peak_y = roof_peak_y - shed_rise
                
                # Shed roof lines (extending from gable peak to rear wall)
                svg_lines.append(f'  <line x1="{gable_end_x}" y1="{roof_peak_y}" x2="{offset_x + building_width}" y2="{shed_peak_y}" stroke="black" stroke-width="2"/>')
                svg_lines.append(f'  <line x1="{offset_x + building_width}" y1="{shed_peak_y}" x2="{offset_x + building_width}" y2="{roof_base_y}" stroke="black" stroke-width="2"/>')
        
        elif roof_type == 'hipped-gable':
            # Hipped-gable: combination, show as sloped lines
            roof_run = building_depth / 2
            roof_pitch_radians = math.radians(roof_pitch)
            roof_rise = math.tan(roof_pitch_radians) * roof_run
            roof_peak_y = roof_base_y - roof_rise
            
            # Similar to side-gable
            svg_lines.append(f'  <line x1="{offset_x}" y1="{roof_base_y}" x2="{offset_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
            svg_lines.append(f'  <line x1="{offset_x + building_width}" y1="{roof_base_y}" x2="{offset_x + building_width}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
            svg_lines.append(f'  <line x1="{offset_x}" y1="{roof_peak_y}" x2="{offset_x + building_width}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
        
        # === LABELS ===
        svg_lines.append(f'  <!-- Labels -->')
        svg_lines.append(f'  <text x="{view_width / 2}" y="{view_height - 10}" text-anchor="middle" font-family="serif" font-size="12" fill="black">')
        svg_lines.append(f'    Section View - {stories} Story Building')
        svg_lines.append(f'  </text>')
        
        # Story labels
        current_z = 0
        for i in range(stories):
            floor_y = offset_y + total_height - current_z
            ceiling_height = ceiling_heights[i]
            mid_floor_y = floor_y - ceiling_height / 2
            
            svg_lines.append(f'  <text x="20" y="{mid_floor_y}" text-anchor="start" font-family="sans-serif" font-size="10" fill="#666">')
            svg_lines.append(f'    Story {i + 1}')
            svg_lines.append(f'  </text>')
            svg_lines.append(f'  <text x="20" y="{mid_floor_y + 12}" text-anchor="start" font-family="sans-serif" font-size="9" fill="#999">')
            svg_lines.append(f'    {ceiling_height / 12:.1f}\'')
            svg_lines.append(f'  </text>')
            
            joist_height = joist_heights[i] if i < len(joist_heights) else 10
            current_z += joist_height + ceiling_height
        
        # Close SVG
        svg_lines.append('</svg>')
        
        svg_content = '\n'.join(svg_lines)
        
        # Save to file if path provided
        if output_path:
            output_path.write_text(svg_content, encoding='utf-8')
            logger.info(f"Generated section view SVG: {output_path}")
        
        return svg_content

