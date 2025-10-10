"""
Plan view generator for creating architectural-style 2D floor plans.
Generates SVG drawings directly instead of projecting 3D models.
"""
from pathlib import Path
from typing import List, Optional
import logging

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
        Generate an architectural floor plan in SVG format.
        
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
        
        # SVG setup
        svg_lines = []
        svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{view_width}" height="{view_height}" viewBox="0 0 {view_width} {view_height}">')
        svg_lines.append(f'  <!-- Generated Floor Plan - {floorplan_type} -->')
        
        # Background
        svg_lines.append(f'  <rect width="{view_width}" height="{view_height}" fill="#f8f8f0"/>')
        
        # Offset for margins
        offset_x = margin
        offset_y = margin
        
        # === EXTERIOR WALLS ===
        
        # Front wall (bottom)
        svg_lines.append(f'  <!-- Front Wall -->')
        svg_lines.append(f'  <rect x="{offset_x}" y="{offset_y + left - wall_thickness}" width="{front}" height="{wall_thickness}" fill="black"/>')
        
        # Rear wall (top)
        svg_lines.append(f'  <!-- Rear Wall -->')
        svg_lines.append(f'  <rect x="{offset_x}" y="{offset_y}" width="{rear}" height="{wall_thickness}" fill="black"/>')
        
        # Left wall
        svg_lines.append(f'  <!-- Left Wall -->')
        svg_lines.append(f'  <rect x="{offset_x}" y="{offset_y}" width="{wall_thickness}" height="{left}" fill="black"/>')
        
        # Right wall
        svg_lines.append(f'  <!-- Right Wall -->')
        svg_lines.append(f'  <rect x="{offset_x + front - wall_thickness}" y="{offset_y}" width="{wall_thickness}" height="{right}" fill="black"/>')
        
        # === CENTER HALL WALLS ===
        if floorplan_type == 'center-hall':
            # Calculate hall position
            # Center of building in front/rear direction (X-axis)
            building_center_x = front / 2
            
            # Hall walls run perpendicular to front/rear (parallel to side walls)
            # They run from front to rear (along Y-axis)
            # Left hall wall (closer to left exterior wall)
            hall_left_x = building_center_x - (hall_width / 2) + hall_offset
            hall_right_x = building_center_x + (hall_width / 2) + hall_offset
            
            svg_lines.append(f'  <!-- Center Hall Walls (running front to rear) -->')
            
            # Left hall wall (vertical wall running from front to rear)
            svg_lines.append(f'  <rect x="{offset_x + hall_left_x}" y="{offset_y + wall_thickness}" width="{wall_thickness}" height="{left - 2 * wall_thickness}" fill="black"/>')
            
            # Right hall wall (vertical wall running from front to rear)
            svg_lines.append(f'  <rect x="{offset_x + hall_right_x - wall_thickness}" y="{offset_y + wall_thickness}" width="{wall_thickness}" height="{left - 2 * wall_thickness}" fill="black"/>')
            
            # === ROOM DIMENSIONS FOR CENTER-HALL ===
            # Calculate room widths
            left_room_width = hall_left_x - wall_thickness  # From left exterior wall to left hall wall
            right_room_width = (front - wall_thickness) - hall_right_x  # From right hall wall to right exterior wall
            room_depth = left - (2 * wall_thickness)  # Front to rear, minus walls
            
            svg_lines.append(f'  <!-- Room Dimension Labels -->')
            
            # Left room dimensions (centered in the room)
            left_room_center_x = offset_x + (hall_left_x / 2)
            left_room_center_y = offset_y + (left / 2)
            svg_lines.append(f'  <text x="{left_room_center_x}" y="{left_room_center_y - 10}" text-anchor="middle" font-family="serif" font-size="14" fill="#333">')
            svg_lines.append(f'    {left_room_width / 12:.1f}\' × {room_depth / 12:.1f}\'')
            svg_lines.append(f'  </text>')
            svg_lines.append(f'  <text x="{left_room_center_x}" y="{left_room_center_y + 10}" text-anchor="middle" font-family="serif" font-size="11" fill="#666">')
            svg_lines.append(f'    ({left_room_width:.0f}" × {room_depth:.0f}")')
            svg_lines.append(f'  </text>')
            
            # Hall dimensions
            hall_center_x = offset_x + building_center_x + hall_offset
            hall_center_y = offset_y + (left / 2)
            svg_lines.append(f'  <text x="{hall_center_x}" y="{hall_center_y}" text-anchor="middle" font-family="serif" font-size="12" fill="#666" font-style="italic">')
            svg_lines.append(f'    Hall: {hall_width / 12:.1f}\' ({hall_width:.0f}")')
            svg_lines.append(f'  </text>')
            
            # Right room dimensions
            right_room_center_x = offset_x + hall_right_x + (right_room_width / 2)
            right_room_center_y = offset_y + (left / 2)
            svg_lines.append(f'  <text x="{right_room_center_x}" y="{right_room_center_y - 10}" text-anchor="middle" font-family="serif" font-size="14" fill="#333">')
            svg_lines.append(f'    {right_room_width / 12:.1f}\' × {room_depth / 12:.1f}\'')
            svg_lines.append(f'  </text>')
            svg_lines.append(f'  <text x="{right_room_center_x}" y="{right_room_center_y + 10}" text-anchor="middle" font-family="serif" font-size="11" fill="#666">')
            svg_lines.append(f'    ({right_room_width:.0f}" × {room_depth:.0f}")')
            svg_lines.append(f'  </text>')
        
        elif floorplan_type == 'side-hall':
            # For side-hall, the hall runs along one side
            # Hall wall separates the hall from the main rooms
            hall_wall_x = hall_width
            
            svg_lines.append(f'  <!-- Side Hall Wall -->')
            svg_lines.append(f'  <rect x="{offset_x + hall_wall_x}" y="{offset_y + wall_thickness}" width="{wall_thickness}" height="{left - 2 * wall_thickness}" fill="black"/>')
            
            # === ROOM DIMENSIONS FOR SIDE-HALL ===
            # Calculate room dimensions
            hall_actual_width = hall_width - wall_thickness  # Hall width from exterior to hall wall
            main_room_width = (front - wall_thickness) - (hall_width + wall_thickness)  # Main room width
            room_depth = left - (2 * wall_thickness)
            
            svg_lines.append(f'  <!-- Room Dimension Labels -->')
            
            # Hall dimensions
            hall_center_x = offset_x + (hall_width / 2)
            hall_center_y = offset_y + (left / 2)
            svg_lines.append(f'  <text x="{hall_center_x}" y="{hall_center_y}" text-anchor="middle" font-family="serif" font-size="12" fill="#666" font-style="italic">')
            svg_lines.append(f'    Hall: {hall_actual_width / 12:.1f}\' × {room_depth / 12:.1f}\'')
            svg_lines.append(f'  </text>')
            
            # Main room dimensions
            main_room_center_x = offset_x + hall_width + wall_thickness + (main_room_width / 2)
            main_room_center_y = offset_y + (left / 2)
            svg_lines.append(f'  <text x="{main_room_center_x}" y="{main_room_center_y - 10}" text-anchor="middle" font-family="serif" font-size="14" fill="#333">')
            svg_lines.append(f'    {main_room_width / 12:.1f}\' × {room_depth / 12:.1f}\'')
            svg_lines.append(f'  </text>')
            svg_lines.append(f'  <text x="{main_room_center_x}" y="{main_room_center_y + 10}" text-anchor="middle" font-family="serif" font-size="11" fill="#666">')
            svg_lines.append(f'    ({main_room_width:.0f}" × {room_depth:.0f}")')
            svg_lines.append(f'  </text>')
        
        # === WINDOW OPENINGS ===
        # Use first story window config if available (windows[0])
        window_bay_width = 29.25  # Default window bay width
        if windows and len(windows) > 0:
            first_story_window = windows[0]
            if isinstance(first_story_window, dict) and 'bay_width' in first_story_window:
                window_bay_width = first_story_window['bay_width']
        
        svg_lines.append(f'  <!-- Window Openings -->')
        
        # Draw window openings on each wall using bay centerlines
        if bays and isinstance(bays, dict):
            # Front wall windows
            if 'front' in bays and len(bays['front']) > 1:
                for bay_x in bays['front'][1:]:  # Skip first element (count)
                    window_x = offset_x + bay_x - (window_bay_width / 2)
                    window_y = offset_y + left - wall_thickness
                    # White rectangle with thin border
                    svg_lines.append(f'  <rect x="{window_x}" y="{window_y}" width="{window_bay_width}" height="{wall_thickness}" fill="white" stroke="black" stroke-width="0.5"/>')
            
            # Rear wall windows
            if 'rear' in bays and len(bays['rear']) > 1:
                for bay_x in bays['rear'][1:]:
                    window_x = offset_x + bay_x - (window_bay_width / 2)
                    window_y = offset_y
                    svg_lines.append(f'  <rect x="{window_x}" y="{window_y}" width="{window_bay_width}" height="{wall_thickness}" fill="white" stroke="black" stroke-width="0.5"/>')
            
            # Left wall windows
            if 'left' in bays and len(bays['left']) > 1:
                for bay_y in bays['left'][1:]:
                    window_x = offset_x
                    window_y = offset_y + bay_y - (window_bay_width / 2)
                    svg_lines.append(f'  <rect x="{window_x}" y="{window_y}" width="{wall_thickness}" height="{window_bay_width}" fill="white" stroke="black" stroke-width="0.5"/>')
            
            # Right wall windows
            if 'right' in bays and len(bays['right']) > 1:
                for bay_y in bays['right'][1:]:
                    window_x = offset_x + front - wall_thickness
                    window_y = offset_y + bay_y - (window_bay_width / 2)
                    svg_lines.append(f'  <rect x="{window_x}" y="{window_y}" width="{wall_thickness}" height="{window_bay_width}" fill="white" stroke="black" stroke-width="0.5"/>')
        
        # === DOOR OPENINGS ===
        svg_lines.append(f'  <!-- Door Openings -->')
        
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
                    svg_lines.append(f'  <rect x="{door_x}" y="{door_y}" width="{door_bay_width}" height="{wall_thickness}" fill="white" stroke="black" stroke-width="0.5"/>')
                elif wall == 'rear':
                    door_x = offset_x + position - (door_bay_width / 2)
                    door_y = offset_y
                    svg_lines.append(f'  <rect x="{door_x}" y="{door_y}" width="{door_bay_width}" height="{wall_thickness}" fill="white" stroke="black" stroke-width="0.5"/>')
                elif wall == 'left':
                    door_x = offset_x
                    door_y = offset_y + position - (door_bay_width / 2)
                    svg_lines.append(f'  <rect x="{door_x}" y="{door_y}" width="{wall_thickness}" height="{door_bay_width}" fill="white" stroke="black" stroke-width="0.5"/>')
                elif wall == 'right':
                    door_x = offset_x + front - wall_thickness
                    door_y = offset_y + position - (door_bay_width / 2)
                    svg_lines.append(f'  <rect x="{door_x}" y="{door_y}" width="{wall_thickness}" height="{door_bay_width}" fill="white" stroke="black" stroke-width="0.5"/>')
        
        # === BAY MARKERS (for window placement reference) ===
        if bays and isinstance(bays, dict):
            svg_lines.append(f'  <!-- Bay Centerlines (dotted reference lines) -->')
            
            # Front bay markers
            if 'front' in bays and len(bays['front']) > 1:
                for i, bay_x in enumerate(bays['front'][1:]):  # Skip first element (count)
                    x = offset_x + bay_x
                    svg_lines.append(f'  <line x1="{x}" y1="{offset_y + left - wall_thickness * 2}" x2="{x}" y2="{offset_y + left}" stroke="gray" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.5"/>')
            
            # Rear bay markers
            if 'rear' in bays and len(bays['rear']) > 1:
                for i, bay_x in enumerate(bays['rear'][1:]):
                    x = offset_x + bay_x
                    svg_lines.append(f'  <line x1="{x}" y1="{offset_y}" x2="{x}" y2="{offset_y + wall_thickness * 2}" stroke="gray" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.5"/>')
        
        # === LABELS ===
        svg_lines.append(f'  <!-- Labels -->')
        svg_lines.append(f'  <text x="{view_width / 2}" y="{view_height - 10}" text-anchor="middle" font-family="serif" font-size="12" fill="black">')
        svg_lines.append(f'    Floor Plan - {floorplan_type.replace("-", " ").title()}')
        svg_lines.append(f'  </text>')
        
        # Dimension labels
        svg_lines.append(f'  <text x="{view_width / 2}" y="15" text-anchor="middle" font-family="sans-serif" font-size="10" fill="gray">')
        svg_lines.append(f'    {front / 12:.1f}\' × {left / 12:.1f}\'')
        svg_lines.append(f'  </text>')
        
        # Close SVG
        svg_lines.append('</svg>')
        
        svg_content = '\n'.join(svg_lines)
        
        # Save to file if path provided
        if output_path:
            output_path.write_text(svg_content, encoding='utf-8')
            logger.info(f"Generated plan view SVG: {output_path}")
        
        return svg_content
    
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

