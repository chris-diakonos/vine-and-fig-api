"""
Windows builder service using CadQuery.
"""
import cadquery as cq
import math
from typing import Dict, Any, List, Optional
from app.models.openings import Window
from app.models.floorplan import Dimensions, Floorplan


class WindowsBuilder:
    """Builds window geometry using CadQuery."""
    
    @staticmethod
    def _beaded_board(width: float, height: float, bead_size: float) -> cq.Workplane:
        """
        Create a beaded board profile.
        
        Args:
            width: Width of the board
            height: Height of the board
            bead_size: Size of the bead
            
        Returns:
            2D CadQuery Workplane profile
        """
        profile_points = []
        segments = 32
        increment = 180 / segments

        # Define the bead
        bead_diameter = bead_size
        bead_radius = bead_diameter / 2
        board_height = height - bead_diameter
        board_width = width
        center_x = board_width - bead_radius
        center_y = -height + bead_radius

        # Add initial point
        profile_points.append((0, 0))
        profile_points.append((board_width, 0))
        profile_points.append((board_width, -board_height))

        # Add the bead points from 90 to 270 degrees
        for segment in range(1, segments):
            if segment <= (segments / 2):
                angle_degrees = 90 - (segment * increment)
            else:
                segment_counter = segment - (segments / 2)
                angle_degrees = 360 - (segment_counter * increment)

            angle_radians = math.radians(angle_degrees)
            
            bead_x = center_x + (bead_radius * math.cos(angle_radians))
            bead_y = center_y + (bead_radius * math.sin(angle_radians))

            profile_points.append((bead_x, bead_y))

        # Add the board corners
        profile_points.append((0, -height))

        # Create the 2D profile
        profile = cq.Workplane("XZ").polyline(profile_points).close()

        return profile
    
    @staticmethod
    def _beaded_sill(width: float, inside_height: float, outside_height: float, bead_size: float) -> cq.Workplane:
        """
        Create a beaded sill profile.
        
        Args:
            width: Width of the sill
            inside_height: Inside height of the sill
            outside_height: Outside height of the sill
            bead_size: Size of the bead
            
        Returns:
            2D CadQuery Workplane profile
        """
        profile_points = []
        segments = 32
        increment = 180 / segments

        # Define the bead
        bead_diameter = bead_size
        bead_radius = bead_diameter / 2
        board_height = inside_height - bead_diameter
        board_width = width
        center_x = board_width - bead_radius
        center_y = -inside_height + bead_radius
        rain_stem = 0.5
        rain_slope = (inside_height - outside_height)
        siding_notch = 0.375
        wall_width = 4.00
        siding_notch_x = wall_width + siding_notch

        # Add initial point
        profile_points.append((0, 0))
        profile_points.append((rain_stem, 0))
        profile_points.append((rain_stem, -rain_stem))
        profile_points.append((board_width, -rain_slope))
        profile_points.append((board_width, -board_height))

        # Add the bead points from 90 to 270 degrees
        for segment in range(1, segments):
            if segment <= (segments / 2):
                angle_degrees = 90 - (segment * increment)
            else:
                segment_counter = segment - (segments / 2)
                angle_degrees = 360 - (segment_counter * increment)

            angle_radians = math.radians(angle_degrees)
            
            bead_x = center_x + (bead_radius * math.cos(angle_radians))
            bead_y = center_y + (bead_radius * math.sin(angle_radians))

            profile_points.append((bead_x, bead_y))

        # Add the board corners
        profile_points.append((siding_notch_x, -inside_height))
        profile_points.append((siding_notch_x, -inside_height + siding_notch))
        profile_points.append((wall_width, -inside_height + siding_notch))
        profile_points.append((wall_width, -inside_height))
        profile_points.append((0, -inside_height))

        # Create the 2D profile
        profile = cq.Workplane("XZ").polyline(profile_points).close()

        return profile
    
    @staticmethod
    def _window_frame(
        window: Window,
        center_x: float,
        center_y: float,
        chair_rail_bottom_z: float,
        face: str
    ) -> cq.Assembly:
        """
        Create a window frame with bottom of opening at chair_rail_bottom_z.
        
        Args:
            window: Window specification
            center_x: X coordinate of opening center
            center_y: Y coordinate of opening center
            chair_rail_bottom_z: Z coordinate of bottom of opening (chair rail height)
            face: Wall face ("front", "rear", "left", "right") - determines rotation
            
        Returns:
            CadQuery Assembly with window frame components
        """
        # Parse window size and configuration
        size_parts = window.size.split('x')
        light_width = float(size_parts[0])
        light_height = float(size_parts[1])
        
        configuration_parts = window.configuration.split("/")
        top_sash_lights = int(configuration_parts[0])
        bottom_sash_lights = int(configuration_parts[1])
        
        # Frame parameters - use values from Window model or defaults
        frame_depth = 4
        frame_width = 5
        top_rail_width = window.rail_width
        bottom_rail_width = window.rail_width
        meeting_rail_width = window.meeting_rail_width
        muntin_width = window.muntin_width
        
        # Sill parameters (fixed values - could be made configurable)
        sill_inside_height = 5.0
        sill_outside_height = 3.0
        sill_width = 5.0
        
        # Joint parameters (fixed values - standard joinery)
        bead_size = 0.625
        tenon_size = 2.0
        tenon_type = "blind"  # Could be made configurable
        lap_thickness = 1.0
        lap_size = 3.0
        
        # Precalculate part lengths
        glazing_rabbet = 0.25
        top_stile_length = ((top_sash_lights / 3) * (light_height - (glazing_rabbet * 2))) + top_rail_width + meeting_rail_width + (((top_sash_lights / 3) - 1) * muntin_width)
        bottom_stile_length = ((bottom_sash_lights / 3) * (light_height - (glazing_rabbet * 2))) + bottom_rail_width + meeting_rail_width + (((bottom_sash_lights / 3) - 1) * muntin_width)
        pulley_stile_length = top_stile_length + bottom_stile_length - meeting_rail_width
        
        if tenon_type == "blind":
            tenon_adjustment = -1
            tenon_length = frame_width + (tenon_adjustment / 2)
        else:
            tenon_adjustment = 0
            tenon_length = frame_width
        
        rail_length = (light_width * 3) + (frame_width * 2) + (muntin_width * 2) - (glazing_rabbet * 6) + tenon_adjustment
        header_length = (frame_width * 2) + rail_length
        
        # Calculate the center Z position based on the actual opening height
        # The bottom of the opening (where sill sits) should be at chair_rail_bottom_z
        # So the center is at: bottom + (opening_height / 2)
        center_z = chair_rail_bottom_z + (pulley_stile_length / 2)
        
        # Create window frame assembly
        window_frame = cq.Assembly()
        
        # For left/right walls, swap X and Y translation coordinates only
        # Keep all rotations the same - just swap which axis we use for positioning
        if face in ["left", "right"]:
            # Swap coordinates: stiles positioned along Y, header/sill along Y
            stile_pos_left = center_y - (header_length / 2)
            stile_pos_right = center_y + (header_length / 2) - frame_width
            header_sill_const = center_x
            header_sill_start = center_y - (header_length / 2)
        else:
            # Front/rear: stiles positioned along X, header/sill along X
            stile_pos_left = center_x - (header_length / 2)
            stile_pos_right = center_x + (header_length / 2) - frame_width
            header_sill_const = center_y
            header_sill_start = center_x - (header_length / 2)
        
        # Frame center point for rotation
        frame_center = (center_x, center_y, center_z)
        
        # Left stile (vertical piece)
        stile_z = center_z + (pulley_stile_length / 2) - (frame_width / 2)
        left_frame = WindowsBuilder._beaded_board(frame_width, frame_depth, bead_size).extrude(pulley_stile_length + 2).rotate((0, 0, 0), (1, 0, 0), 90)
        if face in ["left", "right"]:
            left_frame = left_frame.translate((header_sill_const, stile_pos_left, stile_z))
        else:
            left_frame = left_frame.translate((stile_pos_left, header_sill_const, stile_z))
        window_frame.add(left_frame, name="left_frame", color=cq.Color(0.8, 0.7, 0.6))
        
        # Right stile (vertical piece)
        right_frame = WindowsBuilder._beaded_board(frame_width, frame_depth, bead_size).extrude(pulley_stile_length + 2).rotate((0, 0, 0), (1, 0, 0), 90)
        if face in ["left", "right"]:
            right_frame = right_frame.translate((header_sill_const, stile_pos_right, stile_z))
        else:
            right_frame = right_frame.translate((stile_pos_right, header_sill_const, stile_z))
        window_frame.add(right_frame, name="right_frame", color=cq.Color(0.8, 0.7, 0.6))
        
        # Top header (horizontal piece)
        header_z = center_z + ((pulley_stile_length + frame_width) / 2)
        if face in ["left", "right"]:
            # For left/right walls, header extends in Y - use X rotation to keep profile aligned perpendicular to wall
            # Create profile, extrude, rotate into horizontal position, then rotate to face along wall
            top_frame = WindowsBuilder._beaded_board(frame_width, frame_depth, bead_size).extrude(header_length).rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), 90)
            top_frame = top_frame.translate((header_sill_const, header_sill_start, header_z))
        else:
            # For front/rear walls, header extends in X, rotate around Z
            top_frame = WindowsBuilder._beaded_board(frame_depth, frame_width, bead_size).extrude(header_length).rotate((0, 0, 0), (0, 0, 1), 90)
            top_frame = top_frame.translate((header_sill_start, header_sill_const, header_z))
        window_frame.add(top_frame, name="top_frame", color=cq.Color(0.8, 0.7, 0.6))
        
        # Bottom sill (horizontal piece)
        sill_z = center_z - (pulley_stile_length / 2)
        if face in ["left", "right"]:
            # For left/right walls, sill extends in Y - use X rotation to keep profile aligned perpendicular to wall
            # Create profile, extrude, rotate into horizontal position, then rotate to face along wall
            bottom_frame = WindowsBuilder._beaded_sill(sill_width, sill_inside_height, sill_outside_height, bead_size).extrude(header_length).rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), 90)
            bottom_frame = bottom_frame.translate((header_sill_const, header_sill_start, sill_z))
        else:
            # For front/rear walls, sill extends in X, rotate around Z
            bottom_frame = WindowsBuilder._beaded_sill(sill_width, sill_inside_height, sill_outside_height, bead_size).extrude(header_length).rotate((0, 0, 0), (0, 0, 1), 90)
            bottom_frame = bottom_frame.translate((header_sill_start, header_sill_const, sill_z))
        window_frame.add(bottom_frame, name="bottom_frame_sill", color=cq.Color(0.8, 0.7, 0.6))
        
        return window_frame
    
    @staticmethod
    def build(
        windows: List[Window],
        dimensions: Dimensions,
        stories: int,
        floor_heights: List[float],
        calculated_chair_rail_heights: List[float],
        floorplan: Optional[Floorplan] = None,
        door_openings: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[cq.Assembly]:
        """
        Build window frames at specified locations or at bays, skipping door openings.
        
        Args:
            windows: List of window specifications (one per story + attic)
            dimensions: Building dimensions
            stories: Number of stories
            floor_heights: Pre-calculated floor heights for each story
            calculated_chair_rail_heights: Pre-calculated chair rail heights for each story
            floorplan: Optional floorplan for bay information
            door_openings: Optional list of door opening locations (wall, position, floor)
            
        Returns:
            CadQuery Assembly with window frames, or None if no windows
        """
        if not windows:
            return None
        
        windows_assembly = cq.Assembly()
        
        # Build set of door locations for quick lookup (wall, position, floor)
        door_locations = set()
        if door_openings:
            for door_info in door_openings:
                door_locations.add((door_info['wall'], door_info['position'], door_info['floor']))
        
        # Check if windows have explicit locations
        has_explicit_locations = any(w.wall and w.position is not None and w.floor is not None for w in windows)
        
        if has_explicit_locations:
            # Honor explicit window locations
            for i, window in enumerate(windows):
                if not (window.wall and window.position is not None and window.floor is not None):
                    continue  # Skip windows without explicit locations
                
                # Convert floor to 0-indexed story
                story_idx = window.floor - 1
                if story_idx < 0 or story_idx >= stories:
                    continue  # Skip invalid floors
                
                # Get floor height and chair rail height for this story
                floor_height = floor_heights[story_idx]
                chair_rail_height_z = calculated_chair_rail_heights[story_idx] if story_idx < len(calculated_chair_rail_heights) else floor_height + 30.0
                
                # Frame depth
                frame_depth = 4
                
                # Calculate window center coordinates based on face
                if window.wall == "front":
                    window_center_x = window.position
                    window_center_y = frame_depth / 2
                elif window.wall == "rear":
                    window_center_x = window.position
                    window_center_y = -dimensions.right + frame_depth / 2
                elif window.wall == "left":
                    window_center_x = frame_depth / 2
                    window_center_y = -window.position
                elif window.wall == "right":
                    window_center_x = dimensions.front + frame_depth / 2
                    window_center_y = -window.position
                else:
                    continue
                
                # Create window frame
                frame_assembly = WindowsBuilder._window_frame(
                    window,
                    window_center_x,
                    window_center_y,
                    chair_rail_height_z,
                    window.wall
                )
                
                # Add all frame components to the windows assembly
                for name, obj_data in frame_assembly.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        component_name = f"window_{window.wall}_story{story_idx}_pos{window.position}_{name}"
                        windows_assembly.add(
                            obj_data.obj,
                            name=component_name,
                            color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.8, 0.7, 0.6)
                        )
        else:
            # Use automatic bay placement, but skip door openings
            # Iterate through each story (skip attic/dormers for now)
            for story_idx, window in enumerate(windows):
                if story_idx >= len(floor_heights):
                    break  # Skip if we don't have floor height for this story
                if story_idx >= stories:
                    break  # Skip attic/dormer windows (handle separately in future)
                
                # Get floor height and chair rail height for this story
                floor_height = floor_heights[story_idx]
                chair_rail_height_z = calculated_chair_rail_heights[story_idx] if story_idx < len(calculated_chair_rail_heights) else floor_height + 30.0
                
                # Frame depth
                frame_depth = 4
                
                # Get bays for each face
                for face in ["front", "rear", "left", "right"]:
                    bays = getattr(floorplan.bays, face, []) if floorplan and floorplan.bays else []
                    
                    if not bays:
                        continue
                    
                    # Create window at each bay center, skipping door locations
                    for bay_idx, bay_position in enumerate(bays):
                        # Check if this bay has a door on this story
                        floor_number = story_idx + 1
                        if (face, bay_position, floor_number) in door_locations:
                            continue  # Skip this bay - it has a door
                        
                        # Calculate window center coordinates based on face
                        if face == "front":
                            window_center_x = bay_position
                            window_center_y = frame_depth / 2
                        elif face == "rear":
                            window_center_x = bay_position
                            window_center_y = -dimensions.right + frame_depth / 2
                        elif face == "left":
                            window_center_x = frame_depth / 2
                            window_center_y = -bay_position
                        elif face == "right":
                            window_center_x = dimensions.front + frame_depth / 2
                            window_center_y = -bay_position
                        else:
                            continue
                        
                        # Create window frame
                        frame_assembly = WindowsBuilder._window_frame(
                            window,
                            window_center_x,
                            window_center_y,
                            chair_rail_height_z,
                            face
                        )
                        
                        # Add all frame components to the windows assembly
                        for name, obj_data in frame_assembly.traverse():
                            if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                                component_name = f"window_{face}_story{story_idx}_bay{bay_position}_{name}"
                                windows_assembly.add(
                                    obj_data.obj,
                                    name=component_name,
                                    color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.8, 0.7, 0.6)
                                )
        
        return windows_assembly if windows_assembly.children else None
