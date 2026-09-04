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
    bounds_for_workplane,
    collect_component_metadata,
    project_scene_to_assembly,
)
from app.services.window_config import load_window_config
from app.services.window_validation import validate_window_scene


class WindowsBuilder:
    """Builds window geometry using CadQuery."""

    @staticmethod
    def _window_config() -> Dict[str, Any]:
        return load_window_config()

    @staticmethod
    def _color(name: str) -> cq.Color:
        values = WindowsBuilder._window_config().get("colors", {}).get(name)
        if not values:
            values = WindowsBuilder._window_config()["colors"]["fallback"]
        return cq.Color(*values)
    
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
        profile_config = WindowsBuilder._window_config().get("profile", {})
        segments = profile_config["bead_segments"]
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
        config = WindowsBuilder._window_config()
        profile_config = config.get("profile", {})
        defaults = config.get("defaults", {})
        segments = profile_config["bead_segments"]
        increment = 180 / segments

        # Define the bead
        bead_diameter = bead_size
        bead_radius = bead_diameter / 2
        board_height = inside_height - bead_diameter
        board_width = width
        center_x = board_width - bead_radius
        center_y = -inside_height + bead_radius
        rain_stem = defaults["sill_rain_stem"]
        rain_slope = (inside_height - outside_height)
        siding_notch = defaults["sill_siding_notch"]
        wall_width = defaults["sill_wall_width"]
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
    def _ogee_profile(
        begin_x: float,
        begin_y: float,
        direction: int,
        thickness: float,
        glazing_rabbet: float,
    ) -> List[tuple[float, float]]:
        """Notebook-derived ogee profile points for sash members."""
        profile_points: List[tuple[float, float]] = []
        profile_config = WindowsBuilder._window_config().get("profile", {})
        segments = profile_config["segments"]
        increment = 90 / segments
        stem_width = profile_config["stem_width"]
        stem_height = profile_config["stem_height"]
        stile_rabbet = profile_config["stile_rabbet"]
        ogee_diameter = thickness - (stem_width + stile_rabbet + stem_height)
        ogee_radius = ogee_diameter / 2
        vertical_radius = glazing_rabbet / 2

        concave_center_x = -begin_x + stile_rabbet + stem_width + ogee_radius
        concave_center_y = begin_y
        for segment in range(1, segments):
            angle_degrees = 360 - (segment * increment) if direction == -1 else 180 + (segment * increment)
            angle_radians = math.radians(angle_degrees)
            profile_points.append(
                (
                    concave_center_x + (ogee_radius * math.cos(angle_radians)),
                    concave_center_y + (vertical_radius * math.sin(angle_radians)),
                )
            )

        convex_center_x = concave_center_x
        convex_center_y = concave_center_y - (2 * vertical_radius)
        for segment in range(1, segments):
            angle_degrees = 90 + (segment * increment) if direction == -1 else 90 - (segment * increment)
            angle_radians = math.radians(angle_degrees)
            profile_points.append(
                (
                    convex_center_x + (ogee_radius * math.cos(angle_radians)),
                    convex_center_y + (vertical_radius * math.sin(angle_radians)),
                )
            )

        return profile_points

    @staticmethod
    def _add_rail(
        rail_width: float,
        rail_length: float,
        thickness: float,
        glazing_rabbet: float,
    ) -> cq.Workplane:
        profile_config = WindowsBuilder._window_config().get("profile", {})
        stem_width = profile_config["stem_width"]
        stem_height = profile_config["stem_height"]
        stile_rabbet = profile_config["stile_rabbet"]
        vertical_radius = glazing_rabbet / 2

        profile_points = [
            (0, 0),
            (-thickness, 0),
            (-thickness, rail_width - glazing_rabbet),
            (-thickness + stile_rabbet, rail_width - glazing_rabbet),
            (-thickness + stile_rabbet, rail_width),
            (-thickness + stile_rabbet + stem_width, rail_width),
        ]
        profile_points += WindowsBuilder._ogee_profile(thickness, rail_width, 1, thickness, glazing_rabbet)
        profile_points.append((-stem_height, rail_width - (vertical_radius * 2)))
        profile_points.append((0, rail_width - (vertical_radius * 2)))

        return cq.Workplane("XZ").polyline(profile_points).close().extrude(rail_length)

    @staticmethod
    def _add_stile(
        stile_length: float,
        stile_width: float,
        thickness: float,
        glazing_rabbet: float,
    ) -> cq.Workplane:
        profile_config = WindowsBuilder._window_config().get("profile", {})
        stem_width = profile_config["stem_width"]
        stem_height = profile_config["stem_height"]
        stile_rabbet = profile_config["stile_rabbet"]
        vertical_radius = glazing_rabbet / 2

        profile_points = [
            (0, 0),
            (-thickness, 0),
            (-thickness, stile_width - glazing_rabbet),
            (-thickness + stile_rabbet, stile_width - glazing_rabbet),
            (-thickness + stile_rabbet, stile_width),
            (-thickness + stile_rabbet + stem_width, stile_width),
        ]
        profile_points += WindowsBuilder._ogee_profile(thickness, stile_width, 1, thickness, glazing_rabbet)
        profile_points.append((-stem_height, stile_width - (vertical_radius * 2)))
        profile_points.append((0, stile_width - (vertical_radius * 2)))

        return cq.Workplane("XZ").polyline(profile_points).close().extrude(stile_length)

    @staticmethod
    def _add_top_meeting_rail(
        rail_length: float,
        meeting_rail_width: float,
        meeting_rail_thickness: float,
    ) -> cq.Workplane:
        profile_config = WindowsBuilder._window_config().get("profile", {})
        stile_rabbet = profile_config["stile_rabbet"]
        stile_bevel = profile_config["stile_bevel"]
        bevel = profile_config["meeting_rail_bevel"]
        profile_points = [
            (0, meeting_rail_width),
            (0, bevel),
            (stile_rabbet, bevel),
            (stile_rabbet, 0),
            (meeting_rail_thickness - bevel, 0),
            (meeting_rail_thickness - bevel, meeting_rail_width - stile_bevel),
            (meeting_rail_thickness, meeting_rail_width - stile_rabbet),
            (meeting_rail_thickness, meeting_rail_width),
        ]
        return cq.Workplane("XZ").polyline(profile_points).close().extrude(rail_length)

    @staticmethod
    def _add_bottom_meeting_rail(
        rail_length: float,
        meeting_rail_width: float,
        meeting_rail_thickness: float,
        thickness: float,
        glazing_rabbet: float,
    ) -> cq.Workplane:
        profile_config = WindowsBuilder._window_config().get("profile", {})
        stem_width = profile_config["stem_width"]
        stem_height = profile_config["stem_height"]
        stile_rabbet = profile_config["stile_rabbet"]
        stile_bevel = profile_config["stile_bevel"]
        bevel = profile_config["meeting_rail_bevel"]
        ogee_begin_x = profile_config["bottom_meeting_rail_ogee_begin_x"]
        step_x = profile_config["bottom_meeting_rail_step_x"]
        step_width = profile_config["bottom_meeting_rail_step_width"]
        ogee_radius = (thickness - (stem_width + stile_rabbet + stem_height)) / 2

        profile_points = [(0, meeting_rail_width)]
        profile_points += WindowsBuilder._ogee_profile(ogee_begin_x, ogee_radius + stem_height, 1, thickness, glazing_rabbet)
        profile_points += [
            (step_x, 0),
            (step_x + stem_width, 0),
            (step_x + stem_width, bevel),
            (step_x + stem_width + step_width, bevel),
            (step_x + stem_width + step_width, 0),
            (meeting_rail_thickness - bevel, 0),
            (meeting_rail_thickness - bevel, meeting_rail_width - stile_bevel),
            (meeting_rail_thickness, meeting_rail_width - stile_rabbet),
            (meeting_rail_thickness, meeting_rail_width),
        ]
        return cq.Workplane("XZ").polyline(profile_points).close().extrude(rail_length)

    @staticmethod
    def _ogee_muntin(length: float, thickness: float, glazing_rabbet: float) -> cq.Workplane:
        config = WindowsBuilder._window_config().get("muntin_profile", {})
        start_x = config["start_x"]
        wing_drop = config["wing_drop"]
        bridge_width = config["bridge_width"]
        reverse_offset = config["reverse_offset"]
        reverse_begin_y = config["reverse_begin_y"]
        profile_points = [(start_x, -wing_drop), (start_x, 0)]
        profile_points += WindowsBuilder._ogee_profile(0, 0, 1, thickness, glazing_rabbet)
        ogee_x, ogee_y = profile_points[-1]
        profile_points += [
            (ogee_x + bridge_width, ogee_y),
            (ogee_x + bridge_width, ogee_y - wing_drop),
            (ogee_x, ogee_y - wing_drop),
        ]
        profile_points += WindowsBuilder._ogee_profile(0, reverse_begin_y, -1, thickness, glazing_rabbet)
        ogee_x, ogee_y = profile_points[-1]
        profile_points += [
            (ogee_x - reverse_offset, ogee_y),
            (ogee_x - reverse_offset, ogee_y + wing_drop),
            (0, ogee_y + wing_drop),
            (0, ogee_y + (2 * wing_drop)),
        ]
        return cq.Workplane("XZ").polyline(profile_points).close().extrude(length)
    
    @staticmethod
    def _window_metrics(window: Window) -> Dict[str, float]:
        config = WindowsBuilder._window_config()
        defaults = config["defaults"]
        joinery = config["joinery"]
        # Parse window size and configuration
        size_parts = window.size.split('x')
        light_width = float(size_parts[0])
        light_height = float(size_parts[1])

        configuration_parts = window.configuration.split("/")
        top_sash_lights = int(configuration_parts[0])
        bottom_sash_lights = int(configuration_parts[1])

        # Frame parameters - use values from Window model or defaults
        frame_depth = defaults["frame_depth"]
        frame_width = defaults["frame_width"]
        top_rail_width = defaults["top_rail_width"]
        bottom_rail_width = window.rail_width
        meeting_rail_width = window.meeting_rail_width
        meeting_rail_thickness = defaults["meeting_rail_thickness"]
        muntin_width = window.muntin_width
        
        # Sill parameters (fixed values - could be made configurable)
        sill_inside_height = defaults["sill_inside_height"]
        sill_outside_height = defaults["sill_outside_height"]
        sill_width = defaults["sill_width"]
        
        # Joint parameters (fixed values - standard joinery)
        bead_size = defaults["bead_size"]
        tenon_size = joinery["tenon_size"]
        tenon_type = joinery["tenon_type"]
        lap_thickness = joinery["lap_thickness"]
        lap_size = joinery["lap_size"]
        
        # Precalculate part lengths
        glazing_rabbet = defaults["glazing_rabbet"]
        columns = int(defaults["columns"])
        top_rows = top_sash_lights / columns
        bottom_rows = bottom_sash_lights / columns
        top_stile_length = (top_rows * (light_height - (glazing_rabbet * 2))) + top_rail_width + meeting_rail_width + ((top_rows - 1) * muntin_width)
        bottom_stile_length = (bottom_rows * (light_height - (glazing_rabbet * 2))) + bottom_rail_width + meeting_rail_width + ((bottom_rows - 1) * muntin_width)
        pulley_stile_length = top_stile_length + bottom_stile_length - meeting_rail_width
        
        if tenon_type == "blind":
            tenon_adjustment = -1
            tenon_length = frame_width + (tenon_adjustment / 2)
        else:
            tenon_adjustment = 0
            tenon_length = window.stile_width
        
        rail_length = (light_width * 3) + (window.stile_width * 2) + (muntin_width * 2) - (glazing_rabbet * 6) + tenon_adjustment
        net_rail_length = rail_length - (window.stile_width * 2)
        header_length = (frame_width * 2) + rail_length

        return {
            "light_width": light_width,
            "light_height": light_height,
            "top_sash_lights": top_sash_lights,
            "bottom_sash_lights": bottom_sash_lights,
            "columns": columns,
            "frame_depth": frame_depth,
            "frame_width": frame_width,
            "stile_width": window.stile_width,
            "top_rail_width": top_rail_width,
            "bottom_rail_width": bottom_rail_width,
            "meeting_rail_width": meeting_rail_width,
            "meeting_rail_thickness": meeting_rail_thickness,
            "muntin_width": muntin_width,
            "sill_inside_height": sill_inside_height,
            "sill_outside_height": sill_outside_height,
            "sill_width": sill_width,
            "bead_size": bead_size,
            "tenon_size": tenon_size,
            "tenon_type": tenon_type,
            "lap_thickness": lap_thickness,
            "lap_size": lap_size,
            "glass_thickness": defaults["glass_thickness"],
            "glazing_rabbet": glazing_rabbet,
            "top_stile_length": top_stile_length,
            "bottom_stile_length": bottom_stile_length,
            "pulley_stile_length": pulley_stile_length,
            "rail_length": rail_length,
            "net_rail_length": net_rail_length,
            "header_length": header_length,
            "opening_width": header_length,
            "opening_height": pulley_stile_length + frame_width,
        }

    @staticmethod
    def _notebook_frame(metrics: Dict[str, float]) -> cq.Assembly:
        """Frame construction ported from docs/Windows.ipynb."""
        center_x = 0.0
        center_y = 0.0
        center_z = 0.0
        frame_depth = metrics["frame_depth"]
        frame_width = metrics["frame_width"]
        sill_inside_height = metrics["sill_inside_height"]
        sill_outside_height = metrics["sill_outside_height"]
        sill_width = metrics["sill_width"]
        bead_size = metrics["bead_size"]
        tenon_size = metrics["tenon_size"]
        header_length = metrics["header_length"]
        pulley_stile_length = metrics["pulley_stile_length"]
        lap_thickness = metrics["lap_thickness"]
        lap_size = metrics["lap_size"]
        offsets = WindowsBuilder._window_config()["placement_offsets"]
        sash_color = WindowsBuilder._color("sash")

        frame = cq.Assembly()

        left_x = center_x - (header_length / 2)
        left_z = center_z + (pulley_stile_length / 2) - (frame_width / 2) + offsets["frame_stile_z_lift"]
        left_frame = (
            WindowsBuilder._beaded_board(frame_width, frame_depth, bead_size)
            .extrude(pulley_stile_length + offsets["frame_extra_stile_length"])
            .rotate((center_x, center_y, center_z), (1, 0, 0), 90)
            .translate((left_x, center_y, left_z))
        )
        left_frame = (
            left_frame.faces(">Z").workplane()
            .center(left_x + (frame_width / 2), center_y + tenon_size)
            .rect(tenon_size, tenon_size, forConstruction=True)
            .wires().toPending().extrude(frame_width)
            .faces("<Z").workplane()
            .rect(tenon_size, tenon_size, forConstruction=True)
            .wires().toPending().extrude(frame_width - 2)
        )
        frame.add(left_frame, name="left_frame", color=sash_color)

        right_x = center_x + (header_length / 2) - frame_width
        right_z = center_z + (pulley_stile_length / 2) - (frame_width / 2) + offsets["frame_stile_z_lift"]
        right_frame = (
            WindowsBuilder._beaded_board(frame_width, frame_depth, bead_size)
            .extrude(pulley_stile_length + offsets["frame_extra_stile_length"])
            .rotate((center_x, center_y, center_z), (1, 0, 0), 90)
            .translate((right_x, center_y, right_z))
        )
        right_frame = (
            right_frame.faces(">Z").workplane()
            .center(right_x + (frame_width / 2), center_y + tenon_size)
            .rect(tenon_size, tenon_size, forConstruction=True)
            .wires().toPending().extrude(frame_width)
            .faces("<Z").workplane()
            .rect(tenon_size, tenon_size, forConstruction=True)
            .wires().toPending().extrude(frame_width - 2)
        )
        frame.add(right_frame, name="right_frame", color=sash_color)

        top_z = center_z + ((pulley_stile_length + frame_width) / 2) + offsets["top_frame_z_lift"]
        top_x = center_x - (header_length / 2)
        top_frame = (
            WindowsBuilder._beaded_board(frame_depth, frame_width, bead_size)
            .extrude(header_length)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .translate((top_x, center_y, top_z))
        )
        top_frame = (
            top_frame.faces("<Z").workplane()
            .center(right_x + (frame_width / 2), center_y + tenon_size)
            .rect(tenon_size, tenon_size, forConstruction=True)
            .wires().toPending().cutBlind(frame_width)
            .faces("<Z").workplane()
            .center(left_x + (frame_width / 2), center_y + tenon_size)
            .rect(tenon_size, tenon_size, forConstruction=True)
            .wires().toPending().cutBlind(frame_width)
            .faces("<X").workplane()
            .center(offsets["top_frame_lap_center_x"], center_z + lap_size / 2 + offsets["top_frame_lap_center_z_extra"])
            .rect(lap_thickness, frame_depth, forConstruction=True)
            .wires().toPending().extrude(frame_depth)
            .faces(">X").workplane()
            .rect(lap_thickness, frame_depth, forConstruction=True)
            .wires().toPending().extrude(frame_depth)
        )
        frame.add(top_frame, name="top_frame", color=sash_color)

        bottom_x = center_x - (header_length / 2)
        bottom_z = center_z - ((pulley_stile_length + frame_width) / 2) - offsets["bottom_frame_z_drop"]
        bottom_frame = (
            WindowsBuilder._beaded_sill(sill_width, sill_inside_height, sill_outside_height, bead_size)
            .extrude(header_length)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .translate((bottom_x, center_y, bottom_z))
        )
        bottom_frame = (
            bottom_frame.faces("<Z").workplane()
            .center(right_x + (frame_width / 2), center_y + tenon_size)
            .rect(tenon_size, tenon_size, forConstruction=True)
            .wires().toPending().cutBlind(frame_width)
            .faces("<Z").workplane()
            .center(left_x + (frame_width / 2), center_y + tenon_size)
            .rect(tenon_size, tenon_size, forConstruction=True)
            .wires().toPending().cutBlind(frame_width)
            .faces("<X").workplane()
            .center(offsets["bottom_frame_lap_center_x"], center_z + lap_size / 2)
            .rect(lap_thickness, lap_size, forConstruction=True)
            .wires().toPending().extrude(frame_depth)
            .faces(">X").workplane()
            .rect(lap_thickness, lap_size, forConstruction=True)
            .wires().toPending().extrude(frame_depth)
        )
        frame.add(bottom_frame, name="bottom_frame_sill", color=sash_color)
        return frame

    @staticmethod
    def _add_glass_panes(
        sash: cq.Assembly,
        rows: int,
        metrics: Dict[str, float],
        z_start: float,
        y_center: float,
    ) -> None:
        """Add simple glass panes in sash-local coordinates."""
        cols = int(metrics["columns"])
        light_width = metrics["light_width"]
        light_height = metrics["light_height"]
        stile_width = metrics["stile_width"]
        rail_length = metrics["rail_length"]
        muntin_width = metrics["muntin_width"]
        glazing_rabbet = metrics["glazing_rabbet"]
        glass_thickness = metrics["glass_thickness"]
        glass_color = WindowsBuilder._color("glass")

        pane_width = light_width - (2 * glazing_rabbet)
        pane_height = light_height - (2 * glazing_rabbet)
        x_start = -(rail_length / 2) + stile_width + glazing_rabbet
        x_pitch = light_width + muntin_width - (2 * glazing_rabbet)
        z_pitch = light_height + muntin_width - (2 * glazing_rabbet)

        for row in range(rows):
            for col in range(cols):
                x_center = x_start + (col * x_pitch) + (pane_width / 2)
                z_center = z_start + (row * z_pitch) + (pane_height / 2)
                pane = (
                    cq.Workplane("XY")
                    .box(pane_width, glass_thickness, pane_height)
                    .translate((x_center, y_center, z_center))
                )
                sash.add(pane, name=f"glass_{row}_{col}", color=glass_color)

    @staticmethod
    def _notebook_top_sash(window: Window, metrics: Dict[str, float]) -> cq.Assembly:
        center_x = 0.0
        center_y = 0.0
        center_z = 0.0
        sash = cq.Assembly()
        sash_color = WindowsBuilder._color("sash")
        offsets = WindowsBuilder._window_config()["placement_offsets"]
        thickness = window.thickness
        rail_length = metrics["rail_length"]
        top_stile_length = metrics["top_stile_length"]
        top_rail_width = metrics["top_rail_width"]
        meeting_rail_width = metrics["meeting_rail_width"]
        meeting_rail_thickness = metrics["meeting_rail_thickness"]
        muntin_width = metrics["muntin_width"]
        light_width = metrics["light_width"]
        light_height = metrics["light_height"]
        glazing_rabbet = metrics["glazing_rabbet"]
        stile_width = window.stile_width
        top_sash_lights = int(metrics["top_sash_lights"])
        columns = int(metrics["columns"])

        stile_z = center_z + top_stile_length - thickness
        stile_y = center_y + (thickness / 2) + thickness + offsets["top_sash_y_extra"]
        left_x = center_x - (rail_length / 2)
        right_x = center_x + (rail_length / 2)

        left_stile = (
            WindowsBuilder._add_stile(top_stile_length, stile_width, thickness, glazing_rabbet)
            .rotate((center_x, center_y, center_z), (1, 0, 0), 90)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .translate((left_x, stile_y, stile_z))
        )
        sash.add(left_stile, name="left_stile", color=sash_color)

        right_stile = (
            WindowsBuilder._add_stile(top_stile_length, stile_width, thickness, glazing_rabbet)
            .rotate((center_x, center_y, center_z), (1, 0, 0), 270)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .translate((right_x, stile_y, stile_z - top_stile_length))
        )
        sash.add(right_stile, name="right_stile", color=sash_color)

        top_rail_x = center_x + (rail_length / 2)
        top_rail = (
            WindowsBuilder._add_rail(top_rail_width, rail_length, thickness, glazing_rabbet)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .rotate((center_x, center_y, center_z), (0, 1, 0), 180)
            .translate((top_rail_x, stile_y, stile_z))
        )
        sash.add(top_rail, name="top_rail", color=sash_color)

        meeting_rail_x = center_x + (rail_length / 2)
        meeting_rail = (
            WindowsBuilder._add_top_meeting_rail(rail_length, meeting_rail_width, meeting_rail_thickness)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .rotate((center_x, center_y, center_z), (0, 1, 0), 180)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 180)
            .translate((-meeting_rail_x, stile_y, -stile_z + top_stile_length - thickness))
        )
        sash.add(meeting_rail, name="meeting_rail", color=sash_color)

        muntin_light_overlap = offsets["muntin_light_overlap"]
        vertical_muntin_left_x = left_x + stile_width + light_width - muntin_light_overlap + (muntin_width / 2)
        vertical_muntin_right_x = right_x - stile_width - light_width + muntin_light_overlap
        for muntin_name, muntin_x in [
            ("left_vertical_muntin", vertical_muntin_left_x),
            ("right_vertical_muntin", vertical_muntin_right_x),
        ]:
            muntin = (
                WindowsBuilder._ogee_muntin(top_stile_length, thickness, glazing_rabbet)
                .rotate((center_x, center_y, center_z), (1, 0, 0), 90)
                .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
                .translate((muntin_x, stile_y - thickness, stile_z))
            )
            sash.add(muntin, name=muntin_name, color=sash_color)

        muntins = max((top_sash_lights // columns) - 1, 0)
        for muntin in range(1, muntins + 1):
            horizontal_muntin_z = stile_z - stile_width - (muntin * (light_height + offsets["top_horizontal_muntin_light_adjust"] - (muntin_width / 2)))
            horizontal_muntin = (
                WindowsBuilder._ogee_muntin(rail_length, thickness, glazing_rabbet)
                .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
                .translate((top_rail_x - rail_length, stile_y - thickness, horizontal_muntin_z))
            )
            sash.add(horizontal_muntin, name=f"horizontal_muntin_{muntin}", color=sash_color)

        WindowsBuilder._add_glass_panes(
            sash,
            rows=top_sash_lights // columns,
            metrics=metrics,
            z_start=glazing_rabbet,
            y_center=stile_y - (thickness / 2),
        )

        return sash

    @staticmethod
    def _notebook_bottom_sash(window: Window, metrics: Dict[str, float]) -> cq.Assembly:
        center_x = 0.0
        center_y = 0.0
        center_z = 0.0
        sash = cq.Assembly()
        sash_color = WindowsBuilder._color("sash")
        offsets = WindowsBuilder._window_config()["placement_offsets"]
        thickness = window.thickness
        rail_length = metrics["rail_length"]
        top_stile_length = metrics["top_stile_length"]
        bottom_stile_length = metrics["bottom_stile_length"]
        bottom_rail_width = metrics["bottom_rail_width"]
        meeting_rail_width = metrics["meeting_rail_width"]
        meeting_rail_thickness = metrics["meeting_rail_thickness"]
        muntin_width = metrics["muntin_width"]
        light_width = metrics["light_width"]
        light_height = metrics["light_height"]
        glazing_rabbet = metrics["glazing_rabbet"]
        stile_width = window.stile_width
        bottom_sash_lights = int(metrics["bottom_sash_lights"])
        columns = int(metrics["columns"])

        stile_z = center_z - bottom_stile_length + (thickness / 2) + top_stile_length - thickness
        stile_y = center_y + (thickness / 2) + offsets["bottom_sash_y_extra"]
        left_x = center_x - (rail_length / 2) + stile_width
        right_x = center_x + (rail_length / 2) - stile_width

        left_stile = (
            WindowsBuilder._add_stile(bottom_stile_length, stile_width, thickness, glazing_rabbet)
            .rotate((center_x, center_y, center_z), (1, 0, 0), 90)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .rotate((0, 0, 0), (0, 1, 0), 180)
            .translate((left_x, stile_y, stile_z - bottom_stile_length))
        )
        sash.add(left_stile, name="left_stile", color=sash_color)

        right_stile = (
            WindowsBuilder._add_stile(bottom_stile_length, stile_width, thickness, glazing_rabbet)
            .rotate((center_x, center_y, center_z), (1, 0, 0), 270)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .rotate((0, 0, 0), (0, 1, 0), 180)
            .translate((right_x, stile_y, stile_z))
        )
        sash.add(right_stile, name="right_stile", color=sash_color)

        bottom_rail_x = center_x - (rail_length / 2)
        bottom_rail = (
            WindowsBuilder._add_rail(bottom_rail_width, rail_length, thickness, glazing_rabbet)
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .rotate((center_x, center_y, center_z), (0, 1, 0), 180)
            .rotate((0, 0, 0), (0, 1, 0), 180)
            .translate((bottom_rail_x, stile_y, stile_z - bottom_stile_length))
        )
        sash.add(bottom_rail, name="bottom_rail", color=sash_color)

        meeting_rail_x = center_x + (rail_length / 2)
        meeting_rail = (
            WindowsBuilder._add_bottom_meeting_rail(
                rail_length,
                meeting_rail_width,
                meeting_rail_thickness,
                thickness,
                glazing_rabbet,
            )
            .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
            .rotate((center_x, center_y, center_z), (1, 0, 0), 180)
            .rotate((0, 0, 0), (0, 1, 0), 180)
            .rotate((0, 0, 0), (0, 0, 1), 180)
            .translate((-meeting_rail_x, -stile_y + offsets["bottom_meeting_rail_y_adjust"], stile_z))
        )
        sash.add(meeting_rail, name="meeting_rail", color=sash_color)

        muntin_light_overlap = offsets["muntin_light_overlap"]
        vertical_muntin_left_x = left_x + light_width - muntin_light_overlap + (muntin_width / 2)
        vertical_muntin_right_x = right_x - light_width + muntin_light_overlap
        for muntin_name, muntin_x in [
            ("left_vertical_muntin", vertical_muntin_left_x),
            ("right_vertical_muntin", vertical_muntin_right_x),
        ]:
            muntin = (
                WindowsBuilder._ogee_muntin(bottom_stile_length, thickness, glazing_rabbet)
                .rotate((center_x, center_y, center_z), (1, 0, 0), 90)
                .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
                .translate((muntin_x, stile_y - thickness, stile_z))
            )
            sash.add(muntin, name=muntin_name, color=sash_color)

        muntins = max((bottom_sash_lights // columns) - 1, 0)
        for muntin in range(1, muntins + 1):
            horizontal_muntin_z = stile_z - (muntin * (light_height - offsets["bottom_horizontal_muntin_light_adjust"] + (muntin_width / 2)))
            horizontal_muntin = (
                WindowsBuilder._ogee_muntin(rail_length, thickness, glazing_rabbet)
                .rotate((center_x, center_y, center_z), (0, 0, 1), 90)
                .translate((bottom_rail_x, stile_y - thickness, horizontal_muntin_z))
            )
            sash.add(horizontal_muntin, name=f"horizontal_muntin_{muntin}", color=sash_color)

        bottom_glass_start = stile_z - bottom_stile_length + bottom_rail_width + glazing_rabbet
        WindowsBuilder._add_glass_panes(
            sash,
            rows=bottom_sash_lights // columns,
            metrics=metrics,
            z_start=bottom_glass_start,
            y_center=stile_y - (thickness / 2),
        )

        return sash

    @staticmethod
    def _normalize_local_window(window: cq.Assembly) -> cq.Assembly:
        """Move notebook-centered geometry to the canonical local window origin."""
        aggregate = None
        for _, obj_data in window.traverse():
            if not hasattr(obj_data, 'obj') or obj_data.obj is None:
                continue
            bounds = bounds_for_workplane(obj_data.obj)
            if bounds is None:
                continue
            aggregate = bounds if aggregate is None else aggregate.union(bounds)

        if aggregate is None:
            return window

        offset = (-aggregate.min[0], -aggregate.min[1], -aggregate.min[2])
        normalized = cq.Assembly()
        for name, obj_data in window.traverse():
            if not hasattr(obj_data, 'obj') or obj_data.obj is None:
                continue
            normalized.add(
                obj_data.obj.translate(offset),
                name=name,
                color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.95, 0.96, 0.94, 1),
            )
        return normalized

    @staticmethod
    def _window_frame(window: Window) -> cq.Assembly:
        """
        Create a complete window in canonical local coordinates.

        Origin is the lower-left exterior corner of the opening. The returned
        assembly contains no wall/building placement assumptions.
        """
        metrics = WindowsBuilder._window_metrics(window)
        raw_window = cq.Assembly()

        for name, obj_data in WindowsBuilder._notebook_frame(metrics).traverse():
            if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                raw_window.add(obj_data.obj, name=name, color=obj_data.color)

        for name, obj_data in WindowsBuilder._notebook_top_sash(window, metrics).traverse():
            if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                raw_window.add(obj_data.obj, name=f"top_sash_{name}", color=obj_data.color)

        for name, obj_data in WindowsBuilder._notebook_bottom_sash(window, metrics).traverse():
            if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                raw_window.add(obj_data.obj, name=f"bottom_sash_{name}", color=obj_data.color)

        return WindowsBuilder._normalize_local_window(raw_window)

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
        component_records = []
        group_bounds: Dict[str, Any] = {}

        for name, obj_data in frame_assembly.traverse():
            if not hasattr(obj_data, 'obj') or obj_data.obj is None:
                continue
            bounds = bounds_for_workplane(obj_data.obj)
            if bounds is None:
                continue
            group_name = WindowsBuilder._scene_group_for_component(name)
            group_bounds[group_name] = bounds if group_name not in group_bounds else group_bounds[group_name].union(bounds)
            component_records.append(
                {
                    "name": name,
                    "obj": obj_data.obj,
                    "color": obj_data.color if hasattr(obj_data, 'color') else WindowsBuilder._color("fallback"),
                    "bounds": bounds,
                    "group_name": group_name,
                }
            )

        for group_name, bounds in group_bounds.items():
            groups[group_name].local_transform = Transform.translate(*bounds.min)
            groups[group_name].metadata["local_bounds_datum"] = bounds.as_dict()

        for record in component_records:
            name = record["name"]
            bounds = record["bounds"]
            group_name = record["group_name"]
            group_origin = group_bounds[group_name].min
            part_origin = bounds.min
            part_transform = Transform.translate(
                part_origin[0] - group_origin[0],
                part_origin[1] - group_origin[1],
                part_origin[2] - group_origin[2],
            )
            local_geometry = record["obj"].translate((-part_origin[0], -part_origin[1], -part_origin[2]))
            part_name = WindowsBuilder._scene_part_name(name)
            groups[group_name].add_child(
                SceneNode(
                    name=part_name,
                    node_type="part",
                    role=WindowsBuilder._scene_role_for_component(name),
                    local_transform=part_transform,
                    geometry=local_geometry,
                    color=record["color"],
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
