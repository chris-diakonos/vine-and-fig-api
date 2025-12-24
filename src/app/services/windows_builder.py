"""
Windows builder service using CadQuery.
"""
import cadquery as cq
import math
from typing import List, Optional
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
        
        # Frame center point for rotation
        frame_center = (center_x, center_y, center_z)
        
        # For now, create simplified frames without complex joinery to avoid geometry errors
        # Left window frame (left side of opening, not left wall)
        left_x = center_x - (header_length / 2)
        left_z = center_z + (pulley_stile_length / 2) - (frame_width / 2)
        left_frame = WindowsBuilder._beaded_board(frame_width, frame_depth, bead_size).extrude(pulley_stile_length + 2).rotate((0, 0, 0), (1, 0, 0), 90).translate((left_x, center_y, left_z))
        if face in ["left", "right"]:
            # Rotate 90 degrees around Z axis at the frame center to align with wall
            left_frame = left_frame.rotate(frame_center, (0, 0, 1), 90)
        window_frame.add(left_frame, name="left_frame", color=cq.Color(0.8, 0.7, 0.6))
        
        # Right window frame (right side of opening, not right wall)
        right_x = center_x + (header_length / 2) - frame_width
        right_z = center_z + (pulley_stile_length / 2) - (frame_width / 2)
        right_frame = WindowsBuilder._beaded_board(frame_width, frame_depth, bead_size).extrude(pulley_stile_length + 2).rotate((0, 0, 0), (1, 0, 0), 90).translate((right_x, center_y, right_z))
        if face in ["left", "right"]:
            right_frame = right_frame.rotate(frame_center, (0, 0, 1), 90)
        window_frame.add(right_frame, name="right_frame", color=cq.Color(0.8, 0.7, 0.6))
        
        # Top window frame
        top_z = center_z + ((pulley_stile_length + frame_width) / 2)
        top_x = center_x - (header_length / 2)
        top_frame = WindowsBuilder._beaded_board(frame_depth, frame_width, bead_size).extrude(header_length).rotate((0, 0, 0), (0, 0, 1), 90).translate((top_x, center_y, top_z))
        if face in ["left", "right"]:
            top_frame = top_frame.rotate(frame_center, (0, 0, 1), 90)
        window_frame.add(top_frame, name="top_frame", color=cq.Color(0.8, 0.7, 0.6))
        
        # Bottom window frame (sill)
        # The sill sits at the bottom of the opening
        # pulley_stile_length represents the full opening height
        bottom_x = center_x - (header_length / 2)
        # Position sill center at center_z - (pulley_stile_length / 2) so bottom aligns with opening bottom
        bottom_z = center_z - (pulley_stile_length / 2)
        bottom_frame = WindowsBuilder._beaded_sill(sill_width, sill_inside_height, sill_outside_height, bead_size).extrude(header_length).rotate((0, 0, 0), (0, 0, 1), 90).translate((bottom_x, center_y, bottom_z))
        if face in ["left", "right"]:
            bottom_frame = bottom_frame.rotate(frame_center, (0, 0, 1), 90)
        window_frame.add(bottom_frame, name="bottom_frame_sill", color=cq.Color(0.8, 0.7, 0.6))
        
        return window_frame
    
    @staticmethod
    def build(
        windows: List[Window],
        dimensions: Dimensions,
        stories: int,
        floor_heights: List[float],
        calculated_chair_rail_heights: List[float],
        floorplan: Optional[Floorplan] = None
    ) -> Optional[cq.Assembly]:
        """
        Build window frames at each bay on each story.
        
        Args:
            windows: List of window specifications (one per story + attic)
            dimensions: Building dimensions
            stories: Number of stories
            floor_heights: Pre-calculated floor heights for each story
            calculated_chair_rail_heights: Pre-calculated chair rail heights for each story
            floorplan: Optional floorplan for bay information
            
        Returns:
            CadQuery Assembly with window frames, or None if no windows
        """
        if not windows:
            return None
        
        windows_assembly = cq.Assembly()
        
        # Iterate through each story (and attic)
        for story_idx, window in enumerate(windows):
            if story_idx >= len(floor_heights):
                break  # Skip if we don't have floor height for this story
            
            # Get floor height and chair rail height for this story
            floor_height = floor_heights[story_idx]
            # calculated_chair_rail_heights already includes floor_height + chair_rail_height
            chair_rail_height_z = calculated_chair_rail_heights[story_idx] if story_idx < len(calculated_chair_rail_heights) else floor_height + 30.0
            
            # Parse window size to get dimensions
            size_parts = window.size.split('x')
            if len(size_parts) == 2:
                window_width = float(size_parts[0])
                window_height = float(size_parts[1])
            else:
                window_width, window_height = 24, 36  # Default size
            
            # chair_rail_height_z is where the bottom of the opening (sill) should be
            # We'll pass this to _window_frame which will calculate the center using the actual opening height
            
            # Get bays for each face
            for face in ["front", "rear", "left", "right"]:
                bays = getattr(floorplan.bays, face, []) if floorplan and floorplan.bays else []
                
                if not bays:
                    # No bays on this face, skip
                    continue
                
                wall_length = getattr(dimensions, face)
                
                # Frame depth - back of frame should be flush with inside of stud wall
                frame_depth = 4  # Frame depth in inches
                
                # Create window at each bay center
                for bay_idx, bay_position in enumerate(bays):
                    # Calculate window center coordinates based on face
                    # Frame back (interior side) should be flush with inside of stud wall
                    # Frame extends from inside (back) to outside (front) by frame_depth
                    if face == "front":
                        # Back of frame at Y=0 (inside of wall), center at Y=frame_depth/2
                        window_center_x = bay_position
                        window_center_y = frame_depth / 2
                    elif face == "rear":
                        # Back of frame at Y=-dimensions.right (inside of wall), center at Y=-dimensions.right + frame_depth/2
                        window_center_x = bay_position
                        window_center_y = -dimensions.right + frame_depth / 2
                    elif face == "left":
                        # Back of frame at X=0 (inside of wall), center at X=frame_depth/2
                        window_center_x = frame_depth / 2
                        window_center_y = -bay_position
                    elif face == "right":
                        # Back of frame at X=dimensions.front (inside of wall), center at X=dimensions.front + frame_depth/2
                        window_center_x = dimensions.front + frame_depth / 2
                        window_center_y = -bay_position
                    else:
                        continue
                    
                    # Create window frame
                    # Pass chair_rail_height_z so the bottom of the opening aligns with it
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
