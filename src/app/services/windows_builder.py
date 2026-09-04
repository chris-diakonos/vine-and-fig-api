"""
Windows builder service using CadQuery.
"""
import cadquery as cq
import math
from typing import Dict, Any, List, Optional
from app.models.openings import Window
from app.models.floorplan import Dimensions, Floorplan
from app.services.coordinate_system import window_placement_for_wall
from app.services.scene_graph import (
    SceneNode,
    Transform,
    aggregate_local_bounds,
    collect_component_metadata,
    project_scene_to_assembly,
)
from app.services.window_validation import validate_window_scene


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
    def _create_sash_assembly(
        num_lights: int,
        light_width: float,
        light_height: float,
        stile_width: float,
        top_rail_width: float,
        bottom_rail_width: float,
        muntin_width: float,
        glazing_rabbet: float,
        sash_thickness: float = 1.375
    ) -> cq.Assembly:
        """
        Create a complete sash assembly with stiles, rails, muntins, and glazing.
        
        Args:
            num_lights: Total number of lights (e.g., 9 for 3x3, 6 for 2x3)
            light_width: Width of each light in inches
            light_height: Height of each light in inches
            stile_width: Width of sash stiles
            top_rail_width: Width of top rail
            bottom_rail_width: Width of bottom rail
            muntin_width: Width of muntins
            glazing_rabbet: Rabbet depth for glazing
            sash_thickness: Thickness of sash components
            
        Returns:
            CadQuery Assembly with sash, muntins, and glazing
        """
        sash_assembly = cq.Assembly()
        
        # Determine grid dimensions (num_lights = rows * cols, always 3 cols)
        cols = 3
        rows = num_lights // cols
        
        # Calculate sash dimensions
        # Sash width = 3 lights + 2 vertical muntins + 2 stiles
        sash_width = (cols * light_width) + ((cols - 1) * muntin_width) + (2 * stile_width) - (glazing_rabbet * 2 * cols)
        # Sash height = rows of lights + (rows-1) horizontal muntins + top and bottom rails
        sash_height = (rows * light_height) + ((rows - 1) * muntin_width) + top_rail_width + bottom_rail_width - (glazing_rabbet * 2 * rows)
        
        # Create stiles (left and right vertical pieces)
        stile_profile = cq.Workplane("XZ").rect(stile_width, sash_thickness).extrude(sash_height)
        
        # Left stile
        left_stile = stile_profile.translate((0, 0, 0))
        sash_assembly.add(left_stile, name="left_stile", color=cq.Color(0.8, 0.7, 0.6))
        
        # Right stile
        right_stile = stile_profile.translate((sash_width - stile_width, 0, 0))
        sash_assembly.add(right_stile, name="right_stile", color=cq.Color(0.8, 0.7, 0.6))
        
        # Create rails (top and bottom horizontal pieces)
        # Top rail
        top_rail = cq.Workplane("XZ").rect(sash_width, sash_thickness).extrude(top_rail_width)
        top_rail = top_rail.translate((0, 0, sash_height - top_rail_width))
        sash_assembly.add(top_rail, name="top_rail", color=cq.Color(0.8, 0.7, 0.6))
        
        # Bottom rail
        bottom_rail = cq.Workplane("XZ").rect(sash_width, sash_thickness).extrude(bottom_rail_width)
        bottom_rail = bottom_rail.translate((0, 0, 0))
        sash_assembly.add(bottom_rail, name="bottom_rail", color=cq.Color(0.8, 0.7, 0.6))
        
        # Create vertical muntins (between columns)
        muntin_profile_v = cq.Workplane("XZ").rect(muntin_width, sash_thickness).extrude(
            sash_height - top_rail_width - bottom_rail_width
        )
        for col in range(1, cols):
            muntin_x = stile_width + (col * light_width) + ((col - 1) * muntin_width) - (glazing_rabbet * 2 * col) + (muntin_width * (col - 1))
            muntin_v = muntin_profile_v.translate((muntin_x, 0, bottom_rail_width))
            sash_assembly.add(muntin_v, name=f"muntin_v_{col}", color=cq.Color(0.8, 0.7, 0.6))
        
        # Create horizontal muntins (between rows)
        muntin_profile_h = cq.Workplane("XZ").rect(
            sash_width - (2 * stile_width), sash_thickness
        ).extrude(muntin_width)
        for row in range(1, rows):
            muntin_z = bottom_rail_width + (row * light_height) + ((row - 1) * muntin_width) - (glazing_rabbet * 2 * row) + (muntin_width * (row - 1))
            muntin_h = muntin_profile_h.translate((stile_width, 0, muntin_z))
            sash_assembly.add(muntin_h, name=f"muntin_h_{row}", color=cq.Color(0.8, 0.7, 0.6))
        
        # Create glazing (glass panes)
        glass_thickness = 0.125
        # Each light is positioned within its grid cell
        for row in range(rows):
            for col in range(cols):
                # Calculate position for this light
                glass_x = stile_width + (col * (light_width + muntin_width)) - (glazing_rabbet * 2 * col) + (muntin_width * col) + glazing_rabbet
                glass_z = bottom_rail_width + (row * (light_height + muntin_width)) - (glazing_rabbet * 2 * row) + (muntin_width * row) + glazing_rabbet
                glass_width = light_width - (2 * glazing_rabbet)
                glass_height = light_height - (2 * glazing_rabbet)
                
                # Create glass pane (slightly recessed into the sash)
                glass_y = -sash_thickness / 2 + glass_thickness / 2
                glass_pane = cq.Workplane("XZ").rect(glass_width, glass_thickness).extrude(glass_height)
                glass_pane = glass_pane.translate((glass_x, glass_y, glass_z))
                sash_assembly.add(glass_pane, name=f"glass_{row}_{col}", color=cq.Color(0.7, 0.9, 1.0, 0.3))
        
        return sash_assembly
    
    @staticmethod
    def _window_metrics(window: Window) -> Dict[str, float]:
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

        return {
            "light_width": light_width,
            "light_height": light_height,
            "top_sash_lights": top_sash_lights,
            "bottom_sash_lights": bottom_sash_lights,
            "frame_depth": frame_depth,
            "frame_width": frame_width,
            "top_rail_width": top_rail_width,
            "bottom_rail_width": bottom_rail_width,
            "meeting_rail_width": meeting_rail_width,
            "muntin_width": muntin_width,
            "sill_inside_height": sill_inside_height,
            "sill_outside_height": sill_outside_height,
            "sill_width": sill_width,
            "bead_size": bead_size,
            "glazing_rabbet": glazing_rabbet,
            "top_stile_length": top_stile_length,
            "bottom_stile_length": bottom_stile_length,
            "pulley_stile_length": pulley_stile_length,
            "rail_length": rail_length,
            "header_length": header_length,
            "opening_width": header_length,
            "opening_height": pulley_stile_length + frame_width,
        }

    @staticmethod
    def _window_frame(window: Window) -> cq.Assembly:
        """
        Create a complete window in canonical local coordinates.

        Origin is the lower-left exterior corner of the opening. The returned
        assembly contains no wall/building placement assumptions.
        """
        metrics = WindowsBuilder._window_metrics(window)
        light_width = metrics["light_width"]
        light_height = metrics["light_height"]
        top_sash_lights = int(metrics["top_sash_lights"])
        bottom_sash_lights = int(metrics["bottom_sash_lights"])
        frame_depth = metrics["frame_depth"]
        frame_width = metrics["frame_width"]
        top_rail_width = metrics["top_rail_width"]
        bottom_rail_width = metrics["bottom_rail_width"]
        meeting_rail_width = metrics["meeting_rail_width"]
        muntin_width = metrics["muntin_width"]
        sill_inside_height = metrics["sill_inside_height"]
        sill_width = metrics["sill_width"]
        bead_size = metrics["bead_size"]
        glazing_rabbet = metrics["glazing_rabbet"]
        pulley_stile_length = metrics["pulley_stile_length"]
        rail_length = metrics["rail_length"]
        header_length = metrics["header_length"]
        bottom_stile_length = metrics["bottom_stile_length"]

        center_x = header_length / 2
        center_y = frame_depth / 2
        center_z = pulley_stile_length / 2

        # Create window frame assembly
        window_frame = cq.Assembly()

        stile_pos_left = 0
        stile_pos_right = header_length - frame_width
        header_sill_const = center_y
        header_sill_start = 0
        header_sill_length = header_length
        
        # Left stile (vertical jamb)
        stile_z = center_z + (pulley_stile_length / 2) - (frame_width / 2)
        left_frame = WindowsBuilder._beaded_board(frame_width, frame_depth, bead_size).extrude(pulley_stile_length + 2).rotate((0, 0, 0), (1, 0, 0), 90)
        left_frame = left_frame.translate((stile_pos_left, header_sill_const, stile_z))
        window_frame.add(left_frame, name="left_frame", color=cq.Color(0.8, 0.7, 0.6))
        
        # Right stile (vertical jamb)
        right_frame = WindowsBuilder._beaded_board(frame_width, frame_depth, bead_size).extrude(pulley_stile_length + 2).rotate((0, 0, 0), (1, 0, 0), 90)
        right_frame = right_frame.translate((stile_pos_right, header_sill_const, stile_z))
        window_frame.add(right_frame, name="right_frame", color=cq.Color(0.8, 0.7, 0.6))
        
        # Top header (horizontal piece)
        header_z = center_z + ((pulley_stile_length + frame_width) / 2)
        top_frame = WindowsBuilder._beaded_board(frame_depth, frame_width, bead_size).extrude(header_sill_length).rotate((0, 0, 0), (0, 0, 1), 90)
        top_frame = top_frame.translate((header_sill_start, header_sill_const, header_z))
        window_frame.add(top_frame, name="top_frame", color=cq.Color(0.8, 0.7, 0.6))
        
        # Bottom sill (horizontal piece)
        sill_z = center_z - (pulley_stile_length / 2)
        bottom_frame = WindowsBuilder._beaded_sill(sill_width, sill_inside_height, metrics["sill_outside_height"], bead_size).extrude(header_sill_length).rotate((0, 0, 0), (0, 0, 1), 90)
        bottom_frame = bottom_frame.translate((header_sill_start, header_sill_const, sill_z))
        window_frame.add(bottom_frame, name="bottom_frame_sill", color=cq.Color(0.8, 0.7, 0.6))
        
        # Create top and bottom sash assemblies with muntins and glazing
        sash_thickness = window.thickness
        
        # Top sash
        top_sash = WindowsBuilder._create_sash_assembly(
            num_lights=top_sash_lights,
            light_width=light_width,
            light_height=light_height,
            stile_width=window.stile_width,
            top_rail_width=top_rail_width,
            bottom_rail_width=meeting_rail_width,
            muntin_width=muntin_width,
            glazing_rabbet=glazing_rabbet,
            sash_thickness=sash_thickness
        )
        
        # Bottom sash
        bottom_sash = WindowsBuilder._create_sash_assembly(
            num_lights=bottom_sash_lights,
            light_width=light_width,
            light_height=light_height,
            stile_width=window.stile_width,
            top_rail_width=meeting_rail_width,
            bottom_rail_width=bottom_rail_width,
            muntin_width=muntin_width,
            glazing_rabbet=glazing_rabbet,
            sash_thickness=sash_thickness
        )
        
        # Position sashes inside the local frame opening.
        sash_y = center_y - (sash_thickness / 2)
        bottom_sash_x_start = frame_width
        top_sash_x_start = bottom_sash_x_start
        bottom_sash_z = sill_z + sill_inside_height
        top_sash_z = bottom_sash_z + bottom_stile_length - meeting_rail_width

        for name, obj_data in bottom_sash.traverse():
            if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                positioned_obj = obj_data.obj.rotate((0, 0, 0), (1, 0, 0), -90)
                positioned_obj = positioned_obj.translate((bottom_sash_x_start, sash_y, bottom_sash_z))
                window_frame.add(positioned_obj, name=f"bottom_sash_{name}", color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.8, 0.7, 0.6))

        for name, obj_data in top_sash.traverse():
            if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                positioned_obj = obj_data.obj.rotate((0, 0, 0), (1, 0, 0), -90)
                positioned_obj = positioned_obj.translate((top_sash_x_start, sash_y, top_sash_z))
                window_frame.add(positioned_obj, name=f"top_sash_{name}", color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.8, 0.7, 0.6))
        
        return window_frame

    @staticmethod
    def _window_scene(
        window: Window,
        semantic_name: str,
        component_prefix: str,
        placement: Transform,
        placement_metadata: Dict[str, Any],
    ) -> SceneNode:
        """Create a semantic window scene node from local window geometry."""
        metrics = WindowsBuilder._window_metrics(window)
        window_node = SceneNode(
            name=semantic_name,
            node_type="window",
            role="window",
            local_transform=placement,
            metadata={
                "metrics": metrics,
                "placement": placement_metadata,
                "coordinate_system": "window-local",
            },
        )

        groups = {
            "frame": window_node.add_child(SceneNode("frame", "assembly", "frame")),
            "upper_sash": window_node.add_child(SceneNode("upper_sash", "assembly", "upper_sash")),
            "lower_sash": window_node.add_child(SceneNode("lower_sash", "assembly", "lower_sash")),
        }

        frame_assembly = WindowsBuilder._window_frame(window)
        for name, obj_data in frame_assembly.traverse():
            if not hasattr(obj_data, 'obj') or obj_data.obj is None:
                continue
            group_name = WindowsBuilder._scene_group_for_component(name)
            part_name = WindowsBuilder._scene_part_name(name)
            groups[group_name].add_child(
                SceneNode(
                    name=part_name,
                    node_type="part",
                    role=WindowsBuilder._scene_role_for_component(name),
                    geometry=obj_data.obj,
                    color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.8, 0.7, 0.6),
                    metadata={"component_name": f"{component_prefix}_{name}"},
                )
            )

        local_bounds = aggregate_local_bounds(window_node)
        if local_bounds is not None:
            metrics["opening_width"] = local_bounds.size[0]
            metrics["opening_height"] = local_bounds.size[2]
            window_node.metadata["local_bounds_datum"] = local_bounds.as_dict()

        return window_node

    @staticmethod
    def _scene_group_for_component(name: str) -> str:
        if name.startswith("top_sash_"):
            return "upper_sash"
        if name.startswith("bottom_sash_"):
            return "lower_sash"
        return "frame"

    @staticmethod
    def _scene_part_name(name: str) -> str:
        if name.startswith("top_sash_"):
            return name.replace("top_sash_", "", 1)
        if name.startswith("bottom_sash_"):
            return name.replace("bottom_sash_", "", 1)
        return name

    @staticmethod
    def _scene_role_for_component(name: str) -> str:
        if "glass" in name:
            return "glass"
        if "muntin" in name:
            return "muntin"
        if "rail" in name:
            return "rail"
        if "stile" in name or "frame" in name:
            return "stile"
        if "sill" in name:
            return "sill"
        return "part"
    
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
        scene_root = SceneNode("building", "building", "building")
        windows_root = scene_root.add_child(SceneNode("windows", "assembly", "windows"))
        
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
                
                if window.wall not in ["front", "rear", "left", "right"]:
                    continue

                metrics = WindowsBuilder._window_metrics(window)
                wall_placement = window_placement_for_wall(
                    window.wall,
                    window.position,
                    chair_rail_height_z,
                    metrics["opening_width"],
                    dimensions,
                )
                semantic_name = f"{window.wall}_wall/story_{window.floor}/window_{window.position:g}"
                component_prefix = f"window_{window.wall}_story{story_idx}_pos{window.position}"
                windows_root.add_child(
                    WindowsBuilder._window_scene(
                        window,
                        semantic_name,
                        component_prefix,
                        wall_placement.legacy_transform,
                        wall_placement.as_dict(),
                    )
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
                        
                        metrics = WindowsBuilder._window_metrics(window)
                        wall_placement = window_placement_for_wall(
                            face,
                            bay_position,
                            chair_rail_height_z,
                            metrics["opening_width"],
                            dimensions,
                        )
                        semantic_name = f"{face}_wall/story_{floor_number}/window_{bay_position:g}"
                        component_prefix = f"window_{face}_story{story_idx}_bay{bay_position}"
                        windows_root.add_child(
                            WindowsBuilder._window_scene(
                                window,
                                semantic_name,
                                component_prefix,
                                wall_placement.legacy_transform,
                                wall_placement.as_dict(),
                            )
                        )

        if not windows_root.children:
            return None

        project_scene_to_assembly(scene_root, windows_assembly)
        windows_assembly.scene_root = scene_root
        windows_assembly.scene_components = collect_component_metadata(scene_root)
        windows_assembly.validation_results = validate_window_scene(scene_root)

        return windows_assembly if windows_assembly.children else None
