"""
Sheathing builder service using CadQuery.
Creates individual sheathing boards positioned on the exterior of studs.
"""
import cadquery as cq
import math
from typing import List, Optional
from app.models.building import Sheathing
from app.models.floorplan import Dimensions, Floorplan
from app.services.framing_builder import FramingBuilder


class SheathingBuilder:
    """Builds exterior sheathing boards using CadQuery."""
    
    @staticmethod
    def _bevel_weatherboard(top_width: float, bottom_width: float, height: float, length: float) -> cq.Workplane:
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
        profile = cq.Workplane("XY").polyline(profile_points).close().extrude(length)
        
        return profile
    
    @staticmethod
    def _beaded_weatherboard(top_width: float, bottom_width: float, height: float, length: float) -> cq.Workplane:
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
        profile = cq.Workplane("XY").polyline(profile_points).close().extrude(length)
        
        return profile
    
    @staticmethod
    def build(
        sheathing: Sheathing,
        dimensions: Dimensions,
        stories: int,
        ceiling_heights: Optional[List[float]] = None,
        joist_heights: Optional[List[float]] = None,
        floorplan: Optional[Floorplan] = None
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
        chair_rail_height = 30

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
        bevel_angle_degrees = 4
        
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
        vertical_boards = math.ceil(vertical_coverage / board_exposure)
        
        # Create sheathing boards for each face
        for face in ["front"]:

            if face == "front":
                wall_length = dimensions.front
                bays = floorplan.bays.front if floorplan and floorplan.bays else []
                board_x = wall_length / 2
                board_y = 0
            elif face == "rear":
                wall_length = dimensions.rear
                bays = floorplan.bays.rear if floorplan and floorplan.bays else []
                board_x = wall_length / 2
                board_y = -dimensions.right
            elif face == "left":
                wall_length = dimensions.left
                bays = floorplan.bays.left if floorplan and floorplan.bays else []
                board_x = 0
                board_y = wall_length / 2
            elif face == "right":
                wall_length = dimensions.right
                bays = floorplan.bays.right if floorplan and floorplan.bays else []
                board_x = 0
                board_y = -wall_length / 2
            # Create individual sheathing boards lapping continuously from bottom to top
            for board_index in range(vertical_boards):
                
                # Calculate the board length
                board_top_height = (board_index * board_exposure) + board_exposure
                board_length = wall_length
                board_z = board_top_height - (board_height / 2)

                
                # Create 2D profile based on sheathing type
                # Profile functions create profiles in XZ plane: X = width, Z = height (negative)
                if sheathing.sheathing_type == "beveled-weatherboard":
                    board = SheathingBuilder._bevel_weatherboard(
                        top_width, bottom_width, board_height, board_length
                    )
                elif sheathing.sheathing_type == "beaded-weatherboard":
                    board = SheathingBuilder._beaded_weatherboard(
                        top_width, bottom_width, board_height, board_length
                    )
                else:
                    # Fallback to beveled if unknown type
                    board = SheathingBuilder._bevel_weatherboard(
                        top_width, bottom_width, board_height, board_length
                    )
                
                board = board.translate((board_x, board_y, board_z)).rotateAboutCenter((0,0,1), 90).rotateAboutCenter((0,1,0), bevel_angle_degrees)
                
                # Add board to assembly as individual component with color
                board_name = f"sheathing_{face}_board{board_index}"
                sheathing_assembly.add(board, name=board_name, color=cq.Color(0.9, 0.85, 0.75))  # Light sheathing
        
        return sheathing_assembly

