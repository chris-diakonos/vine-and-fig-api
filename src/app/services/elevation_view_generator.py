"""
Elevation view generator for creating architectural-style 2D elevation drawings.
Uses CadQuery 2D for precise geometric drawings.
"""
from pathlib import Path
from typing import List, Optional
import logging
import math
import cadquery as cq

from app.services.cadquery_drawing_components import CadQueryDrawingComponents

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
        
        # Collect all drawing elements
        elements = []
        
        # Ground line (create as a thin rectangle instead of a line)
        ground_y = offset_y + total_height
        ground_line = cq.Workplane("XY").rect(view_width, 2).translate((view_width/2, ground_y))
        elements.append(ground_line)
        
        # === FOUNDATION ===
        foundation_y = offset_y + roof_rise + building_height
        
        # Draw individual foundation blocks with mortar joints
        block_length = foundation_block_size[0]  # Length along the wall
        block_height = foundation_block_size[2]  # Height of each block
        joint = foundation_block_joint
        
        # Create foundation blocks using simple rectangles
        logger.info(f"Creating foundation blocks: {foundation_courses} courses, block_size={block_length}x{block_height}, joint={joint}")
        blocks_created = 0
        for course in range(foundation_courses):
            course_y = foundation_y + (course * (block_height + joint))
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
                        block = cq.Workplane("XY").rect(actual_width, block_height).translate((actual_x + actual_width/2, course_y + block_height/2))
                        elements.append(block)
                        blocks_created += 1
        
        logger.info(f"Created {blocks_created} foundation blocks")
        
        # Outline foundation
        foundation_outline = cq.Workplane("XY").rect(building_width, foundation_height).translate((offset_x + building_width/2, foundation_y + foundation_height/2))
        elements.append(foundation_outline)
        
        # === WALLS WITH SHEATHING ===
        wall_y = offset_y + roof_rise
        
        # Main wall rectangle
        main_wall = cq.Workplane("XY").rect(building_width, building_height).translate((offset_x + building_width/2, wall_y + building_height/2))
        elements.append(main_wall)
        
        # Sheathing lines (horizontal weatherboard)
        if sheathing:
            sheathing_exposure = sheathing.get('sheathing_exposure', 6)
            num_boards = int(building_height / sheathing_exposure)
            
            for i in range(1, num_boards):
                sheathing_y = wall_y + (i * sheathing_exposure)
                if sheathing_y < wall_y + building_height:
                    sheathing_line = cq.Workplane("XY").rect(building_width, 0.5).translate((offset_x + building_width/2, sheathing_y))
                    elements.append(sheathing_line)
        
        # Corner boards (vertical trim at edges)
        corner_board_width = 4
        left_corner_board = cq.Workplane("XY").rect(corner_board_width, building_height).translate((offset_x + corner_board_width/2, wall_y + building_height/2))
        right_corner_board = cq.Workplane("XY").rect(corner_board_width, building_height).translate((offset_x + building_width - corner_board_width/2, wall_y + building_height/2))
        elements.append(left_corner_board)
        elements.append(right_corner_board)
        
        # === WINDOWS ===
        
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
                            
                            # Use simple window rectangle for now
                            window_2d = cq.Workplane("XY").rect(window_width, window_height).translate((window_x + window_width/2, window_y + window_height/2))
                            elements.append(window_2d)
        
        # === DOORS ===
        
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
                    
                    # Use simple door rectangle for now
                    door_2d = cq.Workplane("XY").rect(door_width, door_height).translate((door_x + door_width/2, door_y + door_height/2))
                    elements.append(door_2d)
        
        # === ROOF ===
        
        roof_base_y = wall_y
        
        # Create roof using CadQuery
        roof_2d = CadQueryDrawingComponents.create_roof_2d(
            x=offset_x,
            y=roof_base_y,
            width=building_width,
            roof_type=roof_type,
            roof_pitch=roof_pitch,
            roof_overhang=roof_overhang,
            roof_shed_length=roof_shed_length
        )
        elements.append(roof_2d)
        
        # Create final workplane by unioning all elements
        logger.info(f"Total elements collected: {len(elements)}")
        if elements:
            # Find the first solid element to start with
            wp = None
            start_index = 0
            for i, element in enumerate(elements):
                try:
                    # Try to get the solids from this element
                    solids = element.solids().vals()
                    if solids:
                        wp = element
                        start_index = i
                        logger.info(f"Starting with element {i} (has {len(solids)} solids)")
                        break
                except Exception as e:
                    logger.warning(f"Element {i} is not a solid: {str(e)}")
                    continue
            
            if wp is None:
                logger.error("No solid elements found, creating empty workplane")
                wp = cq.Workplane("XY")
            else:
                # Union remaining elements
                logger.info(f"Unioning {len(elements)-start_index-1} more elements")
                for i, element in enumerate(elements[start_index+1:], start_index+1):
                    try:
                        wp = wp.union(element)
                        logger.info(f"Successfully unioned element {i}")
                    except Exception as e:
                        logger.error(f"Failed to union element {i}: {str(e)}")
                        # Skip this element and continue
                        continue
        else:
            logger.warning("No elements collected, creating empty workplane")
            wp = cq.Workplane("XY")
        
        # Export to SVG
        svg_content = CadQueryDrawingComponents.export_to_svg(wp, str(output_path) if output_path else None)
        
        # Add SVG wrapper with proper dimensions and background
        svg_wrapper = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{view_width}" height="{view_height}" viewBox="0 0 {view_width} {view_height}">
  <!-- Generated {face.capitalize()} Elevation -->
  <rect width="{view_width}" height="{view_height}" fill="#f8f8f0"/>
  {svg_content}
  <!-- Labels -->
  <text x="{view_width / 2}" y="{view_height - 10}" text-anchor="middle" font-family="serif" font-size="12" fill="black">
    {face.capitalize()} Elevation - {stories} Story Building
  </text>
</svg>'''
        
        # Save to file if path provided
        if output_path:
            output_path.write_text(svg_wrapper, encoding='utf-8')
            logger.info(f"Generated {face} elevation SVG: {output_path}")
        
        return svg_wrapper
    
    @staticmethod
    def generate_front_elevation_svg(*args, **kwargs):
        """
        Convenience method for backwards compatibility.
        Generates front elevation by default.
        """
        return ElevationViewGenerator.generate_elevation_svg('front', *args, **kwargs)

