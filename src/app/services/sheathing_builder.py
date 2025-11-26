"""
Sheathing builder service using CadQuery.
Creates individual sheathing boards positioned on the exterior of studs.
"""
import cadquery as cq
import math
from typing import List, Optional
from app.models.building import Sheathing
from app.models.floorplan import Dimensions


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
        ceiling_heights: Optional[List[float]] = None
    ) -> cq.Workplane:
        """
        Build exterior sheathing boards positioned on the outside of studs.
        
        Creates individual sheathing boards based on exposure and height specifications,
        positioned on the exterior face of the wall studs.
        
        Args:
            sheathing: Sheathing specification (exposure, height, type)
            dimensions: Building dimensions
            stories: Number of stories
            ceiling_heights: Ceiling heights for each story
            
        Returns:
            CadQuery Workplane with sheathing board geometry
        """
        # Use default ceiling heights if not specified
        if ceiling_heights is None:
            ceiling_heights = [120] * stories  # 10 feet default
        
        # Sheathing board specifications
        board_exposure = sheathing.sheathing_exposure  # Visible exposure in inches
        board_height = sheathing.sheathing_height  # Board height in inches
        board_thickness = 0.75  # Typical sheathing board thickness in inches
        
        # Profile dimensions (same for beveled and beaded weatherboard)
        top_width = 0.375  # Top width in inches
        bottom_width = 0.625  # Bottom width in inches
        
        # Stud dimensions (from framing)
        stud_depth_front_rear = 4  # Front/rear studs: 3" wide x 4" deep
        stud_depth_left_right = 3  # Left/right studs: 4" wide x 3" deep
        
        # Calculate sheathing position offset from stud face
        # Sheathing sits on the exterior (outside) of studs
        front_rear_offset = stud_depth_front_rear / 2 + board_thickness / 2
        left_right_offset = stud_depth_left_right / 2 + board_thickness / 2
        
        all_boards = None
        
        # Build sheathing for each story
        current_z = 0  # Start at foundation level (sills)
        
        for story in range(1, stories + 1):
            story_ceiling_height = ceiling_heights[story - 1] if story <= len(ceiling_heights) else ceiling_heights[-1]
            
            # Calculate previous ceiling height for this story
            previous_ceiling_height = 0
            if story > 1:
                for p in range(story - 1):
                    previous_ceiling_height += ceiling_heights[p]
            
            # Wall height for this story (from previous ceiling to current ceiling)
            wall_bottom = previous_ceiling_height
            wall_top = previous_ceiling_height + story_ceiling_height
            
            # Create sheathing boards for each face
            for face in ["front", "rear", "left", "right"]:
                if face == "front":
                    wall_length = dimensions.front
                    # Position on exterior: studs at y=0, sheathing at y = -offset (outside)
                    # Studs are 3" wide x 4" deep, so exterior face is at y = -2"
                    # Sheathing center should be at y = -2" - board_thickness/2
                    base_y = -(stud_depth_front_rear / 2) - (board_thickness / 2)
                    wall_center_x = wall_length / 2
                    
                elif face == "rear":
                    wall_length = dimensions.rear
                    # Position on exterior: studs at y=-right_dimension, sheathing at y = -right_dimension + offset
                    # Studs are 3" wide x 4" deep, so exterior face is at y = -right_dimension + 2"
                    # Sheathing center should be at y = -right_dimension + 2" + board_thickness/2
                    base_y = -dimensions.right + (stud_depth_front_rear / 2) + (board_thickness / 2)
                    wall_center_x = wall_length / 2
                    
                elif face == "left":
                    wall_length = dimensions.left
                    # Position on exterior: studs at x=0, sheathing at x = -offset (outside)
                    # Studs are 4" wide x 3" deep, so exterior face is at x = -1.5"
                    # Sheathing center should be at x = -1.5" - board_thickness/2
                    base_x = -(stud_depth_left_right / 2) - (board_thickness / 2)
                    wall_center_y = -dimensions.right + (wall_length / 2)
                    
                elif face == "right":
                    wall_length = dimensions.right
                    # Position on exterior: studs at x=front_dimension, sheathing at x = front_dimension + offset
                    # Studs are 4" wide x 3" deep, so exterior face is at x = front_dimension + 1.5"
                    # Sheathing center should be at x = front_dimension + 1.5" + board_thickness/2
                    base_x = dimensions.front + (stud_depth_left_right / 2) + (board_thickness / 2)
                    wall_center_y = -dimensions.right + (wall_length / 2)
                
                # Calculate number of boards needed vertically
                # Boards overlap based on exposure (visible portion)
                vertical_coverage = wall_top - wall_bottom
                num_boards = math.ceil(vertical_coverage / board_exposure)
                
                # Create individual sheathing boards
                for board_index in range(num_boards):
                    # Calculate vertical position (bottom of board)
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
                    board_center_z = board_bottom_z + (actual_board_height / 2)
                    
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
                        rotated_profile = base_profile.rotate((0, 0, 0), (0, 0, 1), 90)
                        # Create path along X axis
                        sweep_path = cq.Workplane("XY").moveTo(0, 0).lineTo(wall_length, 0)
                        board = (
                            rotated_profile
                            .sweep(sweep_path)
                            .translate((wall_center_x - wall_length / 2, base_y, board_center_z))
                        )
                    else:  # left, right
                        # Boards run horizontally along Y axis (wall length)
                        # Profile width should be in X direction (perpendicular to wall)
                        # Profile height is in Z direction (vertical)
                        # Profile is in XZ plane, so width is already in X
                        # Extrude along Y (default direction for XZ workplane)
                        board = (
                            base_profile
                            .extrude(wall_length)  # Extrude along Y (wall length)
                            .translate((base_x, wall_center_y - wall_length / 2, board_center_z))
                        )
                    
                    # Add board to collection
                    if all_boards is None:
                        all_boards = board
                    else:
                        all_boards = all_boards.union(board)
            
            # Move up for next story
            current_z += story_ceiling_height
        
        if all_boards is None:
            return cq.Workplane("XY")
        
        return all_boards

