"""
Reusable SVG components for architectural drawings.
Provides functions to draw windows, doors, and other building elements.
"""
from typing import List, Literal, Optional
import logging

from app.services.door_calculator import DoorCalculator

logger = logging.getLogger(__name__)


class DrawingComponents:
    """Reusable SVG components for architectural drawings."""
    
    @staticmethod
    def draw_window_section(
        x: float,
        y: float,
        width: float,
        height: float,
        operation: str = 'single-hung',
        configuration: str = '6/6'
    ) -> str:
        """
        Draw a window in section view (side profile).
        
        Args:
            x: Left position of window
            y: Top position of window
            width: Window width in inches
            height: Window height in inches
            operation: Window operation type (single-hung, double-hung, casement, fixed)
            configuration: Muntin configuration (e.g., '6/6', '2/2')
            
        Returns:
            SVG string for the window
        """
        svg_lines = []
        
        # Window frame (outer box)
        frame_thickness = 4
        svg_lines.append(f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" fill="white" stroke="black" stroke-width="1.5"/>')
        
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
            svg_lines.append(f'  <line x1="{x}" y1="{meeting_rail_y}" x2="{x + width}" y2="{meeting_rail_y}" stroke="black" stroke-width="1"/>')
            
            # Muntins (vertical dividers for panes)
            sash_height = height / 2
            if num_panes_per_sash >= 2:
                # Calculate number of rows (e.g., 6 panes = 3 rows x 2 columns)
                cols = 2 if num_panes_per_sash >= 4 else 1
                rows = num_panes_per_sash // cols if cols > 1 else num_panes_per_sash
                
                # Draw horizontal muntins for upper sash
                for i in range(1, rows):
                    muntin_y = y + (i * sash_height / rows)
                    svg_lines.append(f'  <line x1="{x}" y1="{muntin_y}" x2="{x + width}" y2="{muntin_y}" stroke="black" stroke-width="0.5"/>')
                
                # Draw horizontal muntins for lower sash
                for i in range(1, rows):
                    muntin_y = meeting_rail_y + (i * sash_height / rows)
                    svg_lines.append(f'  <line x1="{x}" y1="{muntin_y}" x2="{x + width}" y2="{muntin_y}" stroke="black" stroke-width="0.5"/>')
                
                # Draw vertical muntin (if more than 1 column)
                if cols > 1:
                    muntin_x = x + (width / 2)
                    svg_lines.append(f'  <line x1="{muntin_x}" y1="{y}" x2="{muntin_x}" y2="{y + height}" stroke="black" stroke-width="0.5"/>')
        
        elif operation == 'casement':
            # Casement window - single opening pane
            svg_lines.append(f'  <line x1="{x}" y1="{y}" x2="{x + width}" y2="{y + height}" stroke="black" stroke-width="0.5" stroke-dasharray="2,2"/>')
        
        elif operation == 'fixed':
            # Fixed window - no moving parts
            pass
        
        return '\n'.join(svg_lines)
    
    @staticmethod
    def draw_window_elevation(
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
    ) -> str:
        """
        Draw a window in elevation view (front view showing full detail).
        
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
            SVG string for the window
        """
        svg_lines = []
        
        # Outer frame (stiles and rails)
        svg_lines.append(f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" fill="white" stroke="black" stroke-width="2"/>')
        
        # Parse configuration
        # Standard: 3 panes across (columns)
        # For 6/6: 6 panes per sash ÷ 3 columns = 2 rows in each sash
        # For 6/9: 6 top ÷ 3 = 2 rows top, 9 bottom ÷ 3 = 3 rows bottom
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
        svg_lines.append(f'  <rect x="{x}" y="{y}" width="{stile_width}" height="{height}" fill="none" stroke="black" stroke-width="1"/>')
        svg_lines.append(f'  <rect x="{x + width - stile_width}" y="{y}" width="{stile_width}" height="{height}" fill="none" stroke="black" stroke-width="1"/>')
        
        # Rails (top and bottom horizontal frame members)
        svg_lines.append(f'  <rect x="{x}" y="{y}" width="{width}" height="{rail_width}" fill="none" stroke="black" stroke-width="1"/>')
        svg_lines.append(f'  <rect x="{x}" y="{y + height - rail_width}" width="{width}" height="{rail_width}" fill="none" stroke="black" stroke-width="1"/>')
        
        if operation in ['single-hung', 'double-hung']:
            # Meeting rail (middle) - positioned based on actual sash heights
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
            svg_lines.append(f'  <rect x="{x}" y="{meeting_rail_y}" width="{width}" height="{meeting_rail_width}" fill="none" stroke="black" stroke-width="1"/>')
            
            # Horizontal muntins - TOP SASH
            for row in range(1, top_rows):
                muntin_y = y + rail_width + (row * top_sash_height / top_rows)
                svg_lines.append(f'  <line x1="{x + stile_width}" y1="{muntin_y}" x2="{x + width - stile_width}" y2="{muntin_y}" stroke="black" stroke-width="{muntin_width}"/>')
            
            # Horizontal muntins - BOTTOM SASH
            for row in range(1, bottom_rows):
                muntin_y_lower = meeting_rail_y + meeting_rail_width + (row * bottom_sash_height / bottom_rows)
                svg_lines.append(f'  <line x1="{x + stile_width}" y1="{muntin_y_lower}" x2="{x + width - stile_width}" y2="{muntin_y_lower}" stroke="black" stroke-width="{muntin_width}"/>')
            
            # Vertical muntins (same for both sashes)
            for col in range(1, cols):
                muntin_x = x + stile_width + (col * inner_width / cols)
                # Upper sash
                svg_lines.append(f'  <line x1="{muntin_x}" y1="{y + rail_width}" x2="{muntin_x}" y2="{meeting_rail_y}" stroke="black" stroke-width="{muntin_width}"/>')
                # Lower sash
                svg_lines.append(f'  <line x1="{muntin_x}" y1="{meeting_rail_y + meeting_rail_width}" x2="{muntin_x}" y2="{y + height - rail_width}" stroke="black" stroke-width="{muntin_width}"/>')
        
        return '\n'.join(svg_lines)
    
    @staticmethod
    def draw_door_section(
        x: float,
        y: float,
        width: float,
        height: float,
        door_type: str = 'panel'
    ) -> str:
        """
        Draw a door in section view.
        
        Args:
            x: Left position of door
            y: Top position of door
            width: Door width in inches
            height: Door height in inches
            door_type: Type of door (panel, glass, etc.)
            
        Returns:
            SVG string for the door
        """
        svg_lines = []
        
        # Door frame
        svg_lines.append(f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" fill="#d4a574" stroke="black" stroke-width="1.5"/>')
        
        # Door panels (if panel door)
        if door_type == 'panel':
            panel_height = height / 6
            for i in range(2, 6):
                panel_y = y + (i * panel_height)
                svg_lines.append(f'  <line x1="{x + 2}" y1="{panel_y}" x2="{x + width - 2}" y2="{panel_y}" stroke="black" stroke-width="0.5"/>')
        
        return '\n'.join(svg_lines)
    
    @staticmethod
    def draw_door_elevation(
        x: float,
        y: float,
        width: float,
        height: float,
        configuration: str = 'six-panel',
        panel_type: str = 'raised-panel',
        stile_widths: Optional[List[float]] = None,
        rail_widths: Optional[List[float]] = None,
        panel_widths: Optional[List[float]] = None
    ) -> str:
        """
        Draw a door in elevation view (front view showing full detail).
        
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
            SVG string for the door
        """
        svg_lines = []
        
        # Calculate door dimensions if not provided
        door_config = DoorCalculator.calculate_door_config(width, height, configuration)
        stile_widths = stile_widths or door_config['stile_widths']
        rail_widths = rail_widths or door_config['rail_widths']
        panel_widths = panel_widths or door_config['panel_widths']
        rail_positions = door_config['rail_positions']
        panels = door_config['panels']
        
        # Door background (wood color)
        svg_lines.append(f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" fill="#c19a6b" stroke="black" stroke-width="2"/>')
        
        # Calculate stile positions
        left_stile_width = stile_widths[0]
        center_stile_width = stile_widths[1]
        right_stile_width = stile_widths[2]
        
        left_stile_x = x
        # Center stile should be at the center of the door
        center_stile_x = x + (width / 2) - (center_stile_width / 2)
        right_stile_x = x + width - right_stile_width
        
        # Draw left and right stiles (outer vertical members - full height)
        # Left stile
        svg_lines.append(f'  <line x1="{left_stile_x}" y1="{y}" x2="{left_stile_x}" y2="{y + height}" stroke="black" stroke-width="1"/>')
        svg_lines.append(f'  <line x1="{left_stile_x + left_stile_width}" y1="{y}" x2="{left_stile_x + left_stile_width}" y2="{y + height}" stroke="black" stroke-width="1"/>')
        
        # Right stile
        svg_lines.append(f'  <line x1="{right_stile_x}" y1="{y}" x2="{right_stile_x}" y2="{y + height}" stroke="black" stroke-width="1"/>')
        svg_lines.append(f'  <line x1="{right_stile_x + right_stile_width}" y1="{y}" x2="{right_stile_x + right_stile_width}" y2="{y + height}" stroke="black" stroke-width="1"/>')
        
        # Draw center stile in segments (interrupted by rails)
        current_y = y
        for i, (rail_width, rail_y) in enumerate(zip(rail_widths, rail_positions)):
            # Convert rail_y to absolute position
            absolute_rail_y = y + rail_y
            
            # Draw center stile segment from current_y to rail_y
            if absolute_rail_y > current_y:
                svg_lines.append(f'  <line x1="{center_stile_x}" y1="{current_y}" x2="{center_stile_x}" y2="{absolute_rail_y}" stroke="black" stroke-width="1"/>')
                svg_lines.append(f'  <line x1="{center_stile_x + center_stile_width}" y1="{current_y}" x2="{center_stile_x + center_stile_width}" y2="{absolute_rail_y}" stroke="black" stroke-width="1"/>')
            
            # Draw rails (horizontal members) - run full width between left/right stiles
            svg_lines.append(f'  <line x1="{left_stile_x + left_stile_width}" y1="{absolute_rail_y}" x2="{right_stile_x}" y2="{absolute_rail_y}" stroke="black" stroke-width="1"/>')
            svg_lines.append(f'  <line x1="{left_stile_x + left_stile_width}" y1="{absolute_rail_y + rail_width}" x2="{right_stile_x}" y2="{absolute_rail_y + rail_width}" stroke="black" stroke-width="1"/>')
            
            # Update current_y to after this rail
            current_y = absolute_rail_y + rail_width
        
        # Draw final center stile segment from last rail to bottom
        if current_y < y + height:
            svg_lines.append(f'  <line x1="{center_stile_x}" y1="{current_y}" x2="{center_stile_x}" y2="{y + height}" stroke="black" stroke-width="1"/>')
            svg_lines.append(f'  <line x1="{center_stile_x + center_stile_width}" y1="{current_y}" x2="{center_stile_x + center_stile_width}" y2="{y + height}" stroke="black" stroke-width="1"/>')
        
        # No panel rectangles needed - the stiles and rails define the panel spaces
        
        return '\n'.join(svg_lines)
    
    @staticmethod
    def draw_floor_joists(
        x: float,
        y: float,
        width: float,
        height: float,
        joist_spacing: float = 16
    ) -> str:
        """
        Draw floor joists in section view.
        
        Args:
            x: Left position
            y: Top position of joist system
            width: Building width
            height: Joist depth
            joist_spacing: Spacing between joists in inches
            
        Returns:
            SVG string for floor joists
        """
        svg_lines = []
        
        # Joist band (solid black)
        svg_lines.append(f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" fill="black"/>')
        
        # Individual joists (vertical lines)
        num_joists = int(width / joist_spacing)
        for i in range(num_joists):
            joist_x = x + (i * joist_spacing)
            svg_lines.append(f'  <line x1="{joist_x}" y1="{y}" x2="{joist_x}" y2="{y + height}" stroke="white" stroke-width="0.5"/>')
        
        return '\n'.join(svg_lines)

