"""
Door configuration calculator for panel doors.
Calculates stile widths, rail widths, and panel positions.
"""
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class DoorCalculator:
    """Calculates precise dimensions for panel doors."""
    
    # Standard dimensions
    STILE_WIDTH = 4.5  # All stiles are 4.5" wide
    NUM_STILES = 3     # All panel doors have 3 vertical stiles
    LOCK_HEIGHT = 33.0  # Center of lock rail at 33" from bottom
    
    # Rail widths by door height
    RAIL_DIMENSIONS = {
        80: {
            'bottom_rail': 10.0,
            'lock_rail': 9.0,
            'top_rail': 4.5,  # Matches stile width
        },
        96: {
            'bottom_rail': 12.0,
            'lock_rail': 11.0,
            'top_rail': 4.5,  # Matches stile width
        }
    }
    
    @staticmethod
    def calculate_door_config(
        door_width: float,
        door_height: float,
        configuration: str
    ) -> dict:
        """
        Calculate complete door configuration including stiles, rails, and panels.
        
        Args:
            door_width: Total door width in inches
            door_height: Total door height (80 or 96 inches)
            configuration: 'four-panel' or 'six-panel'
            
        Returns:
            Dictionary with stile_widths, rail_widths, rail_positions, panel_widths
        """
        # Get rail dimensions for this door height
        rail_dims = DoorCalculator.RAIL_DIMENSIONS.get(
            int(door_height),
            DoorCalculator.RAIL_DIMENSIONS[96]  # Default to 96" if not found
        )
        
        # Stiles are always the same (3 stiles at 4.5" each)
        stile_widths = [DoorCalculator.STILE_WIDTH] * DoorCalculator.NUM_STILES
        
        # Calculate panel widths: (door_width - sum of stiles) / 2
        total_stile_width = sum(stile_widths)
        panel_width = (door_width - total_stile_width) / 2
        panel_widths = [panel_width, panel_width]  # Left and right panels
        
        # Calculate rail widths and positions
        if configuration == 'six-panel':
            rail_widths, rail_positions, panel_info = DoorCalculator._calculate_six_panel(
                door_height, rail_dims
            )
        else:  # four-panel
            rail_widths, rail_positions, panel_info = DoorCalculator._calculate_four_panel(
                door_height, rail_dims
            )
        
        return {
            'stile_widths': stile_widths,
            'rail_widths': rail_widths,
            'rail_positions': rail_positions,
            'panel_widths': panel_widths,
            'panels': panel_info,
            'lock_height': DoorCalculator.LOCK_HEIGHT
        }
    
    @staticmethod
    def _calculate_six_panel(door_height: float, rail_dims: dict) -> Tuple[List[float], List[float], List[dict]]:
        """
        Calculate dimensions for a 6-panel door.
        
        Rails (top to bottom):
        - Top rail: 4.5" (matches stile)
        - 2nd rail: 4.5" (matches stile)
        - Lock rail: 9" or 11" (centered at 33" from bottom)
        - Bottom rail: 10" or 12"
        
        Panels:
        - Top 2 panels: height H
        - Middle 2 panels: height 2.5H
        - Bottom 2 panels: remaining space
        
        Returns:
            Tuple of (rail_widths, rail_positions, panel_info)
        """
        top_rail = rail_dims['top_rail']  # 4.5"
        second_rail = rail_dims['top_rail']  # 4.5"
        lock_rail = rail_dims['lock_rail']  # 9" or 11"
        bottom_rail = rail_dims['bottom_rail']  # 10" or 12"
        
        # Rail widths array [top, 2nd, lock, bottom]
        rail_widths = [top_rail, second_rail, lock_rail, bottom_rail]
        
        # Calculate rail positions (from top of door)
        # Lock rail center is at 33" from BOTTOM, so center is at (door_height - 33)
        lock_rail_center = door_height - DoorCalculator.LOCK_HEIGHT
        lock_rail_top = lock_rail_center - (lock_rail / 2)
        lock_rail_bottom = lock_rail_center + (lock_rail / 2)
        
        # Bottom rail position
        bottom_rail_top = door_height - bottom_rail
        
        # Now calculate where 2nd rail should be
        # Available space between top rail and lock rail for panels
        # top_rail + H + second_rail + 2.5H = lock_rail_top
        # Let H = top panel height, 2.5H = middle panel height
        available_space = lock_rail_top - top_rail
        # available_space = H + second_rail + 2.5H
        # available_space = 3.5H + second_rail
        top_panel_height = (available_space - second_rail) / 3.5
        middle_panel_height = 2.5 * top_panel_height
        
        second_rail_top = top_rail + top_panel_height
        second_rail_bottom = second_rail_top + second_rail
        
        # Rail positions from top
        rail_positions = [0, second_rail_top, lock_rail_top, bottom_rail_top]
        
        # Calculate panel info (for reference)
        panels = [
            {'row': 0, 'height': top_panel_height, 'y': top_rail},
            {'row': 1, 'height': middle_panel_height, 'y': second_rail_bottom},
            {'row': 2, 'height': bottom_rail_top - lock_rail_bottom, 'y': lock_rail_bottom}
        ]
        
        logger.info(f"6-panel door ({door_height}\"): top_panel={top_panel_height:.2f}\", middle={middle_panel_height:.2f}\", bottom={panels[2]['height']:.2f}\"")
        logger.info(f"Rail positions: {rail_positions}")
        
        return rail_widths, rail_positions, panels
    
    @staticmethod
    def _calculate_four_panel(door_height: float, rail_dims: dict) -> Tuple[List[float], List[float], List[dict]]:
        """
        Calculate dimensions for a 4-panel door.
        
        Rails (top to bottom):
        - Top rail: 4.5" (matches stile)
        - Lock rail: 9" or 11" (centered at 33" from bottom)
        - Bottom rail: 10" or 12"
        
        Panels:
        - Top 2 panels: equal height
        - Bottom 2 panels: equal height (larger)
        
        Returns:
            Tuple of (rail_widths, rail_positions, panel_info)
        """
        top_rail = rail_dims['top_rail']  # 4.5"
        lock_rail = rail_dims['lock_rail']  # 9" or 11"
        bottom_rail = rail_dims['bottom_rail']  # 10" or 12"
        
        # Rail widths array [top, lock, bottom]
        rail_widths = [top_rail, lock_rail, bottom_rail]
        
        # Calculate rail positions (from top of door)
        lock_rail_center = door_height - DoorCalculator.LOCK_HEIGHT
        lock_rail_top = lock_rail_center - (lock_rail / 2)
        lock_rail_bottom = lock_rail_center + (lock_rail / 2)
        
        bottom_rail_top = door_height - bottom_rail
        
        # Rail positions from top
        rail_positions = [0, lock_rail_top, bottom_rail_top]
        
        # Calculate panel info
        top_panel_height = lock_rail_top - top_rail
        bottom_panel_height = bottom_rail_top - lock_rail_bottom
        
        panels = [
            {'row': 0, 'height': top_panel_height, 'y': top_rail},
            {'row': 1, 'height': bottom_panel_height, 'y': lock_rail_bottom}
        ]
        
        logger.info(f"4-panel door ({door_height}\"): top_panel={top_panel_height:.2f}\", bottom={bottom_panel_height:.2f}\"")
        logger.info(f"Rail positions: {rail_positions}")
        
        return rail_widths, rail_positions, panels
    
    @staticmethod
    def get_default_config(door_size: str, configuration: str) -> dict:
        """
        Get default stile_widths, rail_widths, and panel_widths for a door.
        
        Args:
            door_size: Door size string (e.g., "36x96")
            configuration: 'four-panel' or 'six-panel'
            
        Returns:
            Dictionary with stile_widths, rail_widths, and panel_widths arrays
        """
        # Parse door dimensions
        door_width, door_height = [float(x) for x in door_size.split('x')]
        
        # Calculate full configuration
        config = DoorCalculator.calculate_door_config(door_width, door_height, configuration)
        
        return {
            'stile_widths': config['stile_widths'],
            'rail_widths': config['rail_widths'],
            'panel_widths': config['panel_widths']
        }

