"""
Sheathing builder service using CadQuery.
Creates individual sheathing boards positioned on the exterior of studs.
"""
import cadquery as cq
import math
from typing import Dict, Any, List, Optional
from app.models.building import Sheathing
from app.models.floorplan import Dimensions, Floorplan
from app.services.building_datums import BuildingDatumContext
from app.services.config_loader import load_json_config
from app.services.cornice_builder import CorniceBuilder
from app.services.scene_graph import collect_component_metadata, project_scene_to_assembly, scene_from_assembly
from app.services.sheathing_validation import validate_sheathing_scene


class SheathingBuilder:
    """Builds exterior sheathing boards using CadQuery."""

    @staticmethod
    def _config() -> Dict[str, Any]:
        return load_json_config("sheathing", "SHEATHING_CONFIG_PATH")

    @staticmethod
    def _color() -> cq.Color:
        return cq.Color(*SheathingBuilder._config()["colors"]["board"])
    
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
        profile_config = SheathingBuilder._config()["profile"]
        segments = profile_config["bead_segments"]
        increment = 180 / segments
        
        # Add initial points
        profile_points.append((0, 0))
        profile_points.append((top_width, 0))
        
        # Define the bead
        bead_diameter = bottom_width
        bead_radius = bead_diameter / 2
        bevel_height = height - bead_diameter
        bevel_width = bottom_width * profile_config["bead_bevel_width_ratio"]
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
        openings: Optional[List[Dict[str, Any]]] = None,
        datum_context: BuildingDatumContext = None,
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

        # Sheathing board specifications
        board_exposure = sheathing.sheathing_exposure  # Visible exposure in inches
        board_height = sheathing.sheathing_height  # Board height in inches
        
        # Profile dimensions (same for beveled and beaded weatherboard)
        profile_config = SheathingBuilder._config()["profile"]
        top_width = profile_config["top_width"]
        bottom_width = profile_config["bottom_width"]
        corner_board_width = SheathingBuilder._corner_board_width(sheathing.corner_treatment)
        
        # Calculate bevel angle for lapped siding
        # The bevel is the angle created by the difference between top and bottom width
        # bevel_angle = arctan((bottom_width - top_width) / board_height)
        bevel_angle_degrees = profile_config["bevel_angle_degrees"]
        
        # Stud dimensions (from framing)
        stud_depth = SheathingBuilder._config()["placement"]["stud_depth"]
        placement_source = "framing_datums" if datum_context else "legacy_dimensions"
        
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

                for bay in range(1, horizontal_quantity + 1):
                    if bay == 1:
                        board_length = bays[0] - (bay_width / 2)
                        board_x_position = 0 + (board_length / 2)
                        board_x_positions.append(board_x_position)
                        board_lengths.append(board_length)
                    elif bay == horizontal_quantity:
                        previous_bay = bays[bay - 2] + (bay_width / 2)
                        current_bay = wall_length
                        board_length = current_bay - previous_bay
                        board_lengths.append(board_length)
                        board_x_position = previous_bay + (board_length / 2)
                        board_x_positions.append(board_x_position)
                    elif bay > 1 and bay < horizontal_quantity:
                        previous_bay = bays[bay - 2] + (bay_width / 2)
                        current_bay = bays[bay - 1] - (bay_width / 2)
                        board_length = current_bay - previous_bay
                        board_lengths.append(board_length)
                        board_x_position = previous_bay + (board_length / 2)
                        board_x_positions.append(board_x_position)

            # Create individual sheathing boards lapping continuously from bottom to top
            for row in range(1, vertical_quantity + 1):

                
                # Calculate the vertical position of the board
                current_board_height += board_exposure
                
                # Determine which story we're in and get story-specific values
                story_idx = get_story_index(current_board_height)
                chair_rail_height = calculated_chair_rail_heights[story_idx] if story_idx < len(calculated_chair_rail_heights) else calculated_chair_rail_heights[-1]
                bay_height = calculated_bay_heights[story_idx] if story_idx < len(calculated_bay_heights) else calculated_bay_heights[-1]
                bay_width = calculated_bay_widths[story_idx] if story_idx < len(calculated_bay_widths) else calculated_bay_widths[-1]
                
                
                # Calculate bottom edge Z position (top is at current_board_height)
                bottom_edge_z = current_board_height - board_height
                # Translate moves the geometric center, so calculate center position
                board_z = bottom_edge_z + (board_height / 2)
                
                # Cut only the actual openings that intersect this course.
                floor_number = story_idx + 1
                opening_intervals = SheathingBuilder._opening_intervals_for_course(
                    openings,
                    face,
                    floor_number,
                    bottom_edge_z,
                    current_board_height,
                    floor_heights[story_idx],
                    chair_rail_height,
                    wall_length,
                )
                board_segments = SheathingBuilder._wall_segments_between_openings(wall_length, opening_intervals)
                board_segments = SheathingBuilder._clip_segments(board_segments, corner_board_width, wall_length - corner_board_width)

                for board_start, board_end in board_segments:
                    board_length = board_end - board_start
                    if board_length <= 0:
                        continue
                    board_x_position = board_start + (board_length / 2)

                    face_quantity += 1
                    total_quantity += 1


                    if face == "front":
                        board_x = board_x_position
                        board_y = datum_context.wall_exterior_plane(face, stud_depth) if datum_context else 0 + stud_depth
                    elif face == "rear":
                        board_x = board_x_position
                        board_y = datum_context.wall_exterior_plane(face, stud_depth) if datum_context else -dimensions.right - stud_depth
                    elif face == "left":
                        board_x = datum_context.wall_exterior_plane(face, stud_depth) if datum_context else 0 - (stud_depth / 2)
                        board_y = -board_x_position
                    elif face == "right":
                        board_x = datum_context.wall_exterior_plane(face, stud_depth) if datum_context else dimensions.front + (stud_depth / 2)
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
                    
                    # Get the bounding box after rotation to align real faces, not the pre-rotation origin.
                    bbox = board.val().BoundingBox()
                    x_offset, y_offset = SheathingBuilder._wall_board_offset(face, bbox, board_x, board_y)
                    z_offset = bottom_edge_z - bbox.zmin
                    
                    board = board.translate((x_offset, y_offset, z_offset))
                    
                    # Add board to assembly as individual component with color
                    board_name = f"sheathing_{face}_board{face_quantity}"
                    sheathing_assembly.add(board, name=board_name, color=SheathingBuilder._color())  # Light sheathing

        SheathingBuilder._add_corner_treatment(
            sheathing_assembly,
            sheathing.corner_treatment,
            dimensions,
            lowest_floor_height + board_exposure - board_height,
            lowest_floor_height + vertical_quantity * board_exposure,
            stud_depth,
            datum_context,
        )
        
        return SheathingBuilder._with_scene(sheathing_assembly, "sheathing", placement_source)

    @staticmethod
    def _opening_intervals_for_course(
        openings: List[Dict[str, Any]],
        face: str,
        floor_number: int,
        course_bottom_z: float,
        course_top_z: float,
        floor_height: float,
        chair_rail_height: float,
        wall_length: float,
    ) -> List[tuple[float, float]]:
        intervals = []
        for opening in openings:
            if opening.get("wall") != face or opening.get("floor") != floor_number:
                continue
            opening_type = opening.get("type")
            if opening_type == "door":
                opening_bottom = floor_height
            else:
                opening_bottom = chair_rail_height - float(opening.get("sill_height") or 0.0)
            opening_top = opening_bottom + float(opening.get("height", 0.0))
            if course_bottom_z >= opening_top or course_top_z <= opening_bottom:
                continue
            position = opening.get("position")
            width = opening.get("width")
            if position is None or width is None:
                continue
            half_width = float(width) / 2.0
            intervals.append((
                max(0.0, float(position) - half_width),
                min(wall_length, float(position) + half_width),
            ))
        return intervals

    @staticmethod
    def _wall_segments_between_openings(wall_length: float, opening_intervals: List[tuple[float, float]]) -> List[tuple[float, float]]:
        if not opening_intervals:
            return [(0.0, wall_length)]

        merged = []
        for start, end in sorted(opening_intervals):
            if end <= start:
                continue
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        segments = []
        cursor = 0.0
        for start, end in merged:
            if start > cursor:
                segments.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < wall_length:
            segments.append((cursor, wall_length))
        return segments

    @staticmethod
    def _clip_segments(segments: List[tuple[float, float]], min_station: float, max_station: float) -> List[tuple[float, float]]:
        if min_station <= 0.0 and max_station >= 0.0:
            return segments
        clipped = []
        for start, end in segments:
            clipped_start = max(start, min_station)
            clipped_end = min(end, max_station)
            if clipped_end > clipped_start:
                clipped.append((clipped_start, clipped_end))
        return clipped

    @staticmethod
    def _corner_board_width(corner_treatment: Optional[str]) -> float:
        if corner_treatment == "pilaster":
            return 7.25
        if corner_treatment in ("plain", "beaded"):
            return 3.5
        return 0.0

    @staticmethod
    def _add_corner_treatment(
        assembly: cq.Assembly,
        corner_treatment: Optional[str],
        dimensions: Dimensions,
        bottom_z: float,
        top_z: float,
        stud_depth: float,
        datum_context: BuildingDatumContext = None,
    ) -> None:
        if corner_treatment is None:
            return

        board_width = SheathingBuilder._corner_board_width(corner_treatment)
        if board_width <= 0.0:
            return

        board_thickness = 0.75
        height = max(0.0, top_z - bottom_z)
        if height <= 0.0:
            return

        planes = {
            "front": datum_context.wall_exterior_plane("front", stud_depth) if datum_context else stud_depth,
            "rear": datum_context.wall_exterior_plane("rear", stud_depth) if datum_context else -dimensions.right - stud_depth,
            "left": datum_context.wall_exterior_plane("left", stud_depth) if datum_context else -stud_depth / 2.0,
            "right": datum_context.wall_exterior_plane("right", stud_depth) if datum_context else dimensions.front + stud_depth / 2.0,
        }

        corners = {
            "front_left": {
                "front": (0.0, board_width, planes["front"], planes["front"] + board_thickness),
                "side": (planes["left"] - board_thickness, planes["left"], -board_width, 0.0),
                "bead": (0.0, planes["front"] + board_thickness / 2.0),
            },
            "front_right": {
                "front": (dimensions.front - board_width, dimensions.front, planes["front"], planes["front"] + board_thickness),
                "side": (planes["right"], planes["right"] + board_thickness, -board_width, 0.0),
                "bead": (dimensions.front, planes["front"] + board_thickness / 2.0),
            },
            "rear_left": {
                "front": (0.0, board_width, planes["rear"] - board_thickness, planes["rear"]),
                "side": (planes["left"] - board_thickness, planes["left"], -dimensions.left, -dimensions.left + board_width),
                "bead": (0.0, planes["rear"] - board_thickness / 2.0),
            },
            "rear_right": {
                "front": (dimensions.front - board_width, dimensions.front, planes["rear"] - board_thickness, planes["rear"]),
                "side": (planes["right"], planes["right"] + board_thickness, -dimensions.right, -dimensions.right + board_width),
                "bead": (dimensions.front, planes["rear"] - board_thickness / 2.0),
            },
        }

        for corner_name, corner in corners.items():
            front_x_min, front_x_max, front_y_min, front_y_max = corner["front"]
            side_x_min, side_x_max, side_y_min, side_y_max = corner["side"]
            SheathingBuilder._add_box(
                assembly,
                f"corner_board_{corner_name}_cross",
                front_x_min,
                front_x_max,
                front_y_min,
                front_y_max,
                bottom_z,
                top_z,
            )
            SheathingBuilder._add_box(
                assembly,
                f"corner_board_{corner_name}_side",
                side_x_min,
                side_x_max,
                side_y_min,
                side_y_max,
                bottom_z,
                top_z,
            )
            if corner_treatment == "beaded":
                bead_x, bead_y = corner["bead"]
                bead = cq.Workplane("XY").circle(0.1875).extrude(height).translate((bead_x, bead_y, bottom_z))
                assembly.add(bead, name=f"corner_bead_{corner_name}", color=SheathingBuilder._color())
            elif corner_treatment == "pilaster":
                SheathingBuilder._add_pilaster_capital(
                    assembly,
                    corner_name,
                    corner,
                    bottom_z,
                    top_z,
                )

    @staticmethod
    def _add_pilaster_capital(
        assembly: cq.Assembly,
        corner_name: str,
        corner: Dict[str, tuple[float, float, float, float] | tuple[float, float]],
        bottom_z: float,
        top_z: float,
    ) -> None:
        fillet_height = 0.75
        fillet_projection = 1.25
        bed_height = 1.5
        nose_drop = 5.5

        for side_name in ("front", "side"):
            x_min, x_max, y_min, y_max = corner[side_name]  # type: ignore[misc]
            center_x = (x_min + x_max) / 2.0
            center_y = (y_min + y_max) / 2.0
            width_x = x_max - x_min
            width_y = y_max - y_min
            if width_x >= width_y:
                x_min -= 0.5
                x_max += 0.5
                y_min -= fillet_projection / 2.0
                y_max += fillet_projection / 2.0
                length = x_max - x_min
                face = "front" if center_y >= 0.0 else "rear"
            else:
                y_min -= 0.5
                y_max += 0.5
                x_min -= fillet_projection / 2.0
                x_max += fillet_projection / 2.0
                length = y_max - y_min
                face = "right" if center_x >= 0.0 else "left"

            SheathingBuilder._add_box(
                assembly,
                f"pilaster_fillet_{corner_name}_{side_name}",
                x_min,
                x_max,
                y_min,
                y_max,
                top_z - fillet_height,
                top_z,
            )
            bed = CorniceBuilder._bed_molding(0.75, bed_height).extrude(length)
            bed = SheathingBuilder._place_profile_on_trim_face(bed, face, x_min, x_max, y_min, y_max, top_z - fillet_height)
            assembly.add(bed, name=f"pilaster_bedmold_{corner_name}_{side_name}", color=SheathingBuilder._color())

            nose = SheathingBuilder._nose_and_cove(length)
            nose = SheathingBuilder._place_profile_on_trim_face(nose, face, x_min, x_max, y_min, y_max, top_z - nose_drop)
            assembly.add(nose, name=f"pilaster_nose_and_cove_{corner_name}_{side_name}", color=SheathingBuilder._color())

    @staticmethod
    def _nose_and_cove(length: float) -> cq.Workplane:
        profile_points = []
        segments = 24

        nose_radius = 0.375 / 2.0
        cove_radius = 0.5
        back_size = 0.125
        nose_center_x = 1.0 - nose_radius
        nose_center_y = -nose_radius
        nose_increment = 180 / segments
        increment = 90 / segments

        profile_points.append((0, 0))
        profile_points.append((nose_center_x, 0))

        nose_x = nose_center_x
        nose_y = 0.0
        for segment in range(1, segments):
            angle_degrees = 90 - (segment * nose_increment)
            angle_radians = math.radians(angle_degrees)
            nose_x = nose_center_x + (nose_radius * math.cos(angle_radians))
            nose_y = nose_center_y + (nose_radius * math.sin(angle_radians))
            profile_points.append((nose_x, nose_y))

        profile_points.append((nose_x, nose_y - back_size))

        cove_center_x = nose_x + 0.000001
        cove_center_y = nose_y - back_size - cove_radius
        cove_y = cove_center_y
        for segment in range(segments):
            angle_degrees = 90 + (segment * increment)
            angle_radians = math.radians(angle_degrees)
            cove_x = cove_center_x + (cove_radius * math.cos(angle_radians))
            cove_y = cove_center_y + (cove_radius * math.sin(angle_radians))
            profile_points.append((cove_x, cove_y))

        profile_points.append((0, cove_y))
        return cq.Workplane("XZ").polyline(profile_points).close().extrude(length)

    @staticmethod
    def _place_profile_on_trim_face(
        profile: cq.Workplane,
        face: str,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        top_z: float,
    ) -> cq.Workplane:
        if face in ("front", "rear"):
            profile = profile.rotate((0, 0, 0), (0, 0, 1), -90)
        bbox = profile.val().BoundingBox()

        if face == "front":
            return profile.translate((x_min - bbox.xmin, y_min - bbox.ymin, top_z - bbox.zmax))
        if face == "rear":
            return profile.translate((x_min - bbox.xmin, y_max - bbox.ymax, top_z - bbox.zmax))
        if face == "left":
            return profile.translate((x_max - bbox.xmax, y_min - bbox.ymin, top_z - bbox.zmax))
        return profile.translate((x_min - bbox.xmin, y_min - bbox.ymin, top_z - bbox.zmax))

    @staticmethod
    def _add_box(
        assembly: cq.Assembly,
        name: str,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        z_min: float,
        z_max: float,
    ) -> None:
        box = (
            cq.Workplane("XY")
            .box(x_max - x_min, y_max - y_min, z_max - z_min)
            .translate(((x_min + x_max) / 2.0, (y_min + y_max) / 2.0, (z_min + z_max) / 2.0))
        )
        assembly.add(box, name=name, color=SheathingBuilder._color())

    @staticmethod
    def _wall_board_offset(face: str, bbox, target_x: float, target_y: float) -> tuple[float, float]:
        """Translate a rotated board so its inner face sits on the wall datum."""
        center_x = (bbox.xmin + bbox.xmax) / 2.0
        center_y = (bbox.ymin + bbox.ymax) / 2.0
        if face == "front":
            return target_x - center_x, target_y - bbox.ymin
        if face == "rear":
            return target_x - center_x, target_y - bbox.ymax
        if face == "left":
            return target_x - bbox.xmax, target_y - center_y
        if face == "right":
            return target_x - bbox.xmin, target_y - center_y
        return target_x - center_x, target_y - center_y
    
    @staticmethod
    def build_gable_sheathing(
        sheathing: Sheathing,
        dimensions: Dimensions,
        stories: int,
        floor_heights: List[float],
        roof_pitch_degrees: float,
        roof_overhang: float,
        datum_context: BuildingDatumContext = None,
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
        profile_config = SheathingBuilder._config()["profile"]
        top_width = profile_config["top_width"]
        bottom_width = profile_config["bottom_width"]
        bevel_angle_degrees = profile_config["bevel_angle_degrees"]
        
        # Stud dimensions
        stud_depth = SheathingBuilder._config()["placement"]["stud_depth"]
        
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
                face_x = datum_context.wall_exterior_plane(face, stud_depth) if datum_context else -roof_overhang - (stud_depth / 2)
            else:  # right
                face_x = datum_context.wall_exterior_plane(face, stud_depth) if datum_context else dimensions.front + roof_overhang + (stud_depth / 2)
            
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
                
                bbox = board.val().BoundingBox()
                x_offset, y_offset = SheathingBuilder._wall_board_offset(face, bbox, face_x, board_y_center)
                z_offset = row_bottom_z - bbox.zmin
                
                board = board.translate((x_offset, y_offset, z_offset))
                
                # Add to assembly
                board_name = f"gable_sheathing_{face}_board{face_quantity}"
                gable_assembly.add(board, name=board_name, color=SheathingBuilder._color())
        
        placement_source = "framing_datums" if datum_context else "legacy_dimensions"
        return SheathingBuilder._with_scene(gable_assembly, "gable_sheathing", placement_source)

    @staticmethod
    def _with_scene(assembly: cq.Assembly, subsystem_name: str, placement_source: str) -> cq.Assembly:
        scene_root = scene_from_assembly(
            assembly,
            subsystem_name=subsystem_name,
            subsystem_type="sheathing",
            subsystem_role=subsystem_name,
            group_name_for_component=SheathingBuilder._group_name_for_component,
            role_for_component=SheathingBuilder._role_for_component,
        )
        projected = cq.Assembly()
        subsystem = next((node for node in scene_root.iter_nodes() if node.name == subsystem_name), None)
        if subsystem is not None:
            subsystem.metadata["placement_source"] = placement_source
        project_scene_to_assembly(scene_root, projected)
        projected.scene_root = scene_root
        projected.scene_components = collect_component_metadata(scene_root)
        projected.validation_results = validate_sheathing_scene(scene_root)
        return projected

    @staticmethod
    def _group_name_for_component(component_name: str) -> str:
        parts = component_name.split("_")
        if component_name.startswith(("corner_board_", "corner_bead_", "pilaster_")):
            return "corner_trim"
        if component_name.startswith("gable_sheathing_") and len(parts) >= 3:
            return f"{parts[2]}_gable"
        if component_name.startswith("sheathing_") and len(parts) >= 2:
            return f"{parts[1]}_wall"
        return "sheathing"

    @staticmethod
    def _role_for_component(component_name: str) -> str:
        if component_name.startswith("corner_board_"):
            return "corner_board"
        if component_name.startswith("corner_bead_"):
            return "corner_bead"
        if component_name.startswith("pilaster_"):
            return "pilaster_molding"
        return "sheathing_board"

