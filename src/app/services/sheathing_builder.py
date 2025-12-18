"""
Sheathing builder service using CadQuery.
Creates individual sheathing boards positioned on the exterior of studs.
"""
import cadquery as cq
import math
from typing import List, Optional
from app.models.building import Sheathing
from app.models.floorplan import Dimensions, Floorplan


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
        floor_heights: List[float],
        floorplan: Optional[Floorplan] = None,
        bay_width: float = 0,
        bay_height: float = 0,
        chair_rail_height: float = 0
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
            floor_heights: Pre-calculated floor heights for each story
            floorplan: Optional floorplan for bay information
            bay_width: Width of the bay in inches
            bay_height: Height of the bay in inches
            chair_rail_height: Height of the chair rail in inches
        Returns:
            CadQuery Assembly with individual sheathing boards as separate components
        """
        
        # Determine the range: from lowest floor height to highest floor height
        lowest_floor_height = min(floor_heights)
        highest_floor_height = max(floor_heights)
        print(f"Lowest floor height: {lowest_floor_height}")
        print(f"Highest floor height: {highest_floor_height}")
        print(f"Floor heights: {floor_heights}")

        # Sheathing board specifications
        board_exposure = sheathing.sheathing_exposure  # Visible exposure in inches
        board_height = sheathing.sheathing_height  # Board height in inches
        
        # Profile dimensions (same for beveled and beaded weatherboard)
        top_width = 0.375  # Top width in inches
        bottom_width = 0.625  # Bottom width in inches
        
        # Calculate bevel angle for lapped siding
        # The bevel is the angle created by the difference between top and bottom width
        # bevel_angle = arctan((bottom_width - top_width) / board_height)
        bevel_angle_degrees = 4
        
        # Stud dimensions (from framing)
        stud_depth = 6
        
        # Create assembly to hold individual boards
        sheathing_assembly = cq.Assembly()
        
        # Calculate number of boards needed vertically (continuous lapping)
        vertical_coverage = highest_floor_height - lowest_floor_height
        vertical_quantity = math.ceil(vertical_coverage / board_exposure)
        
        # Create sheathing boards for each face
        for face in ["front", "rear", "left", "right"]:

            current_board_height = lowest_floor_height
            bays = getattr(floorplan.bays, face, [])
            bay_count = len(bays)
            print(f"Bay count: {bay_count}")
            print(f"Bays: {bays}")
            board_lengths = []
            board_x_positions = []

            if bay_count == 0:
                horizontal_quantity = 1
                board_length = wall_length
                board_lengths.append(board_length)
                board_x_positions.append(wall_length / 2)
            else:
                horizontal_quantity = (bay_count + 1)
                print(f"Horizontal quantity: {horizontal_quantity}")

                for bay in range(1, horizontal_quantity + 1):
                    print(f"Bay: {bay}")
                    if bay == 1:
                        board_length = bays[0] - (bay_width / 2)
                        print(f"Board length: {board_length}")
                        board_x_position = bays[bay - 1]
                        print(f"Board x position: {board_x_position}")
                        board_x_positions.append(board_x_position)
                    elif bay > 1:
                        previous_bay = board_x_positions[bay - 2] + (bay_width / 2)
                        current_bay = bays[bay - 1] - (bay_width / 2)
                        board_length = current_bay - previous_bay
                        print(f"Board length: {board_length}")
                        board_lengths.append(board_length)
                        board_x_position = bays[bay - 1]
                        print(f"Board x position: {board_x_position}")
                        board_x_positions.append(board_x_position)

            # Create individual sheathing boards lapping continuously from bottom to top
            for row in range(1, vertical_quantity + 1):
                
                # Calculate the vertical position of the board
                current_board_height += board_exposure
                # Calculate bottom edge Z position (top is at current_board_height)
                bottom_edge_z = current_board_height - board_height
                # Translate moves the geometric center, so calculate center position
                board_z = bottom_edge_z + (board_height / 2)

                # Determine if the board is a single board or a multiple board
                if len(board_lengths) == 1:
                    horizontal_quantity = 1
                elif current_board_height < chair_rail_height or current_board_height > bay_height:
                    horizontal_quantity = 1
                else:
                    horizontal_quantity = len(board_lengths)

                for col in range(1, horizontal_quantity + 1):

                    board_length = board_lengths[col - 1]
                    board_x_position = board_x_positions[col - 1]

                if face == "front":
                    wall_length = dimensions.front
                    board_x = board_x_position
                    board_y = 0 + stud_depth
                elif face == "rear":
                    wall_length = dimensions.rear
                    board_x = board_x_position
                    board_y = -dimensions.right - stud_depth
                elif face == "left":
                    wall_length = dimensions.left
                    board_x = 0 - (stud_depth / 2)
                    board_y = -board_x_position
                elif face == "right":
                    wall_length = dimensions.right
                    board_x = dimensions.front + (stud_depth / 2)
                    board_y = -board_x_position
                
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
                
                # Rotate the board first
                if face == "front":
                    board = board.rotateAboutCenter((1,0,0), 90).rotateAboutCenter((0,0,1), 90).rotateAboutCenter((1,0,0), bevel_angle_degrees)
                elif face == "rear":
                    board = board.rotateAboutCenter((1,0,0), 90).rotateAboutCenter((0,0,1), -90).rotateAboutCenter((1,0,0), -bevel_angle_degrees)
                elif face == "left":
                    board = board.rotateAboutCenter((1,0,0), 90).rotateAboutCenter((0,0,1), 180).rotateAboutCenter((0,1,0), bevel_angle_degrees)
                elif face == "right":
                    board = board.rotateAboutCenter((1,0,0), 90).rotateAboutCenter((0,0,1), 0).rotateAboutCenter((0,1,0), -bevel_angle_degrees)
                
                # Get the bounding box after rotation to find actual bottom position
                bbox = board.val().BoundingBox()
                current_bottom_z = bbox.zmin
                
                # Calculate offset needed to position bottom edge at bottom_edge_z
                # Translate by the difference to move bottom edge to desired position
                z_offset = bottom_edge_z - current_bottom_z
                
                # Translate to final position (X, Y from board_x/board_y, Z offset to position bottom edge)
                board = board.translate((board_x, board_y, z_offset))
                
                # Add board to assembly as individual component with color
                board_name = f"sheathing_{face}_board{q}"
                sheathing_assembly.add(board, name=board_name, color=cq.Color(0.9, 0.85, 0.75))  # Light sheathing
        
        return sheathing_assembly

