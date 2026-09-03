"""
Sheathing builder service using CadQuery.
Creates individual sheathing boards positioned on the exterior of studs.
"""
import cadquery as cq
import math
from typing import Dict, Any, List, Optional
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
        calculated_chair_rail_heights: List[float],
        calculated_bay_heights: List[float],
        calculated_bay_widths: List[float],
        floorplan: Optional[Floorplan] = None,
        openings: Optional[List[Dict[str, Any]]] = None
    ) -> cq.Assembly:
        """
        Build exterior sheathing boards positioned on the outside of studs.
        
        Creates individual sheathing boards based on exposure and height specifications,
        positioned on the exterior face of the wall studs. Boards lap continuously from
        the lowest floor height to the highest floor height. Skips openings for doors/windows.
        
        Args:
            sheathing: Sheathing specification (exposure, height, type)
            dimensions: Building dimensions
            stories: Number of stories
            floor_heights: Pre-calculated floor heights for each story
            calculated_chair_rail_heights: Pre-calculated chair rail heights for each story
            calculated_bay_heights: Pre-calculated bay heights for each story
            calculated_bay_widths: Pre-calculated bay widths for each story
            floorplan: Optional floorplan for bay information
            openings: Optional list of door/window openings to skip
        Returns:
            CadQuery Assembly with individual sheathing boards as separate components
        """
        
        openings = openings or []
        
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
        total_quantity = 0
        
        # Create sheathing boards for each face
        for face in ["front", "rear", "left", "right"]:

            current_board_height = lowest_floor_height
            bays = getattr(floorplan.bays, face, [])
            wall_length = getattr(dimensions, face)
            bay_count = len(bays)
            print(f"Bay count: {bay_count}")
            print(f"Bays: {bays}")
            board_lengths = []
            board_x_positions = []
            face_quantity = 0

            # Helper function to get story index based on current height
            def get_story_index(current_height: float) -> int:
                """Determine which story index to use based on current height.
                
                Returns the index into the calculated lists (0 = first story, etc.)
                The lists have one entry per story plus one for attic (stories+1 total).
                floor_heights[i] is the elevation of floor i.
                Story i spans from floor_heights[i] up to (but not including) floor_heights[i+1].
                The attic is above the top floor.
                """
                # Find which story interval the current height falls into
                for i in range(len(floor_heights) - 1):
                    if floor_heights[i] <= current_height < floor_heights[i + 1]:
                        return i
                # If at or above the top floor, use the last index (attic)
                # Ensure we don't go beyond the list bounds
                max_idx = len(calculated_chair_rail_heights) - 1
                return min(len(floor_heights) - 1, max_idx) if max_idx >= 0 else 0
            
            if bay_count == 0:
                horizontal_quantity = 1
                board_length = wall_length
                board_lengths.append(board_length)
                board_x_positions.append(wall_length / 2)
            else:
                # Use the first story's bay_width for initial board layout
                story_idx = 0
                bay_width = calculated_bay_widths[story_idx] if story_idx < len(calculated_bay_widths) else calculated_bay_widths[-1]
                
                horizontal_quantity = (bay_count + 1)
                print(f"Horizontal quantity: {horizontal_quantity}")

                for bay in range(1, horizontal_quantity + 1):
                    print(f"Bay: {bay}")
                    if bay == 1:
                        board_length = bays[0] - (bay_width / 2)
                        print(f"Board length: {board_length}")
                        board_x_position = 0 + (board_length / 2)
                        print(f"Board x position: {board_x_position}")
                        board_x_positions.append(board_x_position)
                        board_lengths.append(board_length)
                    elif bay == horizontal_quantity:
                        previous_bay = bays[bay - 2] + (bay_width / 2)
                        current_bay = wall_length
                        board_length = current_bay - previous_bay
                        print(f"Board length: {board_length}")
                        board_lengths.append(board_length)
                        board_x_position = previous_bay + (board_length / 2)
                        print(f"Board x position: {board_x_position}")
                        board_x_positions.append(board_x_position)
                    elif bay > 1 and bay < horizontal_quantity:
                        previous_bay = bays[bay - 2] + (bay_width / 2)
                        current_bay = bays[bay - 1] - (bay_width / 2)
                        board_length = current_bay - previous_bay
                        print(f"Board length: {board_length}")
                        board_lengths.append(board_length)
                        board_x_position = previous_bay + (board_length / 2)
                        print(f"Board x position: {board_x_position}")
                        board_x_positions.append(board_x_position)

            # Create individual sheathing boards lapping continuously from bottom to top
            for row in range(1, vertical_quantity + 1):

                print(f"Row: {row}")
                
                # Calculate the vertical position of the board
                current_board_height += board_exposure
                print(f"Current board height: {current_board_height}")
                
                # Determine which story we're in and get story-specific values
                story_idx = get_story_index(current_board_height)
                chair_rail_height = calculated_chair_rail_heights[story_idx] if story_idx < len(calculated_chair_rail_heights) else calculated_chair_rail_heights[-1]
                bay_height = calculated_bay_heights[story_idx] if story_idx < len(calculated_bay_heights) else calculated_bay_heights[-1]
                bay_width = calculated_bay_widths[story_idx] if story_idx < len(calculated_bay_widths) else calculated_bay_widths[-1]
                
                print(f"Story index: {story_idx}, Chair rail: {chair_rail_height}, Bay height: {bay_height}, Bay width: {bay_width}")
                
                # Calculate bottom edge Z position (top is at current_board_height)
                bottom_edge_z = current_board_height - board_height
                # Translate moves the geometric center, so calculate center position
                board_z = bottom_edge_z + (board_height / 2)
                
                # Check if this board row intersects with any openings on this face
                # Opening vertical range is approximately chair_rail to bay_height (simplified)
                board_intersects_opening = False
                board_intersects_door = False
                openings_at_bays = {}  # Map bay position to True if it has an opening in this row
                
                floor_number = story_idx + 1
                for opening in openings:
                    if opening.get('wall') == face and opening.get('floor') == floor_number:
                        # Check if this board's vertical range intersects the opening
                        # Doors start at floor, windows start at chair rail
                        opening_bottom = floor_heights[story_idx] if opening.get('type') == 'door' else chair_rail_height
                        opening_top = opening_bottom + opening.get('height', 80)
                        
                        if bottom_edge_z < opening_top and current_board_height > opening_bottom:
                            board_intersects_opening = True
                            if opening.get('type') == 'door':
                                board_intersects_door = True
                            openings_at_bays[opening.get('position')] = True

                # Determine if the board is a single board or multiple boards
                if len(board_lengths) == 1:
                    horizontal_quantity = 1
                    print("No windows in this row")
                elif not board_intersects_opening:
                    # No openings in this row, use single board
                    horizontal_quantity = 1
                    print("Single board - no opening intersection")
                elif board_intersects_door:
                    # Door opening - always use multiple boards to cut around it
                    horizontal_quantity = len(board_lengths)
                    print("Multiple boards in this row (door opening)")
                elif current_board_height < chair_rail_height:
                    horizontal_quantity = 1
                    print("Single board below window")
                elif current_board_height > bay_height:
                    horizontal_quantity = 1
                    print("Single board above window")
                else:
                    print("Multiple boards in this row")
                    horizontal_quantity = len(board_lengths)

                print(f"Horizontal quantity: {horizontal_quantity}")

                for col in range(1, horizontal_quantity + 1):

                    print(f"Col: {col}")
                    if horizontal_quantity == 1:
                        board_length = wall_length
                        board_x_position = wall_length / 2
                    else:
                        board_length = board_lengths[col - 1]
                        board_x_position = board_x_positions[col - 1]

                    print(f"Board length: {board_length}")
                    print(f"Board x position: {board_x_position}")
                    face_quantity += 1
                    total_quantity += 1

                    print(f"Face quantity: {face_quantity}")

                    if face == "front":
                        board_x = board_x_position
                        board_y = 0 + stud_depth
                    elif face == "rear":
                        board_x = board_x_position
                        board_y = -dimensions.right - stud_depth
                    elif face == "left":
                        board_x = 0 - (stud_depth / 2)
                        board_y = -board_x_position
                    elif face == "right":
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
                    board_name = f"sheathing_{face}_board{face_quantity}"
                    sheathing_assembly.add(board, name=board_name, color=cq.Color(0.9, 0.85, 0.75))  # Light sheathing
        
        return sheathing_assembly
    
    @staticmethod
    def build_gable_sheathing(
        sheathing: Sheathing,
        dimensions: Dimensions,
        stories: int,
        floor_heights: List[float],
        roof_pitch_degrees: float,
        roof_overhang: float
    ) -> cq.Assembly:
        """
        Build gable end sheathing for side-gable roofs.
        
        Creates sheathing boards on the gable ends (left and right walls) that extend
        from the wall top up the rake to the ridge.
        
        Args:
            sheathing: Sheathing specification (exposure, height, type)
            dimensions: Building dimensions
            stories: Number of stories
            floor_heights: Pre-calculated floor heights for each story
            roof_pitch_degrees: Roof pitch in degrees
            roof_overhang: Roof overhang in inches
            
        Returns:
            CadQuery Assembly with gable sheathing boards
        """
        gable_assembly = cq.Assembly()
        
        # Sheathing board specifications
        board_exposure = sheathing.sheathing_exposure
        board_height = sheathing.sheathing_height
        top_width = 0.375
        bottom_width = 0.625
        bevel_angle_degrees = 4
        
        # Stud dimensions
        stud_depth = 6
        
        # Calculate wall top and ridge height
        wall_top = floor_heights[stories]
        right_dimension = dimensions.right
        roof_pitch_radians = roof_pitch_degrees * (math.pi / 180)
        ridge_run = right_dimension / 2
        ridge_height = wall_top + (ridge_run * math.tan(roof_pitch_radians))
        
        # Vertical coverage on gable face
        gable_height = ridge_height - wall_top
        
        # For gable ends at x=0 (left) and x=front_dimension (right)
        for face in ["left", "right"]:
            face_quantity = 0
            
            # Determine X position with overhang
            if face == "left":
                face_x = -roof_overhang - (stud_depth / 2)
            else:  # right
                face_x = dimensions.front + roof_overhang + (stud_depth / 2)
            
            # Calculate number of horizontal courses of boards
            # We'll place boards horizontally, spanning the width at each height
            vertical_quantity = math.ceil(gable_height / board_exposure)
            
            for row in range(1, vertical_quantity + 1):
                # Height of this row's bottom edge
                row_bottom_z = wall_top + (row - 1) * board_exposure
                row_top_z = row_bottom_z + board_height
                
                # At this height, calculate the width of the gable (how far the roof extends)
                # The gable is a triangle, widest at the wall_top (full width) and narrowing to a point at ridge
                height_above_wall = (row_bottom_z + row_top_z) / 2 - wall_top
                
                if height_above_wall >= gable_height:
                    continue  # Above the ridge
                
                # Width at this height (symmetric triangle)
                # At wall_top: width = right_dimension + 2*roof_overhang (includes gable overhang on both ends)
                # At ridge: width = 0
                # The gable should be centered on the building depth (y = 0 to y = -right_dimension)
                full_width_at_base = right_dimension + (2 * roof_overhang)
                width_at_height = full_width_at_base * (1 - height_above_wall / gable_height)
                
                if width_at_height < board_exposure:
                    continue  # Too narrow for a board
                
                # Board spans centered on the gable center at y = -right_dimension/2
                board_length = width_at_height
                board_y_center = -right_dimension / 2
                
                face_quantity += 1
                
                # Create board
                if sheathing.sheathing_type == "beveled-weatherboard":
                    board = SheathingBuilder._bevel_weatherboard(
                        top_width, bottom_width, board_height, board_length
                    )
                elif sheathing.sheathing_type == "beaded-weatherboard":
                    board = SheathingBuilder._beaded_weatherboard(
                        top_width, bottom_width, board_height, board_length
                    )
                else:
                    board = SheathingBuilder._bevel_weatherboard(
                        top_width, bottom_width, board_height, board_length
                    )
                
                # Rotate and position the board
                if face == "left":
                    # Rotate to face outward (left wall)
                    board = board.rotateAboutCenter((1,0,0), 90).rotateAboutCenter((0,0,1), 180).rotateAboutCenter((0,1,0), bevel_angle_degrees)
                else:  # right
                    # Rotate to face outward (right wall)
                    board = board.rotateAboutCenter((1,0,0), 90).rotateAboutCenter((0,0,1), 0).rotateAboutCenter((0,1,0), -bevel_angle_degrees)
                
                # Position the board
                bbox = board.val().BoundingBox()
                current_bottom_z = bbox.zmin
                z_offset = row_bottom_z - current_bottom_z
                
                board = board.translate((face_x, board_y_center, z_offset))
                
                # Add to assembly
                board_name = f"gable_sheathing_{face}_board{face_quantity}"
                gable_assembly.add(board, name=board_name, color=cq.Color(0.9, 0.85, 0.75))
        
        return gable_assembly

