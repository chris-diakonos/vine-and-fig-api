"""
Sheathing builder service using CadQuery.
Creates individual sheathing boards positioned on the exterior of studs.
"""
import cadquery as cq
import math
from typing import List, Optional
from app.models.building import Sheathing
from app.models.floorplan import Dimensions
from app.services.framing_builder import FramingBuilder


class SheathingBuilder:
    """Builds exterior sheathing boards using CadQuery."""
    
    @staticmethod
    def _bevel_weatherboard(top_width: float, bottom_width: float, height: float) -> cq.Workplane:
        """
        Create a 2D beveled weatherboard profile.
        
        Args:
            top_width: Width at the top (exposed portion)
            bottom_width: Width at the bottom (overlap portion)
            height: Height of the board
            
        Returns:
            2D CadQuery Workplane profile
        """
        profile_points = []
        
        # Add initial points
        profile_points.append((0, 0))
        profile_points.append((top_width, 0))
        profile_points.append((bottom_width, -height))
        profile_points.append((0, -height))
        
        # Create the 2D profile
        profile = cq.Workplane("XZ").polyline(profile_points).close()
        
        return profile
    
    @staticmethod
    def _beaded_weatherboard(top_width: float, bottom_width: float, height: float) -> cq.Workplane:
        """
        Create a 2D beaded weatherboard profile.
        
        Args:
            top_width: Width at the top (exposed portion)
            bottom_width: Width at the bottom (overlap portion)
            height: Height of the board
            
        Returns:
            2D CadQuery Workplane profile
        """
        profile_points = []
        segments = 32
        increment = 180 / segments
        
        # Add initial points
        profile_points.append((0, 0))
        profile_points.append((top_width, 0))
        
        # Define the bead
        bead_diameter = bottom_width
        bead_radius = bead_diameter / 2
        bevel_height = height - bead_diameter
        bevel_width = bottom_width * 0.90
        center_x = bead_radius
        center_y = -height + bead_radius
        
        # Add the stopping point before the bead
        profile_points.append((bevel_width, -bevel_height))
        profile_points.append((center_x, -bevel_height))
        
        # Add the bead points from 90 to 270 degrees
        for segment in range(1, segments + 1):
            if segment <= (segments / 2):
                angle_degrees = 90 - (segment * increment)
            else:
                segment_counter = segment - (segments / 2)
                angle_degrees = 360 - (segment_counter * increment)
            
            angle_radians = math.radians(angle_degrees)
            
            bead_x = center_x + (bead_radius * math.cos(angle_radians))
            bead_y = center_y + (bead_radius * math.sin(angle_radians))
            
            profile_points.append((bead_x, bead_y))
        
        # Add the final point
        profile_points.append((0, -height))
        
        # Create the 2D profile
        profile = cq.Workplane("XZ").polyline(profile_points).close()
        
        return profile
    
    @staticmethod
    def build(
        sheathing: Sheathing,
        dimensions: Dimensions,
        stories: int,
        ceiling_heights: Optional[List[float]] = None,
        joist_heights: Optional[List[float]] = None
    ) -> cq.Assembly:
        """
        Build exterior sheathing boards positioned on the outside of studs.
        
        Creates individual sheathing boards based on exposure and height specifications,
        positioned on the exterior face of the wall studs. Boards lap continuously from
        the lowest floor height to the highest floor height.
        
        Args:
            sheathing: Sheathing specification (exposure, height, type)
            dimensions: Building dimensions
            stories: Number of stories
            ceiling_heights: Ceiling heights for each story
            joist_heights: Joist heights for each floor
            
        Returns:
            CadQuery Assembly with individual sheathing boards as separate components
        """
        # Use defaults if not specified
        if ceiling_heights is None:
            ceiling_heights = [120] * stories  # 10 feet default
        if joist_heights is None:
            joist_heights = [10] * (stories + 1)  # Include foundation floor
        
        # Calculate floor heights using the same method as FramingBuilder
        floor_heights = FramingBuilder.calculate_floor_heights(
            stories,
            joist_heights,
            ceiling_heights
        )
        
        # Determine the range: from lowest floor height to highest floor height
        lowest_floor_height = min(floor_heights)
        highest_floor_height = max(floor_heights)
        
        # Sheathing board specifications
        board_exposure = sheathing.sheathing_exposure  # Visible exposure in inches
        board_height = sheathing.sheathing_height  # Board height in inches
        board_thickness = 0  # Typical sheathing board thickness in inches
        
        # Profile dimensions (same for beveled and beaded weatherboard)
        top_width = 0.375  # Top width in inches
        bottom_width = 0.625  # Bottom width in inches
        
        # Calculate bevel angle for lapped siding
        # The bevel is the angle created by the difference between top and bottom width
        # bevel_angle = arctan((bottom_width - top_width) / board_height)
        bevel_angle_radians = math.atan((bottom_width - top_width) / board_height)
        bevel_angle_degrees = math.degrees(bevel_angle_radians)
        
        # Stud dimensions (from framing)
        stud_depth_front_rear = 0  # Front/rear studs: 3" wide x 4" deep
        stud_depth_left_right = 0 # Left/right studs: 4" wide x 3" deep
        
        # Calculate sheathing position offset from stud face
        # Sheathing sits on the exterior (outside) of studs
        front_rear_offset = 5
        left_right_offset = 5
        
        # Create assembly to hold individual boards
        sheathing_assembly = cq.Assembly()
        
        # Start from lowest floor height and lap boards up to highest floor height
        wall_bottom = lowest_floor_height
        wall_top = highest_floor_height
        
        # Calculate number of boards needed vertically (continuous lapping)
        vertical_coverage = wall_top - wall_bottom
        num_boards = math.ceil(vertical_coverage / board_exposure)
        
        # Create sheathing boards for each face
        for face in ["front"]:
            if face == "front":
                wall_length = dimensions.front
                base_y = front_rear_offset
                wall_center_x = wall_length / 2
                
            elif face == "rear":
                wall_length = dimensions.rear
                base_y = -dimensions.right - front_rear_offset
                wall_center_x = wall_length / 2
                
            elif face == "left":
                wall_length = dimensions.left
                base_x = -left_right_offset
                wall_center_y = -dimensions.right + (wall_length / 2)
                
            elif face == "right":
                wall_length = dimensions.right
                base_x = dimensions.front + left_right_offset
                wall_center_y = -dimensions.right + (wall_length / 2)
            
            # Create individual sheathing boards lapping continuously from bottom to top
            for board_index in range(num_boards):
                # Calculate vertical position (bottom of board)
                # Boards lap based on exposure (visible portion)
                board_bottom_z = wall_bottom + (board_index * board_exposure)
                board_top_z = board_bottom_z + board_height
                
                # Clamp to wall boundaries
                if board_bottom_z < wall_bottom:
                    board_bottom_z = wall_bottom
                if board_top_z > wall_top:
                    board_top_z = wall_top
                
                actual_board_height = board_top_z - board_bottom_z
                if actual_board_height <= 0:
                    continue
                
                # Board center Z position
                board_center_z = board_bottom_z + (actual_board_height / 2) + 2
                
                # Create 2D profile based on sheathing type
                # Profile functions create profiles in XZ plane: X = width, Z = height (negative)
                if sheathing.sheathing_type == "beveled-weatherboard":
                    base_profile = SheathingBuilder._bevel_weatherboard(
                        top_width, bottom_width, actual_board_height
                    )
                elif sheathing.sheathing_type == "beaded-weatherboard":
                    base_profile = SheathingBuilder._beaded_weatherboard(
                        top_width, bottom_width, actual_board_height
                    )
                else:
                    # Fallback to beveled if unknown type
                    base_profile = SheathingBuilder._bevel_weatherboard(
                        top_width, bottom_width, actual_board_height
                    )
                
                # Extrude profile along wall length to create board
                # Profile is in XZ plane: X = width, Z = height (negative), normal = Y
                # When extruded from XZ plane, extends in Y direction by default
                if face in ["front", "rear"]:
                    # Boards run horizontally along X axis (wall length)
                    # Profile width should be in Y direction (perpendicular to wall)
                    # Profile height is in Z direction (vertical)
                    # Rotate profile 90° around Z to put width in Y direction
                    # Then sweep along X axis path
                    if face == "front":
                        rotated_profile = base_profile.rotate((0, 0, 0), (0, 0, 1), -90)
                    else:
                        rotated_profile = base_profile.rotate((0, 0, 0), (0, 0, 1), 90)
                    # Create path along X axis
                    sweep_path = cq.Workplane("XY").moveTo(0, 0).lineTo(wall_length, 0)
                    board = (
                        rotated_profile
                        .sweep(sweep_path)
                        .translate((wall_center_x - wall_length / 2, base_y, board_center_z + 1))
                    )
                    # Rotate board around X axis to accommodate bevel angle
                    # This tilts the board so the beveled edge aligns properly when lapped
                    # For lapped siding, the bottom (wider) should tilt outward
                    # Front face: negative Y is outside, so rotate to tilt bottom outward
                    # Rear face: positive Y is outside, so rotate opposite direction
                    if face == "front":
                        # Rotate negative to tilt bottom toward negative Y (outward)
                        board = board.rotate((0,0,0), (1, 0, 0), -bevel_angle_degrees)
                    else:  # rear
                        # Rotate positive to tilt bottom toward positive Y (outward)
                        board = board.rotate((wall_center_x - wall_length / 2, base_y, board_center_z), (1, 0, 0), bevel_angle_degrees)
                else:  # left, right
                    # Boards run horizontally along Y axis (wall length)
                    # Profile width should be in X direction (perpendicular to wall)
                    # Profile height is in Z direction (vertical)
                    # Profile is in XZ plane, so width is already in X
                    # Extrude along Y (default direction for XZ workplane)

                    # Rotate profile 90° around Z to put width in X direction
                    if face == "left":
                        rotated_profile = base_profile.rotate((0, 0, 0), (0, 0, 1), 180)
                    else:
                        rotated_profile = base_profile

                    board = (
                        rotated_profile
                        .extrude(wall_length)  # Extrude along Y (wall length)
                        .translate((base_x, wall_center_y + wall_length / 2, board_center_z))
                    )
                    # Rotate board around Y axis to accommodate bevel angle
                    # This tilts the board so the beveled edge aligns properly when lapped
                    # For lapped siding, the bottom (wider) should tilt outward
                    # Left face: negative X is outside, so rotate to tilt bottom outward
                    # Right face: positive X is outside, so rotate opposite direction
                    if face == "left":
                        # Rotate negative to tilt bottom toward negative X (outward)
                        board = board.rotate((base_x, wall_center_y + wall_length / 2, board_center_z), (0, 1, 0), -bevel_angle_degrees)
                    else:  # right
                        # Rotate positive to tilt bottom toward positive X (outward)
                        board = board.rotate((base_x, wall_center_y + wall_length / 2, board_center_z), (0, 1, 0), bevel_angle_degrees)
                
                # Add board to assembly as individual component with color
                board_name = f"sheathing_{face}_board{board_index}"
                sheathing_assembly.add(board, name=board_name, color=cq.Color(0.9, 0.85, 0.75))  # Light sheathing
        
        return sheathing_assembly

