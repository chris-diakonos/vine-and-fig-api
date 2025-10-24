"""
CadQuery-based drawing components for architectural drawings.
Provides functions to draw windows, doors, and other building elements using CadQuery 2D.
"""
import cadquery as cq
from typing import List, Literal, Optional
import logging
import math

from app.services.door_calculator import DoorCalculator
from app.services.molding_shapes import (
    create_ovolo, create_bead, create_astragal, create_torus, create_cavetto,
    create_cyma_recta, create_cyma_reversa, create_scotia, create_fillet,
    ClassicalProfiles, CustomComposite, ProfileLibrary
)

logger = logging.getLogger(__name__)


class CadQueryDrawingComponents:
    """CadQuery-based reusable components for architectural drawings."""
    
    @staticmethod
    def create_window_section_2d(
        x: float,
        y: float,
        width: float,
        height: float,
        operation: str = 'single-hung',
        configuration: str = '6/6'
    ) -> cq.Workplane:
        """
        Create a window in section view (side profile) using CadQuery 2D.
        
        Args:
            x: Left position of window
            y: Top position of window
            width: Window width in inches
            height: Window height in inches
            operation: Window operation type (single-hung, double-hung, casement, fixed)
            configuration: Muntin configuration (e.g., '6/6', '2/2')
            
        Returns:
            CadQuery Workplane with the window section
        """
        # Start with a 2D workplane
        wp = cq.Workplane("XY")
        
        # Window frame (outer box)
        frame = wp.rect(width, height).translate((x + width/2, y + height/2))
        
        # Sashes (depending on operation type)
        if operation in ['single-hung', 'double-hung']:
            # Parse configuration (e.g., '6/6' means 6 panes top, 6 panes bottom)
            try:
                top_panes, bottom_panes = configuration.split('/')
                num_panes_per_sash = int(top_panes)
            except:
                num_panes_per_sash = 6
            
            # Meeting rail (middle horizontal divider)
            meeting_rail_y = y + (height / 2)
            meeting_rail = wp.rect(width, 0.5).translate((x + width/2, meeting_rail_y))
            
            # Muntins (vertical dividers for panes)
            sash_height = height / 2
            if num_panes_per_sash >= 2:
                # Calculate number of rows (e.g., 6 panes = 3 rows x 2 columns)
                cols = 2 if num_panes_per_sash >= 4 else 1
                rows = num_panes_per_sash // cols if cols > 1 else num_panes_per_sash
                
                # Draw horizontal muntins for upper sash
                for i in range(1, rows):
                    muntin_y = y + (i * sash_height / rows)
                    muntin = wp.rect(width, 0.25).translate((x + width/2, muntin_y))
                    frame = frame.union(muntin)
                
                # Draw horizontal muntins for lower sash
                for i in range(1, rows):
                    muntin_y = meeting_rail_y + (i * sash_height / rows)
                    muntin = wp.rect(width, 0.25).translate((x + width/2, muntin_y))
                    frame = frame.union(muntin)
                
                # Draw vertical muntin (if more than 1 column)
                if cols > 1:
                    muntin_x = x + (width / 2)
                    muntin = wp.rect(0.25, height).translate((muntin_x, y + height/2))
                    frame = frame.union(muntin)
            
            frame = frame.union(meeting_rail)
        
        elif operation == 'casement':
            # Casement window - single opening pane with diagonal line (as thin rectangle)
            diagonal = wp.rect(width, 0.5).translate((x + width/2, y + height/2))
            frame = frame.union(diagonal)
        
        elif operation == 'fixed':
            # Fixed window - no moving parts, just frame
            pass
        
        return frame
    
    @staticmethod
    def create_window_elevation_2d(
        x: float,
        y: float,
        width: float,
        height: float,
        operation: str = 'single-hung',
        configuration: str = '6/6',
        stile_width: float = 2.0,
        rail_width: float = 3.0,
        muntin_width: float = 1.0,
        meeting_rail_width: float = 1.0
    ) -> cq.Workplane:
        """
        Create a window in elevation view (front view showing full detail) using CadQuery 2D.
        
        Args:
            x: Left position of window
            y: Top position of window
            width: Window width in inches
            height: Window height in inches
            operation: Window operation type
            configuration: Muntin configuration (e.g., '6/6')
            stile_width: Width of vertical frame members
            rail_width: Width of horizontal frame members
            muntin_width: Width of interior dividers
            meeting_rail_width: Width of meeting rail
            
        Returns:
            CadQuery Workplane with the window elevation
        """
        # Start with a 2D workplane
        wp = cq.Workplane("XY")
        
        # Outer frame (stiles and rails)
        outer_frame = wp.rect(width, height).translate((x + width/2, y + height/2))
        
        # Parse configuration
        try:
            top_panes, bottom_panes = configuration.split('/')
            cols = 3  # Standard: 3 panes across
            top_rows = int(top_panes) // cols
            bottom_rows = int(bottom_panes) // cols
        except:
            cols = 3
            top_rows = 2
            bottom_rows = 2
        
        # Stiles (vertical frame members)
        left_stile = wp.rect(stile_width, height).translate((x + stile_width/2, y + height/2))
        right_stile = wp.rect(stile_width, height).translate((x + width - stile_width/2, y + height/2))
        
        # Rails (top and bottom horizontal frame members)
        top_rail = wp.rect(width, rail_width).translate((x + width/2, y + rail_width/2))
        bottom_rail = wp.rect(width, rail_width).translate((x + width/2, y + height - rail_width/2))
        
        window = outer_frame.union(left_stile).union(right_stile).union(top_rail).union(bottom_rail)
        
        if operation in ['single-hung', 'double-hung']:
            # Calculate sash heights based on rows
            inner_width = width - (2 * stile_width)
            
            # Calculate individual sash heights (simplified - proportional to rows)
            total_rows = top_rows + bottom_rows
            top_sash_proportion = top_rows / total_rows
            bottom_sash_proportion = bottom_rows / total_rows
            
            available_height = height - (2 * rail_width) - meeting_rail_width
            top_sash_height = available_height * top_sash_proportion
            bottom_sash_height = available_height * bottom_sash_proportion
            
            meeting_rail_y = y + rail_width + top_sash_height
            meeting_rail = wp.rect(width, meeting_rail_width).translate((x + width/2, meeting_rail_y))
            window = window.union(meeting_rail)
            
            # Horizontal muntins - TOP SASH
            for row in range(1, top_rows):
                muntin_y = y + rail_width + (row * top_sash_height / top_rows)
                muntin = wp.rect(inner_width, muntin_width).translate((x + width/2, muntin_y))
                window = window.union(muntin)
            
            # Horizontal muntins - BOTTOM SASH
            for row in range(1, bottom_rows):
                muntin_y_lower = meeting_rail_y + meeting_rail_width + (row * bottom_sash_height / bottom_rows)
                muntin = wp.rect(inner_width, muntin_width).translate((x + width/2, muntin_y_lower))
                window = window.union(muntin)
            
            # Vertical muntins (same for both sashes)
            for col in range(1, cols):
                muntin_x = x + stile_width + (col * inner_width / cols)
                # Upper sash
                upper_muntin = wp.rect(muntin_width, top_sash_height).translate((muntin_x, y + rail_width + top_sash_height/2))
                window = window.union(upper_muntin)
                # Lower sash
                lower_muntin = wp.rect(muntin_width, bottom_sash_height).translate((muntin_x, meeting_rail_y + meeting_rail_width + bottom_sash_height/2))
                window = window.union(lower_muntin)
        
        return window
    
    @staticmethod
    def create_door_section_2d(
        x: float,
        y: float,
        width: float,
        height: float,
        door_type: str = 'panel'
    ) -> cq.Workplane:
        """
        Create a door in section view using CadQuery 2D.
        
        Args:
            x: Left position of door
            y: Top position of door
            width: Door width in inches
            height: Door height in inches
            door_type: Type of door (panel, glass, etc.)
            
        Returns:
            CadQuery Workplane with the door section
        """
        # Start with a 2D workplane
        wp = cq.Workplane("XY")
        
        # Door frame
        door_frame = wp.rect(width, height).translate((x + width/2, y + height/2))
        
        # Door panels (if panel door)
        if door_type == 'panel':
            panel_height = height / 6
            for i in range(2, 6):
                panel_y = y + (i * panel_height)
                panel = wp.rect(width - 4, 0.5).translate((x + width/2, panel_y))
                door_frame = door_frame.union(panel)
        
        return door_frame
    
    @staticmethod
    def create_door_elevation_2d(
        x: float,
        y: float,
        width: float,
        height: float,
        configuration: str = 'six-panel',
        panel_type: str = 'raised-panel',
        stile_widths: Optional[List[float]] = None,
        rail_widths: Optional[List[float]] = None,
        panel_widths: Optional[List[float]] = None
    ) -> cq.Workplane:
        """
        Create a door in elevation view (front view showing full detail) using CadQuery 2D.
        
        Args:
            x: Left position of door
            y: Top position of door
            width: Door width in inches
            height: Door height in inches
            configuration: Panel configuration (four-panel, six-panel)
            panel_type: Type of panels (raised-panel, flat-panel)
            stile_widths: Array of stile widths [left, center, right] (defaults calculated)
            rail_widths: Array of rail widths [top to bottom] (defaults calculated)
            panel_widths: Array of panel widths [left, right] (defaults calculated)
            
        Returns:
            CadQuery Workplane with the door elevation
        """
        # Start with a 2D workplane
        wp = cq.Workplane("XY")
        
        # Calculate door dimensions if not provided
        door_config = DoorCalculator.calculate_door_config(width, height, configuration)
        stile_widths = stile_widths or door_config['stile_widths']
        rail_widths = rail_widths or door_config['rail_widths']
        panel_widths = panel_widths or door_config['panel_widths']
        rail_positions = door_config['rail_positions']
        panels = door_config['panels']
        
        # Door background (wood color)
        door_background = wp.rect(width, height).translate((x + width/2, y + height/2))
        
        # Calculate stile positions
        left_stile_width = stile_widths[0]
        center_stile_width = stile_widths[1]
        right_stile_width = stile_widths[2]
        
        left_stile_x = x
        center_stile_x = x + (width / 2) - (center_stile_width / 2)
        right_stile_x = x + width - right_stile_width
        
        # Draw left and right stiles (outer vertical members - full height)
        left_stile = wp.rect(left_stile_width, height).translate((left_stile_x + left_stile_width/2, y + height/2))
        right_stile = wp.rect(right_stile_width, height).translate((right_stile_x + right_stile_width/2, y + height/2))
        
        door = door_background.union(left_stile).union(right_stile)
        
        # Draw center stile in segments (interrupted by rails)
        current_y = y
        for i, (rail_width, rail_y) in enumerate(zip(rail_widths, rail_positions)):
            # Convert rail_y to absolute position
            absolute_rail_y = y + rail_y
            
            # Draw center stile segment from current_y to rail_y
            if absolute_rail_y > current_y:
                center_stile_segment = wp.rect(center_stile_width, absolute_rail_y - current_y).translate((center_stile_x + center_stile_width/2, current_y + (absolute_rail_y - current_y)/2))
                door = door.union(center_stile_segment)
            
            # Draw rails (horizontal members) - run full width between left/right stiles
            rail = wp.rect(width - left_stile_width - right_stile_width, rail_width).translate((x + width/2, absolute_rail_y + rail_width/2))
            door = door.union(rail)
            
            # Update current_y to after this rail
            current_y = absolute_rail_y + rail_width
        
        # Draw final center stile segment from last rail to bottom
        if current_y < y + height:
            final_center_stile = wp.rect(center_stile_width, y + height - current_y).translate((center_stile_x + center_stile_width/2, current_y + (y + height - current_y)/2))
            door = door.union(final_center_stile)
        
        return door
    
    @staticmethod
    def create_floor_joists_2d(
        x: float,
        y: float,
        width: float,
        height: float,
        joist_spacing: float = 16
    ) -> cq.Workplane:
        """
        Create floor joists in section view using CadQuery 2D.
        
        Args:
            x: Left position
            y: Top position of joist system
            width: Building width
            height: Joist depth
            joist_spacing: Spacing between joists in inches
            
        Returns:
            CadQuery Workplane with the floor joists
        """
        # Start with a 2D workplane
        wp = cq.Workplane("XY")
        
        # Joist band (solid black)
        joist_band = wp.rect(width, height).translate((x + width/2, y + height/2))
        
        # Individual joists (vertical lines)
        num_joists = int(width / joist_spacing)
        for i in range(num_joists):
            joist_x = x + (i * joist_spacing)
            joist = wp.rect(0.5, height).translate((joist_x, y + height/2))
            joist_band = joist_band.union(joist)
        
        return joist_band
    
    @staticmethod
    def create_wall_2d(
        x: float,
        y: float,
        width: float,
        height: float,
        wall_thickness: float = 4.0
    ) -> cq.Workplane:
        """
        Create a wall section using CadQuery 2D.
        
        Args:
            x: Left position
            y: Top position
            width: Wall width
            height: Wall height
            wall_thickness: Wall thickness
            
        Returns:
            CadQuery Workplane with the wall
        """
        # Start with a 2D workplane
        wp = cq.Workplane("XY")
        
        # Wall rectangle
        wall = wp.rect(width, height).translate((x + width/2, y + height/2))
        
        return wall
    
    @staticmethod
    def create_foundation_blocks_2d(
        x: float,
        y: float,
        width: float,
        height: float,
        block_length: float,
        block_height: float,
        joint: float,
        courses: int
    ) -> cq.Workplane:
        """
        Create foundation blocks with mortar joints using CadQuery 2D.
        
        Args:
            x: Left position
            y: Top position
            width: Foundation width
            height: Foundation height
            block_length: Length of each block
            block_height: Height of each block
            joint: Mortar joint thickness
            courses: Number of courses
            
        Returns:
            CadQuery Workplane with the foundation blocks
        """
        # Start with a 2D workplane
        wp = cq.Workplane("XY")
        
        # Calculate course height (block + joint)
        course_height = block_height + joint
        
        # Draw each course (row) of blocks
        for course in range(courses):
            course_y = y + (course * course_height)
            
            # Calculate number of blocks needed for this row
            num_blocks = int(width / (block_length + joint)) + 1
            
            # Offset every other row for running bond pattern
            x_offset = 0
            if course % 2 == 1:
                x_offset = -(block_length / 2)
            
            # Draw blocks in this course
            for i in range(num_blocks):
                block_x = x + x_offset + (i * (block_length + joint))
                
                # Only draw if block is within foundation width
                if block_x < x + width and block_x + block_length > x:
                    # Clip block to foundation width
                    actual_x = max(block_x, x)
                    actual_width = min(block_x + block_length, x + width) - actual_x
                    
                    if actual_width > 0:
                        # Draw block
                        block = wp.rect(actual_width, block_height).translate((actual_x + actual_width/2, course_y + block_height/2))
                        wp = wp.union(block)
        
        return wp
    
    @staticmethod
    def create_roof_2d(
        x: float,
        y: float,
        width: float,
        roof_type: str,
        roof_pitch: float,
        roof_overhang: float = 12,
        roof_shed_length: float = 0
    ) -> cq.Workplane:
        """
        Create roof geometry using CadQuery 2D.
        
        Args:
            x: Left position
            y: Top position
            width: Building width
            roof_type: Type of roof (side-gable, front-gable, etc.)
            roof_pitch: Roof pitch in degrees
            roof_overhang: Roof overhang
            roof_shed_length: Shed length for side-gable-with-shed
            
        Returns:
            CadQuery Workplane with the roof
        """
        # Start with a 2D workplane
        wp = cq.Workplane("XY")
        
        roof_pitch_radians = math.radians(roof_pitch)
        
        if roof_type == 'side-gable':
            # Side-gable: gable ends on sides, ridge runs front-to-back
            roof_run = width / 2
            roof_rise = math.tan(roof_pitch_radians) * roof_run
            roof_peak_y = y - roof_rise
            
            # Draw roof as triangle using polygon
            roof_points = [
                (x - roof_overhang, y),
                (x + width/2, roof_peak_y),
                (x + width + roof_overhang, y)
            ]
            roof = wp.polyline(roof_points).close()
            
        elif roof_type == 'front-gable':
            # Front-gable: gable end on front, ridge runs left-to-right
            roof_run = width / 2
            roof_rise = math.tan(roof_pitch_radians) * roof_run
            roof_peak_y = y - roof_rise
            
            # Draw roof as triangle using polygon
            roof_points = [
                (x - roof_overhang, y),
                (x + width/2, roof_peak_y),
                (x + width + roof_overhang, y)
            ]
            roof = wp.polyline(roof_points).close()
            
        elif roof_type == 'side-gable-with-shed':
            # Side-gable-with-shed: normal side-gable in front, shed extension in rear
            shed_length = roof_shed_length
            gable_length = width - shed_length
            
            # Calculate gable roof slope based on gable length
            roof_run = gable_length / 2
            roof_rise = math.tan(roof_pitch_radians) * roof_run
            roof_peak_y = y - roof_rise
            
            if shed_length > 0:
                # Shed has a lower pitch (typically 3:12 or 4:12)
                shed_pitch_ratio = 0.25  # 3:12 pitch for shed
                shed_rise = (shed_pitch_ratio * shed_length)
                shed_peak_y = roof_peak_y - shed_rise
                
                # Draw complex roof profile using polygon
                roof_points = [
                    (x - roof_overhang, y),
                    (x + gable_length/2, roof_peak_y),
                    (x + gable_length, y),
                    (x + width + roof_overhang, shed_peak_y)
                ]
                roof = wp.polyline(roof_points).close()
            else:
                # No shed - just normal gable
                roof_points = [
                    (x - roof_overhang, y),
                    (x + width/2, roof_peak_y),
                    (x + width + roof_overhang, y)
                ]
                roof = wp.polyline(roof_points).close()
                
        else:
            # Default flat roof
            roof = wp.rect(width + 2*roof_overhang, 2).translate((x + width/2, y - 1))
        
        return roof
    
    @staticmethod
    def create_crown_molding_2d(
        x: float,
        y: float,
        width: float,
        molding_style: str = 'classical',
        molding_height: float = 6.0
    ) -> cq.Workplane:
        """
        Create crown molding using the molding shapes library.
        
        Args:
            x: Left position
            y: Top position
            width: Molding width
            molding_style: Style of molding (classical, georgian, victorian, etc.)
            molding_height: Height of molding
            
        Returns:
            CadQuery Workplane with the crown molding
        """
        # Create molding profile based on style
        if molding_style == 'classical':
            molding = ClassicalProfiles.crown_molding(length=width)
        elif molding_style == 'georgian':
            molding = ProfileLibrary.georgian_crown(length=width)
        elif molding_style == 'victorian':
            molding = ProfileLibrary.victorian_base(length=width)
        else:
            # Default to simple ovolo
            molding = create_ovolo(
                width=width,
                height=molding_height,
                length=width,
                radius_ratio=0.6
            )
        
        # Position the molding
        molding = molding.translate((x + width/2, y + molding_height/2, 0))
        
        return molding
    
    @staticmethod
    def create_base_molding_2d(
        x: float,
        y: float,
        width: float,
        molding_style: str = 'classical',
        molding_height: float = 4.0
    ) -> cq.Workplane:
        """
        Create base molding using the molding shapes library.
        
        Args:
            x: Left position
            y: Top position
            width: Molding width
            molding_style: Style of molding (classical, georgian, victorian, etc.)
            molding_height: Height of molding
            
        Returns:
            CadQuery Workplane with the base molding
        """
        # Create molding profile based on style
        if molding_style == 'classical':
            molding = ClassicalProfiles.base_molding(length=width)
        elif molding_style == 'georgian':
            molding = ProfileLibrary.georgian_crown(length=width)
        elif molding_style == 'victorian':
            molding = ProfileLibrary.victorian_base(length=width)
        else:
            # Default to simple ovolo
            molding = create_ovolo(
                width=width,
                height=molding_height,
                length=width,
                radius_ratio=0.6
            )
        
        # Position the molding
        molding = molding.translate((x + width/2, y + molding_height/2, 0))
        
        return molding
    
    @staticmethod
    def create_custom_molding_2d(
        x: float,
        y: float,
        width: float,
        molding_elements: List[dict]
    ) -> cq.Workplane:
        """
        Create custom molding using the CustomComposite builder.
        
        Args:
            x: Left position
            y: Top position
            width: Molding width
            molding_elements: List of molding element dictionaries
            
        Returns:
            CadQuery Workplane with the custom molding
        """
        # Create custom composite molding
        custom_builder = CustomComposite()
        
        for element in molding_elements:
            element_type = element.get('type', 'ovolo')
            params = element.get('params', {})
            
            if element_type == 'ovolo':
                custom_builder.ovolo(**params)
            elif element_type == 'scotia':
                custom_builder.scotia(**params)
            elif element_type == 'fillet':
                custom_builder.fillet(**params)
            elif element_type == 'cyma_recta':
                custom_builder.cyma_recta(**params)
            elif element_type == 'cyma_reversa':
                custom_builder.cyma_reversa(**params)
            elif element_type == 'astragal':
                custom_builder.astragal(**params)
            elif element_type == 'torus':
                custom_builder.torus(**params)
            elif element_type == 'bead':
                custom_builder.bead(**params)
            elif element_type == 'cavetto':
                custom_builder.cavetto(**params)
        
        # Build the custom molding
        molding = custom_builder.build(length=width)
        
        # Position the molding
        molding = molding.translate((x + width/2, y, 0))
        
        return molding
    
    @staticmethod
    def export_to_svg(workplane: cq.Workplane, output_path: str = None) -> str:
        """
        Export CadQuery Workplane to SVG format.
        
        Args:
            workplane: CadQuery Workplane to export
            output_path: Optional path to save SVG file
            
        Returns:
            SVG content as string
        """
        try:
            # Export to SVG
            svg_content = workplane.val().exportSvg()
            
            # Save to file if path provided
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                logger.info(f"Exported SVG to: {output_path}")
            
            return svg_content
            
        except Exception as e:
            logger.error(f"Failed to export SVG: {str(e)}")
            # Fallback to basic SVG
            return f'<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="20">Export Error: {str(e)}</text></svg>'
