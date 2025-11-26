"""
Door calculator for calculating door panel dimensions and layout.
"""
from typing import Dict, List, Literal


class DoorCalculator:
    """Calculates door panel dimensions and layout based on door size and configuration."""
    
    @staticmethod
    def calculate_door_config(
        width: float,
        height: float,
        configuration: Literal["four-panel", "six-panel"]
    ) -> Dict[str, any]:
        """
        Calculate door panel dimensions and layout.
        
        Args:
            width: Door width in inches
            height: Door height in inches
            configuration: Panel configuration ("four-panel" or "six-panel")
            
        Returns:
            Dictionary containing:
                - stile_widths: [left, center, right] in inches
                - rail_widths: [top, middle(s), bottom] in inches
                - panel_widths: [left, right] in inches
                - rail_positions: Y positions of rails (relative to top) in inches
                - panels: List of panel information dictionaries
        """
        # Standard door frame dimensions
        # Stile widths: left, center, right
        stile_width = 2.5  # Standard stile width
        stile_widths = [stile_width, stile_width, stile_width]
        
        # Rail widths: top, middle(s), bottom
        rail_width = 3.5  # Standard rail width
        top_rail_width = rail_width
        bottom_rail_width = rail_width
        
        # Calculate available space for panels
        # Subtract stiles and rails from total dimensions
        left_stile_width = stile_widths[0]
        right_stile_width = stile_widths[2]
        center_stile_width = stile_widths[1]
        
        # Available width for panels (between stiles)
        available_width = width - left_stile_width - right_stile_width - center_stile_width
        panel_widths = [available_width / 2, available_width / 2]  # Left and right panels
        
        # Calculate rail positions and widths based on configuration
        if configuration == "four-panel":
            # Four-panel door: 2 panels top, 2 panels bottom
            # Rails: top, middle (horizontal divider), bottom
            middle_rail_width = rail_width
            
            # Calculate panel heights
            # Top panels and bottom panels are equal height
            available_height = height - top_rail_width - middle_rail_width - bottom_rail_width
            panel_height = available_height / 2
            
            rail_widths = [top_rail_width, middle_rail_width, bottom_rail_width]
            rail_positions = [
                0,  # Top rail at top
                top_rail_width + panel_height,  # Middle rail
                top_rail_width + panel_height + middle_rail_width + panel_height  # Bottom rail
            ]
            
            # Panel information
            panels = [
                # Top left
                {
                    "x": left_stile_width,
                    "y": top_rail_width,
                    "width": panel_widths[0],
                    "height": panel_height
                },
                # Top right
                {
                    "x": left_stile_width + panel_widths[0] + center_stile_width,
                    "y": top_rail_width,
                    "width": panel_widths[1],
                    "height": panel_height
                },
                # Bottom left
                {
                    "x": left_stile_width,
                    "y": top_rail_width + panel_height + middle_rail_width,
                    "width": panel_widths[0],
                    "height": panel_height
                },
                # Bottom right
                {
                    "x": left_stile_width + panel_widths[0] + center_stile_width,
                    "y": top_rail_width + panel_height + middle_rail_width,
                    "width": panel_widths[1],
                    "height": panel_height
                }
            ]
            
        elif configuration == "six-panel":
            # Six-panel door: 2 panels top, 2 panels middle, 2 panels bottom
            # Rails: top, upper-middle, lower-middle, bottom
            middle_rail_width = rail_width
            
            # Calculate panel heights
            # Top, middle, and bottom panels are equal height
            available_height = height - top_rail_width - (2 * middle_rail_width) - bottom_rail_width
            panel_height = available_height / 3
            
            rail_widths = [top_rail_width, middle_rail_width, middle_rail_width, bottom_rail_width]
            rail_positions = [
                0,  # Top rail at top
                top_rail_width + panel_height,  # Upper middle rail
                top_rail_width + panel_height + middle_rail_width + panel_height,  # Lower middle rail
                top_rail_width + panel_height + middle_rail_width + panel_height + middle_rail_width + panel_height  # Bottom rail
            ]
            
            # Panel information
            panels = [
                # Top left
                {
                    "x": left_stile_width,
                    "y": top_rail_width,
                    "width": panel_widths[0],
                    "height": panel_height
                },
                # Top right
                {
                    "x": left_stile_width + panel_widths[0] + center_stile_width,
                    "y": top_rail_width,
                    "width": panel_widths[1],
                    "height": panel_height
                },
                # Middle left
                {
                    "x": left_stile_width,
                    "y": top_rail_width + panel_height + middle_rail_width,
                    "width": panel_widths[0],
                    "height": panel_height
                },
                # Middle right
                {
                    "x": left_stile_width + panel_widths[0] + center_stile_width,
                    "y": top_rail_width + panel_height + middle_rail_width,
                    "width": panel_widths[1],
                    "height": panel_height
                },
                # Bottom left
                {
                    "x": left_stile_width,
                    "y": top_rail_width + panel_height + middle_rail_width + panel_height + middle_rail_width,
                    "width": panel_widths[0],
                    "height": panel_height
                },
                # Bottom right
                {
                    "x": left_stile_width + panel_widths[0] + center_stile_width,
                    "y": top_rail_width + panel_height + middle_rail_width + panel_height + middle_rail_width,
                    "width": panel_widths[1],
                    "height": panel_height
                }
            ]
        else:
            # Default to four-panel if unknown configuration
            return DoorCalculator.calculate_door_config(width, height, "four-panel")
        
        return {
            "stile_widths": stile_widths,
            "rail_widths": rail_widths,
            "panel_widths": panel_widths,
            "rail_positions": rail_positions,
            "panels": panels
        }

