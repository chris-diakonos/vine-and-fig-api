"""
Elevation view generator for creating architectural-style 2D elevation drawings.
Shows the exterior view of the building from the front.
"""
from pathlib import Path
from typing import List, Optional
import logging
import math

from app.services.drawing_components import DrawingComponents

logger = logging.getLogger(__name__)


class ElevationViewGenerator:
    """Generates architectural-style 2D elevation drawings."""
    
    # Roof panel color mapping
    ROOF_COLORS = {
        'light-gray': '#c8c8c8',
        'ash-gray': '#a0a0a0',
        'charcoal-gray': '#5a5a5a',
        'steel-gray': '#7a7a7a',
        'burnished-slate': '#4a4a4a',
        'emerald-green': '#2d5016',
        'colony-green': '#3d6b2e',
        'rustic-red': '#8b4513',
        'cocoa-brown': '#6b4423',
    }
    
    @staticmethod
    def generate_elevation_svg(
        face: str,  # 'front', 'rear', 'left', or 'right'
        dimensions: dict,
        stories: int,
        ceiling_heights: List[float],
        joist_heights: List[float],
        foundation_height: float,
        foundation_courses: int,
        foundation_block_size: List[float],
        foundation_block_joint: float,
        roof_pitch: float,
        roof_type: str,
        roof_panel_exposure: int = 12,
        roof_panel_color: str = 'charcoal-gray',
        roof_overhang: float = 12,
        roof_shed_length: float = 0,
        floorplan_type: str = 'center-hall',
        bays: Optional[dict] = None,
        windows: Optional[List] = None,
        doors: Optional[List] = None,
        sheathing: Optional[dict] = None,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate an elevation drawing in SVG format for the specified face.
        
        Args:
            face: Which face to render ('front', 'rear', 'left', 'right')
            dimensions: Building dimensions (front, left, building_height)
            stories: Number of stories
            ceiling_heights: List of ceiling heights per story
            joist_heights: List of joist heights per floor
            foundation_height: Total foundation height
            foundation_courses: Number of foundation block courses
            foundation_block_size: Block dimensions [length, width, height]
            foundation_block_joint: Mortar joint thickness
            roof_pitch: Roof pitch in degrees
            roof_type: Type of roof (side-gable, front-gable, etc.)
            floorplan_type: Type of floorplan (center-hall, side-hall)
            bays: Bay centerlines for window placement
            windows: Window configurations
            doors: Door specifications
            sheathing: Sheathing specifications (exposure, height, type)
            output_path: Path to save the SVG file
            
        Returns:
            SVG content as string
        """
        # Determine building dimensions based on which face we're viewing
        if face in ['front', 'rear']:
            building_width = dimensions['front']
            building_depth = dimensions['left']
        else:  # 'left' or 'right'
            building_width = dimensions['left']
            building_depth = dimensions['front']
        
        building_height = dimensions['building_height']
        
        # Calculate total height including foundation and roof
        roof_pitch_radians = math.radians(roof_pitch)
        
        # Calculate roof height based on roof type and floorplan orientation
        building_depth = dimensions['left']
        
        if roof_type == 'side-gable':
            # Side-gable: ridge runs front-to-back
            # Front elevation shows sloped roof lines
            # Rise is based on depth (front-to-back dimension)
            roof_run = building_depth / 2
            roof_rise = math.tan(roof_pitch_radians) * roof_run
        elif roof_type == 'hipped-gable':
            # Hipped-gable: combination of gable on narrow ends, hip on long sides
            # Narrow ends show triangle (gable), long sides show trapezoid (hip)
            # For front elevation, determine if we're viewing narrow or long side
            # Ridge runs along the LONG dimension
            
            # If front is narrower than depth, we're viewing the GABLE end (triangle)
            # If front is wider than depth, we're viewing the HIP side (trapezoid)
            if building_width < building_depth:
                # Narrow end (gable) - use width for triangle
                roof_run = building_width / 2
            else:
                # Long side (hip) - use depth for trapezoid
                roof_run = building_depth / 2
            roof_rise = math.tan(roof_pitch_radians) * roof_run
        elif roof_type == 'front-gable':
            # Front-gable: gable end on front, ridge runs left-to-right
            # Front elevation shows gable triangle
            roof_run = building_width / 2
            roof_rise = math.tan(roof_pitch_radians) * roof_run
        elif roof_type == 'side-gable-with-shed':
            # Side-gable-with-shed: ridge runs front-to-back
            # Front elevation shows sloped roof lines
            # Rise is based on depth (front-to-back dimension)
            roof_run = (building_depth - roof_shed_length) / 2
            roof_rise = math.tan(roof_pitch_radians) * roof_run
        else:
            roof_rise = 0
        
        total_height = foundation_height + building_height + roof_rise
        
        # Calculate view dimensions with margins
        margin = 60
        view_width = building_width + (2 * margin)
        view_height = total_height + (2 * margin)
        
        # Offset for margins
        offset_x = margin
        offset_y = margin
        
        # SVG setup
        svg_lines = []
        svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{view_width}" height="{view_height}" viewBox="0 0 {view_width} {view_height}">')
        svg_lines.append(f'  <!-- Generated Front Elevation -->')
        
        # Background
        svg_lines.append(f'  <rect width="{view_width}" height="{view_height}" fill="#f8f8f0"/>')
        
        # Ground line
        ground_y = offset_y + total_height
        svg_lines.append(f'  <line x1="0" y1="{ground_y}" x2="{view_width}" y2="{ground_y}" stroke="#8b7355" stroke-width="2"/>')
        
        # === FOUNDATION ===
        svg_lines.append(f'  <!-- Foundation -->')
        foundation_y = offset_y + roof_rise + building_height
        
        # Draw individual foundation blocks with mortar joints
        block_length = foundation_block_size[0]  # Length along the wall
        block_height = foundation_block_size[2]  # Height of each block
        joint = foundation_block_joint
        
        # Calculate course height (block + joint)
        course_height = block_height + joint
        
        # Draw each course (row) of blocks
        for course in range(foundation_courses):
            course_y = foundation_y + (course * course_height)
            
            # Calculate number of blocks needed for this row
            num_blocks = int(building_width / (block_length + joint)) + 1
            
            # Offset every other row for running bond pattern
            x_offset = 0
            if course % 2 == 1:
                x_offset = -(block_length / 2)
            
            # Draw blocks in this course
            for i in range(num_blocks):
                block_x = offset_x + x_offset + (i * (block_length + joint))
                
                # Only draw if block is within building width
                if block_x < offset_x + building_width and block_x + block_length > offset_x:
                    # Clip block to building width
                    actual_x = max(block_x, offset_x)
                    actual_width = min(block_x + block_length, offset_x + building_width) - actual_x
                    
                    if actual_width > 0:
                        # Draw block
                        svg_lines.append(f'  <rect x="{actual_x}" y="{course_y}" width="{actual_width}" height="{block_height}" fill="#a8a8a8" stroke="#666" stroke-width="0.5"/>')
                        
                        # Draw mortar joint below (except for last course)
                        if course < foundation_courses - 1:
                            svg_lines.append(f'  <rect x="{actual_x}" y="{course_y + block_height}" width="{actual_width}" height="{joint}" fill="#d4d4d4"/>')
        
        # Outline foundation
        svg_lines.append(f'  <rect x="{offset_x}" y="{foundation_y}" width="{building_width}" height="{foundation_height}" fill="none" stroke="black" stroke-width="2"/>')
        
        # === WALLS WITH SHEATHING ===
        svg_lines.append(f'  <!-- Walls and Sheathing -->')
        wall_y = offset_y + roof_rise
        
        # Main wall rectangle
        svg_lines.append(f'  <rect x="{offset_x}" y="{wall_y}" width="{building_width}" height="{building_height}" fill="#e8dcc0" stroke="black" stroke-width="2"/>')
        
        # Sheathing lines (horizontal weatherboard)
        if sheathing:
            sheathing_exposure = sheathing.get('sheathing_exposure', 6)
            num_boards = int(building_height / sheathing_exposure)
            
            for i in range(1, num_boards):
                sheathing_y = wall_y + (i * sheathing_exposure)
                if sheathing_y < wall_y + building_height:
                    svg_lines.append(f'  <line x1="{offset_x}" y1="{sheathing_y}" x2="{offset_x + building_width}" y2="{sheathing_y}" stroke="black" stroke-width="0.5" opacity="0.4"/>')
        
        # Corner boards (vertical trim at edges)
        corner_board_width = 4
        svg_lines.append(f'  <rect x="{offset_x}" y="{wall_y}" width="{corner_board_width}" height="{building_height}" fill="#d4a574" stroke="black" stroke-width="0.5"/>')
        svg_lines.append(f'  <rect x="{offset_x + building_width - corner_board_width}" y="{wall_y}" width="{corner_board_width}" height="{building_height}" fill="#d4a574" stroke="black" stroke-width="0.5"/>')
        
        # === WINDOWS ===
        svg_lines.append(f'  <!-- Windows -->')
        
        # Calculate floor heights for window positioning
        floor_heights = []
        current_z = 0
        for i in range(stories):
            joist_height = joist_heights[i] if i < len(joist_heights) else 10
            floor_heights.append(current_z)
            current_z += joist_height + ceiling_heights[i]
        
        # Build a set of door positions on this face for quick lookup
        door_positions_on_face = set()
        if doors:
            for door in doors:
                if isinstance(door, dict) and door.get('wall') == face:
                    door_positions_on_face.add(door.get('position', 0))
        
        logger.info(f"{face.capitalize()} elevation: door positions = {door_positions_on_face}")
        
        # Draw windows at bay centerlines for this face
        if bays and face in bays and windows:
            face_bays = bays[face]
            num_bays = face_bays[0] if len(face_bays) > 0 else 0
            bay_positions = face_bays[1:] if len(face_bays) > 1 else []
            
            logger.info(f"{face.capitalize()} elevation: {num_bays} bays at positions {bay_positions}")
            
            # Draw windows for each story
            for story_idx in range(stories):
                if story_idx < len(windows):
                    window_config = windows[story_idx]
                    if isinstance(window_config, dict):
                        # Get window dimensions - use bay_width for total width
                        window_width = window_config.get('bay_width', 29.25)
                        
                        # Get chair_rail_height (window sill height) from config
                        window_sill_height = window_config.get('chair_rail_height', 28)
                        
                        # Parse pane size for height (e.g., "8x10" -> height = 10")
                        size = window_config.get('size', '8x10')
                        pane_width, pane_height = [float(x) for x in size.split('x')]
                        
                        # Parse configuration to determine rows per sash
                        configuration = window_config.get('configuration', '6/6')
                        top_panes, bottom_panes = configuration.split('/')
                        top_panes_int = int(top_panes)
                        bottom_panes_int = int(bottom_panes)
                        panes_across = 3  # Standard: 3 panes across
                        
                        top_rows = top_panes_int // panes_across  # e.g., 6/3 = 2 rows
                        bottom_rows = bottom_panes_int // panes_across  # e.g., 9/3 = 3 rows
                        
                        # Calculate sash heights: rows of panes + muntins between them
                        muntin_width = window_config.get('muntin_width', 1.0)
                        top_muntins = top_rows - 1
                        bottom_muntins = bottom_rows - 1
                        top_sash_height = (top_rows * pane_height) + (top_muntins * muntin_width)
                        bottom_sash_height = (bottom_rows * pane_height) + (bottom_muntins * muntin_width)
                        
                        # Calculate total window height: both sashes + rails + meeting rail
                        rail_width = window_config.get('rail_width', 3.0)
                        meeting_rail_width = window_config.get('meeting_rail_width', 1.0)
                        window_height = top_sash_height + bottom_sash_height + (2 * rail_width) + meeting_rail_width
                        
                        # Get window details
                        operation = window_config.get('operation', 'single-hung')
                        stile_width = window_config.get('stile_width', 2.0)
                        
                        # Calculate Y position for this story
                        floor_base_z = floor_heights[story_idx]
                        window_y = foundation_y - floor_base_z - window_sill_height - window_height
                        
                        logger.info(f"Story {story_idx}: floor_z={floor_base_z}, window_y={window_y}")
                        
                        # Draw window at each bay position
                        for bay_x in bay_positions:
                            # Skip if this bay position has a door (only on first floor)
                            if story_idx == 0 and bay_x in door_positions_on_face:
                                logger.info(f"Skipping window at bay {bay_x} (door position)")
                                continue
                            
                            window_x = offset_x + bay_x - (window_width / 2)
                            
                            # Use detailed window elevation drawing
                            window_svg = DrawingComponents.draw_window_elevation(
                                x=window_x,
                                y=window_y,
                                width=window_width,
                                height=window_height,
                                operation=operation,
                                configuration=configuration,
                                stile_width=stile_width,
                                rail_width=rail_width,
                                muntin_width=muntin_width,
                                meeting_rail_width=meeting_rail_width
                            )
                            svg_lines.append(window_svg)
        
        # === DOORS ===
        svg_lines.append(f'  <!-- Doors -->')
        
        if doors:
            for door in doors:
                if isinstance(door, dict) and door.get('wall') == face:
                    # Use bay_width for total door width
                    door_width = door.get('bay_width', 40.5)
                    door_height = float(door.get('size', '36x96').split('x')[1])
                    door_position = door.get('position', 0)
                    
                    # Get door configuration
                    configuration = door.get('configuration', 'six-panel')
                    panel_type = door.get('panel_type', 'raised-panel')
                    stile_widths = door.get('stile_widths', None)  # Array of 3 widths
                    rail_widths = door.get('rail_widths', None)    # Array of 3 or 4 widths
                    panel_widths = door.get('panel_widths', None)  # Array of 2 widths
                    
                    # Position door centered at bay position
                    door_x = offset_x + door_position - (door_width / 2)
                    door_y = foundation_y - door_height
                    
                    logger.info(f"Drawing door at position {door_position}, x={door_x}, y={door_y}, size={door_width}x{door_height}")
                    logger.info(f"Door config: {configuration}, stile_widths={stile_widths}, rail_widths={rail_widths}, panel_widths={panel_widths}")
                    
                    # Use detailed door elevation drawing
                    door_svg = DrawingComponents.draw_door_elevation(
                        x=door_x,
                        y=door_y,
                        width=door_width,
                        height=door_height,
                        configuration=configuration,
                        panel_type=panel_type,
                        stile_widths=stile_widths,
                        rail_widths=rail_widths,
                        panel_widths=panel_widths
                    )
                    svg_lines.append(door_svg)
        
        # === ROOF ===
        svg_lines.append(f'  <!-- Roof -->')
        
        roof_base_y = wall_y
        roof_peak_y = roof_base_y - roof_rise
        
        # Get roof color from mapping
        roof_color = ElevationViewGenerator.ROOF_COLORS.get(roof_panel_color, '#5a5a5a')
        
        # Determine what to show based on roof_type and which face we're viewing
        logger.info(f"Roof rendering: type={roof_type}, face={face}, width={building_width}, depth={building_depth}")
        
        if roof_type == 'side-gable':
            # Side-gable: gable ends on LEFT/RIGHT sides, ridge runs FRONT-TO-BACK
            if face in ['left', 'right']:
                # Viewing gable end - show TRIANGLE with SIDING
                # Roof extends beyond wall by overhang amount on each side
                roof_left_x = offset_x - roof_overhang
                roof_right_x = offset_x + building_width + roof_overhang
                roof_points = f"{roof_left_x},{roof_base_y} {offset_x + building_width/2},{roof_peak_y} {roof_right_x},{roof_base_y}"
                svg_lines.append(f'  <polygon points="{roof_points}" fill="#e8dcc0" stroke="black" stroke-width="2"/>')
                
                # Draw siding on gable
                if sheathing:
                    sheathing_exposure = sheathing.get('sheathing_exposure', 6)
                    peak_x = offset_x + building_width / 2
                    for i in range(1, int(roof_rise / sheathing_exposure) + 1):
                        siding_y = roof_base_y - (i * sheathing_exposure)
                        if siding_y > roof_peak_y:
                            height_ratio = (roof_base_y - siding_y) / roof_rise
                            half_width = (building_width / 2) * (1 - height_ratio)
                            svg_lines.append(f'  <line x1="{peak_x - half_width}" y1="{siding_y}" x2="{peak_x + half_width}" y2="{siding_y}" stroke="black" stroke-width="0.5" opacity="0.4"/>')
                
                # Roof slopes (extended by overhang)
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_base_y}" x2="{offset_x + building_width/2}" y2="{roof_peak_y}" stroke="black" stroke-width="3"/>')
                svg_lines.append(f'  <line x1="{roof_right_x}" y1="{roof_base_y}" x2="{offset_x + building_width/2}" y2="{roof_peak_y}" stroke="black" stroke-width="3"/>')
            else:
                # Viewing front/rear - show SLOPED ROOF LINES with overhang
                roof_left_x = offset_x - roof_overhang
                roof_right_x = offset_x + building_width + roof_overhang
                svg_lines.append(f'  <polygon points="{roof_left_x},{roof_base_y} {roof_left_x},{roof_peak_y} {roof_right_x},{roof_peak_y} {roof_right_x},{roof_base_y}" fill="{roof_color}"/>')
                
                # Vertical panel lines
                roof_width_with_overhang = building_width + (2 * roof_overhang)
                for i in range(int(roof_width_with_overhang / roof_panel_exposure) + 1):
                    panel_x = roof_left_x + (i * roof_panel_exposure)
                    if roof_left_x <= panel_x <= roof_right_x:
                        svg_lines.append(f'  <line x1="{panel_x}" y1="{roof_base_y}" x2="{panel_x}" y2="{roof_peak_y}" stroke="black" stroke-width="0.5" opacity="0.7"/>')
                
                # Outline
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_base_y}" x2="{roof_left_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
                svg_lines.append(f'  <line x1="{roof_right_x}" y1="{roof_base_y}" x2="{roof_right_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_peak_y}" x2="{roof_right_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
        
        elif roof_type == 'front-gable':
            # Front-gable: gable ends on FRONT/REAR, ridge runs LEFT-TO-RIGHT
            if face in ['front', 'rear']:
                # Viewing gable end - show TRIANGLE with SIDING
                roof_left_x = offset_x - roof_overhang
                roof_right_x = offset_x + building_width + roof_overhang
                roof_points = f"{roof_left_x},{roof_base_y} {offset_x + building_width/2},{roof_peak_y} {roof_right_x},{roof_base_y}"
                svg_lines.append(f'  <polygon points="{roof_points}" fill="#e8dcc0" stroke="black" stroke-width="2"/>')
                
                # Draw siding on gable
                if sheathing:
                    sheathing_exposure = sheathing.get('sheathing_exposure', 6)
                    peak_x = offset_x + building_width / 2
                    for i in range(1, int(roof_rise / sheathing_exposure) + 1):
                        siding_y = roof_base_y - (i * sheathing_exposure)
                        if siding_y > roof_peak_y:
                            height_ratio = (roof_base_y - siding_y) / roof_rise
                            half_width = (building_width / 2) * (1 - height_ratio)
                            svg_lines.append(f'  <line x1="{peak_x - half_width}" y1="{siding_y}" x2="{peak_x + half_width}" y2="{siding_y}" stroke="black" stroke-width="0.5" opacity="0.4"/>')
                
                # Roof slopes (extended by overhang)
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_base_y}" x2="{offset_x + building_width/2}" y2="{roof_peak_y}" stroke="black" stroke-width="3"/>')
                svg_lines.append(f'  <line x1="{roof_right_x}" y1="{roof_base_y}" x2="{offset_x + building_width/2}" y2="{roof_peak_y}" stroke="black" stroke-width="3"/>')
            else:
                # Viewing left/right sides - show SLOPED ROOF LINES with overhang
                roof_left_x = offset_x - roof_overhang
                roof_right_x = offset_x + building_width + roof_overhang
                svg_lines.append(f'  <polygon points="{roof_left_x},{roof_base_y} {roof_left_x},{roof_peak_y} {roof_right_x},{roof_peak_y} {roof_right_x},{roof_base_y}" fill="{roof_color}"/>')
                
                # Vertical panel lines
                roof_width_with_overhang = building_width + (2 * roof_overhang)
                for i in range(int(roof_width_with_overhang / roof_panel_exposure) + 1):
                    panel_x = roof_left_x + (i * roof_panel_exposure)
                    if roof_left_x <= panel_x <= roof_right_x:
                        svg_lines.append(f'  <line x1="{panel_x}" y1="{roof_base_y}" x2="{panel_x}" y2="{roof_peak_y}" stroke="black" stroke-width="0.5" opacity="0.7"/>')
                
                # Outline
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_base_y}" x2="{roof_left_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
                svg_lines.append(f'  <line x1="{roof_right_x}" y1="{roof_base_y}" x2="{roof_right_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_peak_y}" x2="{roof_right_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
        
        elif roof_type == 'side-gable-with-shed':
            # Side-gable-with-shed: normal side-gable in front, shed extension in rear
            # The shed reduces the length of the gable portion
            shed_length = roof_shed_length
            gable_length = building_depth - shed_length + roof_overhang
            gable_run= gable_length / 2
            gable_roof_pitch_radians = math.radians(roof_pitch)
            gable_roof_rise = math.tan(gable_roof_pitch_radians) * gable_run
            
            if face in ['left', 'right']:
                # Viewing gable end - show complex roof profile with gable + shed
                roof_left_x = offset_x - roof_overhang
                roof_right_x = offset_x + building_width + roof_overhang
                
                # Calculate the position where gable transitions to shed (based on building depth)
                # For side-gable-with-shed, the gable portion is at the front, shed at rear
                # In left/right elevation, we see the full building depth
                gable_transition_x = roof_left_x + gable_length
                
                # Calculate gable peak position - peak should be centered over the gable portion
                gable_peak_x = roof_left_x + (gable_length / 2)
                
                # Draw the complex roof profile
                if shed_length > 0:
                    # Combined gable + shed roof
                    shed_pitch_ratio = 0.08333333333333333  # 1:12 pitch for shed
                    shed_rise = (shed_pitch_ratio * shed_length)
                    shed_peak_y = roof_base_y + shed_rise
                    roof_rise = gable_roof_rise
                    gable_roof_peak_y = roof_base_y - gable_roof_rise
                    
       
                    # Roof slopes (extended by overhang)
                    svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_base_y}" x2="{gable_peak_x}" y2="{gable_roof_peak_y}" stroke="black" stroke-width="3"/>')
                    svg_lines.append(f'  <line x1="{gable_peak_x}" y1="{gable_roof_peak_y}" x2="{gable_transition_x}" y2="{roof_base_y}" stroke="black" stroke-width="3"/>')
                    svg_lines.append(f'  <line x1="{gable_transition_x}" y1="{roof_base_y}" x2="{roof_right_x}" y2="{shed_peak_y}" stroke="black" stroke-width="3"/>')
                    
                    
                else:
                    # No shed - just normal gable
                    roof_points = f"{roof_left_x},{roof_base_y} {offset_x + building_width/2},{roof_peak_y} {roof_right_x},{roof_base_y}"
                    svg_lines.append(f'  <polygon points="{roof_points}" fill="{roof_color}" stroke="black" stroke-width="2"/>')
                    
                    # Draw roof panel lines for full gable
                    for i in range(int((building_width + 2*roof_overhang) / roof_panel_exposure) + 1):
                        panel_x = roof_left_x + (i * roof_panel_exposure)
                        if panel_x <= roof_right_x:
                            # Calculate panel line height based on gable slope
                            ratio = abs(panel_x - (offset_x + building_width/2)) / (building_width/2 + roof_overhang)
                            panel_y = roof_base_y - (ratio * roof_rise)
                            svg_lines.append(f'  <line x1="{panel_x}" y1="{roof_base_y}" x2="{panel_x}" y2="{panel_y}" stroke="black" stroke-width="0.5" opacity="0.7"/>')
                    
                    # Main roof outline
                    svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_base_y}" x2="{offset_x + building_width/2}" y2="{roof_peak_y}" stroke="black" stroke-width="3"/>')
                    svg_lines.append(f'  <line x1="{offset_x + building_width/2}" y1="{roof_peak_y}" x2="{roof_right_x}" y2="{roof_base_y}" stroke="black" stroke-width="3"/>')
            elif face == 'front':
                # Viewing front - show normal gable roof lines
                roof_left_x = offset_x - roof_overhang
                roof_right_x = offset_x + building_width + roof_overhang
                svg_lines.append(f'  <polygon points="{roof_left_x},{roof_base_y} {roof_left_x},{roof_peak_y} {roof_right_x},{roof_peak_y} {roof_right_x},{roof_base_y}" fill="{roof_color}"/>')
                
                # Vertical panel lines
                roof_width_with_overhang = building_width + (2 * roof_overhang)
                for i in range(int(roof_width_with_overhang / roof_panel_exposure) + 1):
                    panel_x = roof_left_x + (i * roof_panel_exposure)
                    if roof_left_x <= panel_x <= roof_right_x:
                        svg_lines.append(f'  <line x1="{panel_x}" y1="{roof_base_y}" x2="{panel_x}" y2="{roof_peak_y}" stroke="black" stroke-width="0.5" opacity="0.7"/>')
                
                # Outline
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_base_y}" x2="{roof_left_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
                svg_lines.append(f'  <line x1="{roof_right_x}" y1="{roof_base_y}" x2="{roof_right_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_peak_y}" x2="{roof_right_x}" y2="{roof_peak_y}" stroke="black" stroke-width="2"/>')
            else:  # face == 'rear'
                # Viewing rear - show shed roof (flat slope)
                roof_left_x = offset_x - roof_overhang
                roof_right_x = offset_x + building_width + roof_overhang
                
                # Shed roof has a lower pitch (typically 3:12 or 4:12)
                shed_pitch_ratio = 0.25  # 3:12 pitch for shed
                shed_rise = (shed_pitch_ratio * building_width)
                shed_peak_y = roof_base_y - shed_rise
                
                # Draw shed roof
                svg_lines.append(f'  <polygon points="{roof_left_x},{roof_base_y} {roof_left_x},{shed_peak_y} {roof_right_x},{shed_peak_y} {roof_right_x},{roof_base_y}" fill="{roof_color}"/>')
                
                # Vertical panel lines for shed
                roof_width_with_overhang = building_width + (2 * roof_overhang)
                for i in range(int(roof_width_with_overhang / roof_panel_exposure) + 1):
                    panel_x = roof_left_x + (i * roof_panel_exposure)
                    if roof_left_x <= panel_x <= roof_right_x:
                        svg_lines.append(f'  <line x1="{panel_x}" y1="{roof_base_y}" x2="{panel_x}" y2="{shed_peak_y}" stroke="black" stroke-width="0.5" opacity="0.7"/>')
                
                # Outline
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{roof_base_y}" x2="{roof_left_x}" y2="{shed_peak_y}" stroke="black" stroke-width="2"/>')
                svg_lines.append(f'  <line x1="{roof_right_x}" y1="{roof_base_y}" x2="{roof_right_x}" y2="{shed_peak_y}" stroke="black" stroke-width="2"/>')
                svg_lines.append(f'  <line x1="{roof_left_x}" y1="{shed_peak_y}" x2="{roof_right_x}" y2="{shed_peak_y}" stroke="black" stroke-width="2"/>')
        
        elif roof_type == 'hipped-gable':
            # Hipped-gable: gable on narrow ends, hip on long sides
            # Need to determine which dimension is narrow based on original building, not rotated view
            original_front = dimensions['front']
            original_depth = dimensions['left']
            
            logger.info(f"Hipped-gable roof: pitch={roof_pitch}°, original_front={original_front}\", original_depth={original_depth}\"")
            
            # Determine if THIS face shows gable or hip
            is_gable_end = False
            if face in ['left', 'right']:
                # Left/right: gable if depth < front (building is wider than deep)
                is_gable_end = original_depth < original_front
            else:  # front or rear
                # Front/rear: gable if front < depth (building is deeper than wide)
                is_gable_end = original_front < original_depth
            
            if is_gable_end:
                # Viewing NARROW end - show GABLE TRIANGLE with ROOFING
                logger.info(f"Hipped-gable: showing gable triangle (narrow end)")
                roof_left_x = offset_x - roof_overhang
                roof_right_x = offset_x + building_width + roof_overhang
                roof_points = f"{roof_left_x},{roof_base_y} {offset_x + building_width/2},{roof_peak_y} {roof_right_x},{roof_base_y}"
                
                # Fill gable triangle with roof color (hipped-gable gables are roofed, not sided)
                svg_lines.append(f'  <polygon points="{roof_points}" fill="{roof_color}" stroke="black" stroke-width="2"/>')
                
                # Draw vertical roof panel lines (at 90 degrees)
                roof_width_with_overhang = building_width + (2 * roof_overhang)
                num_panels = int(roof_width_with_overhang / roof_panel_exposure)
                peak_x = offset_x + building_width / 2
                
                for i in range(num_panels + 1):
                    panel_x = roof_left_x + (i * roof_panel_exposure)
                    
                    # Calculate where this vertical line intersects the roof slopes
                    if panel_x < peak_x:
                        # Left slope - using extended roof base
                        ratio = (panel_x - roof_left_x) / (peak_x - roof_left_x)
                        line_top_y = roof_base_y - (ratio * roof_rise)
                    elif panel_x > peak_x:
                        # Right slope
                        ratio = (panel_x - peak_x) / (roof_right_x - peak_x)
                        line_top_y = roof_peak_y + (ratio * roof_rise)
                    else:
                        # At peak
                        line_top_y = roof_peak_y
                    
                    # Draw vertical line from eave to roof edge
                    if roof_left_x <= panel_x <= roof_right_x:
                        svg_lines.append(f'  <line x1="{panel_x}" y1="{roof_base_y}" x2="{panel_x}" y2="{line_top_y}" stroke="black" stroke-width="0.5" opacity="0.7"/>')
            else:
                # Viewing LONG side - show HIP TRAPEZOID
                logger.info(f"Hipped-gable: showing hip trapezoid (long side)")
                
                # Roof extends by overhang on each side
                roof_left_x = offset_x - roof_overhang
                roof_right_x = offset_x + building_width + roof_overhang
                
                # Hip length (ridge is shorter than building width)
                ridge_proportion = 0.7
                ridge_width = building_width * ridge_proportion
                ridge_left_x = offset_x + (building_width - ridge_width) / 2
                ridge_right_x = ridge_left_x + ridge_width
                
                # Trapezoid points (extended by overhang at eaves)
                trapezoid_points = f"{roof_left_x},{roof_base_y} {ridge_left_x},{roof_peak_y} {ridge_right_x},{roof_peak_y} {roof_right_x},{roof_base_y}"
                
                # Fill trapezoid with roof color
                svg_lines.append(f'  <polygon points="{trapezoid_points}" fill="{roof_color}"/>')
                
                # Draw vertical roof panel lines (at 90 degrees)
                roof_width_with_overhang = building_width + (2 * roof_overhang)
                num_panels = int(roof_width_with_overhang / roof_panel_exposure) + 1
                for i in range(num_panels):
                    panel_x = roof_left_x + (i * roof_panel_exposure)
                    
                    if roof_left_x <= panel_x <= roof_right_x:
                        # Calculate where vertical line intersects the trapezoid top
                        if panel_x < ridge_left_x:
                            # Left hip - find Y on sloped edge
                            ratio = (panel_x - roof_left_x) / (ridge_left_x - roof_left_x)
                            line_top_y = roof_base_y - (ratio * roof_rise)
                        elif panel_x > ridge_right_x:
                            # Right hip - find Y on sloped edge
                            ratio = (panel_x - ridge_right_x) / (roof_right_x - ridge_right_x)
                            line_top_y = roof_peak_y + (ratio * roof_rise)
                        else:
                            # Ridge area - vertical line to ridge
                            line_top_y = roof_peak_y
                        
                        # Draw vertical line from eave to top
                        svg_lines.append(f'  <line x1="{panel_x}" y1="{roof_base_y}" x2="{panel_x}" y2="{line_top_y}" stroke="black" stroke-width="0.5" opacity="0.7"/>')
                
                # Outline
                svg_lines.append(f'  <polygon points="{trapezoid_points}" fill="none" stroke="black" stroke-width="2"/>')
        
        # === LABELS ===
        svg_lines.append(f'  <!-- Labels -->')
        svg_lines.append(f'  <text x="{view_width / 2}" y="{view_height - 10}" text-anchor="middle" font-family="serif" font-size="12" fill="black">')
        svg_lines.append(f'    {face.capitalize()} Elevation - {stories} Story Building')
        svg_lines.append(f'  </text>')
        
        # Close SVG
        svg_lines.append('</svg>')
        
        svg_content = '\n'.join(svg_lines)
        
        # Save to file if path provided
        if output_path:
            output_path.write_text(svg_content, encoding='utf-8')
            logger.info(f"Generated {face} elevation SVG: {output_path}")
        
        return svg_content
    
    @staticmethod
    def generate_front_elevation_svg(*args, **kwargs):
        """
        Convenience method for backwards compatibility.
        Generates front elevation by default.
        """
        return ElevationViewGenerator.generate_elevation_svg('front', *args, **kwargs)

