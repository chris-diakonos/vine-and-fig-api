"""
Framing builder service using CadQuery.
Integrates framing.py functionality into the API architecture.
"""
import cadquery as cq
import math
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict

from app.models.structure import Structure
from app.models.floorplan import Dimensions
from app.utils.materials_helper import (
    add_framing_materials,
    add_production_bom_quantities,
    add_sales_bom_quantities
)
from app.services.config_loader import load_json_config
from app.services.framing_datums import FramingMemberDatum, FramingPlacementDatums
from app.services.framing_validation import validate_framing_scene
from app.services.joinery.base import JointSpec, box_at
from app.services.joinery.compiler import compile_joinery as run_joinery_compiler
from app.services.joinery.framing_handlers import FRAMING_JOINERY_HANDLERS
from app.services.scene_graph import Bounds, SceneNode, Transform, bounds_for_workplane, collect_component_metadata, project_scene_to_assembly, scene_from_assembly


@dataclass(frozen=True)
class FramingMember:
    id: str
    node: SceneNode
    role: str
    face: Optional[str]
    index: Optional[int]
    local_bounds: Bounds
    world_bounds: Bounds


@dataclass(frozen=True)
class StudStation:
    station: float
    width: float
    role: str
    component_name: str


class FramingBuilder:
    """Builds framing geometry and tracks BOM data."""
    
    def __init__(self, structure: Structure, structure_hash: str, openings: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize framing builder.
        
        Args:
            structure: Building structure specification
            structure_hash: Structure hash identifier for BOM tracking
            openings: Optional list of door/window openings {wall, position, floor, type, height}
        """
        self.structure = structure
        self.structure_hash = structure_hash
        self.floorplan = structure.floorplan
        self.dimensions = structure.floorplan.dimensions
        self.building_height = structure.floorplan.dimensions.building_height
        self.roof = structure.roof
        self.openings = openings or []
        
        # Extract dimensions
        self.faces = {
            "front": self.dimensions.front,
            "rear": self.dimensions.rear,
            "left": self.dimensions.left,
            "right": self.dimensions.right
        }
        
        # Calculate centerlines from bays
        self.centerlines = self._calculate_centerlines()
        
        # Configuration
        self.framing_defaults = load_json_config("framing", "FRAMING_CONFIG_PATH")["defaults"]
        self.bay_spacing = self.framing_defaults["bay_spacing"]
        self.lap = self.framing_defaults["lap"]
        self.chair_rail_height = self.framing_defaults["chair_rail_height"]
        self.max_member_length = self.framing_defaults["max_member_length"]
        self.joist_spacing = self.floorplan.spacing.joist_spacing
        self.stud_spacing = self.floorplan.spacing.stud_spacing
        self.rafter_spacing = self.floorplan.spacing.rafter_spacing
        self.ceiling_heights = self.floorplan.ceiling_heights or [120, 108]
        self.joist_heights = self.floorplan.joist_heights or [10, 9, 8]
        self.roof_overhang = self.roof.roof_overhang if self.roof else self.framing_defaults["roof_overhang"]
        self.roof_pitch_degrees = self.roof.roof_pitch if self.roof else 40
        
        # Calculated heights (set by build method)
        self.calculated_ceiling_heights: Optional[List[float]] = None
        self.calculated_floor_heights: Optional[List[float]] = None
        
        # BOM tracking
        self.materials = []
        self.bom_components = defaultdict(set)
        self.bom_quantities = defaultdict(float)
        self.bom_levels = defaultdict(int)
        
        # Tracking for stud placement
        self.bay_studs = {}
        self.stud_centerlines = {}
        self.member_registry: Dict[str, FramingMember] = {}
    
    def _calculate_centerlines(self) -> Dict[str, List[float]]:
        """
        Calculate centerlines from bay configurations.
        
        Returns:
            Dictionary mapping face names to centerline positions
        """
        centerlines = {
            "front": [],
            "rear": [],
            "left": [],
            "right": []
        }
        
        if self.floorplan.bays:
            # Convert bay widths to centerline positions
            for face in ["front", "rear", "left", "right"]:
                bay_widths = getattr(self.floorplan.bays, face, [])
                if bay_widths:
                    for width in bay_widths:
                        centerlines[face].append(width)
                else:
                    # Default centerlines if not specified
                    if face in ["front", "rear"]:
                        centerlines[face] = [64, 160, 240, 330, 420]
                    else:
                        centerlines[face] = [64, 192]
        else:
            # Default centerlines
            centerlines["front"] = [64, 160, 240, 330, 420]
            centerlines["rear"] = [64, 160, 240, 330, 420]
            centerlines["right"] = [64, 192]
            centerlines["left"] = [64, 192]
        
        return centerlines


    def build(
        self,
        calculated_ceiling_heights: List[float],
        calculated_floor_heights: List[float],
        compile_joinery: Optional[bool] = None,
    ) -> Tuple[cq.Assembly, Dict[str, Any]]:
        """
        Build complete framing structure.
        
        Args:
            calculated_ceiling_heights: Pre-calculated ceiling heights for each story
            calculated_floor_heights: Pre-calculated floor heights for each story
            
        Returns:
            Tuple of (CadQuery Assembly, BOM data dictionary)
        """
        # Store calculated heights for use in internal methods
        self.calculated_ceiling_heights = calculated_ceiling_heights
        self.calculated_floor_heights = calculated_floor_heights
        if compile_joinery is None:
            compile_joinery = bool(load_json_config("framing", "FRAMING_CONFIG_PATH")["defaults"].get("compile_joinery", False))
        
        assembly = cq.Assembly()
        
        # Calculate offset to center framing on foundation
        # Foundation is centered at (0, 0) with overhang
        # Framing starts at front-left corner (0, 0)
        # Need to shift framing so its center aligns with foundation center (0, 0)
        front_dimension = self.faces["front"]
        right_dimension = self.faces["right"]
        
        # Building center in framing coordinate system:
        # X center: front_dimension / 2
        # Y center: -right_dimension / 2
        # Shift to move center to (0, 0):
        x_offset = 0 #-front_dimension / 2
        y_offset = 0 #right_dimension / 2
        
        migrated_scene = self._build_migrated_framing_scene(x_offset, y_offset)
        self._populate_legacy_assembly(
            assembly,
            x_offset,
            y_offset,
            include_sills_and_posts=False,
            include_joists=False,
            include_girts=False,
            include_studs=False,
        )
        
        # Prepare BOM data
        bom_data = {
            "materials": self.materials,
            "bom_components": self.bom_components,
            "bom_quantities": self.bom_quantities,
            "bom_levels": self.bom_levels
        }
        
        return self._with_scene(assembly, compile_joinery=compile_joinery, migrated_scene=migrated_scene), bom_data

    def build_legacy_reference(
        self,
        calculated_ceiling_heights: List[float],
        calculated_floor_heights: List[float],
        compile_joinery: bool = False,
    ) -> cq.Assembly:
        """Build the pre-migration world-coordinate framing scene for parity tests."""
        self.calculated_ceiling_heights = calculated_ceiling_heights
        self.calculated_floor_heights = calculated_floor_heights
        assembly = cq.Assembly()
        self._populate_legacy_assembly(
            assembly,
            0.0,
            0.0,
            include_sills_and_posts=True,
            include_joists=True,
            include_girts=True,
            include_studs=True,
        )
        return self._with_scene(assembly, compile_joinery=compile_joinery)

    def _populate_legacy_assembly(
        self,
        assembly: cq.Assembly,
        x_offset: float,
        y_offset: float,
        include_sills_and_posts: bool,
        include_joists: bool,
        include_girts: bool,
        include_studs: bool,
    ) -> None:
        """Populate legacy world-coordinate framing members."""
        if include_sills_and_posts:
            self._add_sills(assembly, x_offset, y_offset)
            self._add_posts(assembly, x_offset, y_offset)

        for story in range(1, self.floorplan.stories + 2):
            if include_joists:
                self._add_joists(assembly, story, -y_offset, x_offset)

            if story in range(1, self.floorplan.stories + 1):
                self._add_braces(assembly, story, x_offset, y_offset)
                if include_studs:
                    self._add_bays(assembly, story, x_offset, y_offset)
                    self._add_studs(assembly, story, x_offset, y_offset)

            if include_girts and story not in (1, self.floorplan.stories + 1):
                self._add_girts(assembly, story, x_offset, y_offset)

            if story == self.floorplan.stories:
                self._add_plates(assembly, story, x_offset, y_offset)

        self._add_false_plates(assembly, x_offset, y_offset)
        self._add_rafters(assembly, x_offset, y_offset)

        if self.roof and self.roof.roof_type == "side-gable":
            self._add_gable_framing(assembly, x_offset, y_offset)

    def _with_scene(
        self,
        assembly: cq.Assembly,
        compile_joinery: bool = False,
        migrated_scene: Optional[SceneNode] = None,
    ) -> cq.Assembly:
        scene_root = scene_from_assembly(
            assembly,
            subsystem_name="framing",
            subsystem_type="framing",
            subsystem_role="framing",
            group_name_for_component=self._group_name_for_component,
            role_for_component=lambda name: name.split("_")[0] if name else "framing_member",
        )
        if migrated_scene is not None:
            self._merge_migrated_framing_scene(scene_root, migrated_scene)
        self.member_registry = self._build_member_registry(scene_root)
        scene_root.metadata["framing_member_count"] = len(self.member_registry)
        scene_root.metadata["compile_joinery"] = compile_joinery
        if compile_joinery:
            specs = self._declare_joinery_specs()
            operations = run_joinery_compiler(scene_root, specs, FRAMING_JOINERY_HANDLERS)
            scene_root.metadata["joinery_operation_count"] = len(operations)
            scene_root.metadata["joinery_joint_count"] = len(specs)
        projected = cq.Assembly()
        project_scene_to_assembly(scene_root, projected)
        projected.scene_root = scene_root
        projected.scene_components = collect_component_metadata(scene_root)
        projected.validation_results = validate_framing_scene(scene_root)
        return projected

    def _build_migrated_framing_scene(self, x_offset: float = 0.0, y_offset: float = 0.0) -> SceneNode:
        """Build migrated framing members as cornerstone scene nodes."""
        sill_width = float(self.framing_defaults.get("sill_width", 8.0))
        sill_height = float(self.framing_defaults.get("sill_height", 10.0))
        post_width = float(self.framing_defaults.get("post_width", 6.0))
        post_depth = float(self.framing_defaults.get("post_depth", 4.0))
        post_tenon_depth = float(self.framing_defaults.get("post_tenon_depth", 2.0))
        girt_width = float(self.framing_defaults.get("girt_width", 4.0))
        girt_depth = float(self.framing_defaults.get("girt_depth", 6.0))
        bay_stud_width = float(self.framing_defaults.get("bay_stud_width", 5.0))
        bay_stud_depth = float(self.framing_defaults.get("bay_stud_depth", 4.0))
        stud_width = float(self.framing_defaults.get("stud_width", 3.0))
        stud_depth = float(self.framing_defaults.get("stud_depth", 4.0))
        cripple_stud_width = float(self.framing_defaults.get("cripple_stud_width", 3.0))
        cripple_stud_depth = float(self.framing_defaults.get("cripple_stud_depth", 4.0))
        stud_tenon_depth = float(self.framing_defaults.get("stud_tenon_depth", 2.0))
        stories = self.floorplan.stories
        post_height = self.calculated_ceiling_heights[stories - 1] - self.calculated_floor_heights[0]

        datums = FramingPlacementDatums(
            width=self.faces["front"],
            depth=self.faces["right"],
            sill_width=sill_width,
            sill_height=sill_height,
            post_width=post_width,
            post_depth=post_depth,
            post_tenon_depth=post_tenon_depth,
        )

        root = SceneNode("building", "building", "building")
        framing_node = root.add_child(
            SceneNode(
                "framing",
                "framing",
                "framing",
                metadata={
                    "coordinate_system": "cornerstone_legacy_y",
                    "migrated_member_roles": [
                        "sill",
                        "post",
                        "joist",
                        "girt",
                        "bay_stud",
                        "cripple_stud",
                        "stud",
                    ],
                },
            )
        )
        sills_node = framing_node.add_child(SceneNode("sills", "assembly", "sills"))
        posts_node = framing_node.add_child(SceneNode("posts", "assembly", "posts"))
        joists_node = framing_node.add_child(SceneNode("joists", "assembly", "joists"))
        girts_node = framing_node.add_child(SceneNode("girts", "assembly", "girts"))
        bay_studs_node = framing_node.add_child(SceneNode("bay_studs", "assembly", "bay_studs"))
        cripple_studs_node = framing_node.add_child(SceneNode("cripple_studs", "assembly", "cripple_studs"))
        studs_node = framing_node.add_child(SceneNode("studs", "assembly", "studs"))

        total_sills = 0
        for face in self.faces:
            quantity, sill_length = self._member_quantity_and_length(self.faces[face])
            for segment_index in range(quantity):
                datum = datums.sill(face, segment_index, sill_length)
                self._add_migrated_member(sills_node, self._offset_datum(datum, x_offset, y_offset))
                total_sills += 1

        for corner in ("front_left", "rear_left", "front_right", "rear_right"):
            datum = datums.post(corner, self.calculated_floor_heights[0], post_height)
            self._add_migrated_member(posts_node, self._offset_datum(datum, x_offset, y_offset))

        self._add_sill_bom(total_sills, sill_width, sill_height)
        self._add_post_bom(4, post_width, post_depth, post_height)
        self._add_migrated_joists(joists_node, datums, x_offset, y_offset)
        self._add_migrated_girts(girts_node, datums, x_offset, y_offset, girt_width, girt_depth)
        self._add_migrated_studs(
            bay_studs_node,
            cripple_studs_node,
            studs_node,
            datums,
            x_offset,
            y_offset,
            bay_stud_width,
            bay_stud_depth,
            stud_width,
            stud_depth,
            cripple_stud_width,
            cripple_stud_depth,
            stud_tenon_depth,
        )
        return root

    def _add_migrated_joists(
        self,
        joists_node: SceneNode,
        datums: FramingPlacementDatums,
        x_offset: float,
        y_offset: float,
    ) -> None:
        joist_width = float(self.framing_defaults.get("joist_width", 3.0))
        joist_centerlines = self._joist_centerlines()
        for story in range(1, self.floorplan.stories + 2):
            joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
            floor_height = self.calculated_floor_heights[story - 1]
            if story == len(self.joist_heights):
                joist_length = self.faces["right"] + (self.roof_overhang * 2.0)
                y_min = -self.faces["right"] - self.roof_overhang
            else:
                joist_length = self.faces["right"] - datums.sill_width
                y_min = -self.faces["right"] + datums.sill_width / 2.0

            for index, center_x in enumerate(joist_centerlines, start=1):
                datum = datums.joist(
                    story,
                    index,
                    center_x,
                    y_min,
                    joist_length,
                    joist_width,
                    joist_height,
                    floor_height,
                )
                self._add_migrated_member(joists_node, self._offset_datum(datum, x_offset, y_offset))
            self._add_joist_bom(len(joist_centerlines), joist_length, joist_width, joist_height)

    def _add_migrated_girts(
        self,
        girts_node: SceneNode,
        datums: FramingPlacementDatums,
        x_offset: float,
        y_offset: float,
        girt_width: float,
        girt_depth: float,
    ) -> None:
        bom_lengths: Dict[float, int] = defaultdict(int)
        splice_extension = self._girt_splice_extension()
        for story in range(1, self.floorplan.stories + 2):
            if story in (1, self.floorplan.stories + 1):
                continue
            floor_height = self.calculated_floor_heights[story - 1]
            joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
            for face in self.faces:
                quantity, girt_length = self._member_quantity_and_length(self.faces[face])
                for segment_index in range(quantity):
                    start_extension = splice_extension if segment_index > 0 else 0.0
                    end_extension = splice_extension if segment_index < quantity - 1 else 0.0
                    datum = datums.girt(
                        face,
                        story,
                        segment_index,
                        girt_length,
                        floor_height,
                        joist_height,
                        girt_width,
                        girt_depth,
                        start_extension=start_extension,
                        end_extension=end_extension,
                    )
                    self._add_migrated_member(girts_node, self._offset_datum(datum, x_offset, y_offset))
                    member_length = datum.size[0] if datum.axis == "x" else datum.size[1]
                    bom_lengths[member_length] += 1
        for member_length, quantity in bom_lengths.items():
            self._add_girt_bom(quantity, member_length, girt_width, girt_depth)

    @staticmethod
    def _girt_splice_extension() -> float:
        plate_splice = load_json_config("framing", "FRAMING_CONFIG_PATH").get("joinery", {}).get("plate_splice", {})
        return float(plate_splice.get("lap_length", 12.0)) / 2.0

    def _add_migrated_studs(
        self,
        bay_studs_node: SceneNode,
        cripple_studs_node: SceneNode,
        studs_node: SceneNode,
        datums: FramingPlacementDatums,
        x_offset: float,
        y_offset: float,
        bay_stud_width: float,
        bay_stud_depth: float,
        stud_width: float,
        stud_depth: float,
        cripple_stud_width: float,
        cripple_stud_depth: float,
        stud_tenon_depth: float,
    ) -> None:
        station_records: Dict[Tuple[str, int], List[StudStation]] = defaultdict(list)
        bom_counts: Dict[Tuple[str, float, float, float], int] = defaultdict(int)

        for story in range(1, self.floorplan.stories + 1):
            bottom_z, face_stud_length, side_stud_length = self._stud_story_verticals(story, stud_tenon_depth)
            for face in self.faces:
                centerlines = self.centerlines[face]
                stud_length = face_stud_length if face in ("front", "rear") else side_stud_length
                for index, centerline in enumerate(centerlines, start=1):
                    offset = (self.bay_spacing + bay_stud_width) / 2.0
                    for side, station in (("left", centerline - offset), ("right", centerline + offset)):
                        datum = datums.bay_stud(
                            face,
                            story,
                            index,
                            side,
                            station,
                            bottom_z,
                            stud_length,
                            bay_stud_width,
                            bay_stud_depth,
                        )
                        self._add_migrated_member(
                            bay_studs_node,
                            self._offset_datum(datum, x_offset, y_offset),
                        )
                        station_records[(face, story)].append(
                            StudStation(station, bay_stud_width, "bay_stud", datum.component_name)
                        )
                        bom_counts[("bay_stud", stud_length, bay_stud_width, bay_stud_depth)] += 1

                    if self._should_add_cripple(face, story, index, centerline):
                        datum = datums.cripple_stud(
                            face,
                            story,
                            index,
                            centerline,
                            self.calculated_floor_heights[story - 1],
                            self.chair_rail_height,
                            cripple_stud_width,
                            cripple_stud_depth,
                        )
                        self._add_migrated_member(
                            cripple_studs_node,
                            self._offset_datum(datum, x_offset, y_offset),
                        )
                        station_records[(face, story)].append(
                            StudStation(centerline, cripple_stud_width, "cripple_stud", datum.component_name)
                        )
                        bom_counts[(
                            "cripple_stud",
                            self.chair_rail_height,
                            cripple_stud_width,
                            cripple_stud_depth,
                        )] += 1

        self._add_migrated_regular_studs(
            studs_node,
            datums,
            x_offset,
            y_offset,
            station_records,
            stud_width,
            stud_depth,
            stud_tenon_depth,
            bom_counts,
        )
        for (member_type, length, width, depth), quantity in bom_counts.items():
            self._add_vertical_member_bom(member_type, quantity, length, width, depth)

    def _add_migrated_regular_studs(
        self,
        studs_node: SceneNode,
        datums: FramingPlacementDatums,
        x_offset: float,
        y_offset: float,
        station_records: Dict[Tuple[str, int], List[StudStation]],
        stud_width: float,
        stud_depth: float,
        stud_tenon_depth: float,
        bom_counts: Dict[Tuple[str, float, float, float], int],
    ) -> None:
        for story in range(1, self.floorplan.stories + 1):
            bottom_z, face_stud_length, side_stud_length = self._stud_story_verticals(story, stud_tenon_depth)
            for face in self.faces:
                stud_length = face_stud_length if face in ("front", "rear") else side_stud_length
                start, end = self._stud_run_boundaries(face)
                boundaries = [
                    StudStation(start, 0.0, "boundary", f"{face}_start"),
                    *station_records.get((face, story), []),
                    StudStation(end, 0.0, "boundary", f"{face}_end"),
                ]
                boundaries.sort(key=lambda station: station.station)
                max_interval = len(boundaries) - 2
                for interval_index, (previous, current) in enumerate(zip(boundaries, boundaries[1:])):
                    prior_edge = previous.station + previous.width / 2.0
                    current_edge = current.station - current.width / 2.0
                    wall_length = current_edge - prior_edge
                    wall_quantity = self._regular_stud_quantity(wall_length, interval_index, max_interval)
                    for wall in range(wall_quantity):
                        station = prior_edge + (wall_length / (wall_quantity + 1)) * (wall + 1)
                        datum = datums.stud(
                            face,
                            story,
                            interval_index,
                            wall + 1,
                            station,
                            bottom_z,
                            stud_length,
                            stud_width,
                            stud_depth,
                        )
                        self._add_migrated_member(studs_node, self._offset_datum(datum, x_offset, y_offset))
                        bom_counts[("stud", stud_length, stud_width, stud_depth)] += 1

    def _stud_story_verticals(self, story: int, stud_tenon_depth: float) -> Tuple[float, float, float]:
        floor_height = self.calculated_floor_heights[story - 1]
        ceiling_height = self.calculated_ceiling_heights[story - 1]
        next_floor_height = self.calculated_floor_heights[story]
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        bottom_z = floor_height - stud_tenon_depth
        if story != 1:
            bottom_z = floor_height - (joist_height + stud_tenon_depth)
        face_stud_length = (ceiling_height - floor_height) + (2.0 * stud_tenon_depth)
        side_stud_length = (next_floor_height - floor_height) + (2.0 * stud_tenon_depth) - 6.0
        return bottom_z, face_stud_length, side_stud_length

    def _stud_run_boundaries(self, face: str) -> Tuple[float, float]:
        if face in ("front", "rear"):
            post_clearance = float(self.framing_defaults.get("post_width", 6.0))
            return post_clearance, self.faces[face] - post_clearance
        post_clearance = float(self.framing_defaults.get("post_depth", 4.0))
        return post_clearance, self.faces[face] - post_clearance

    def _should_add_cripple(self, face: str, story: int, bay: int, station: float) -> bool:
        matching_openings = [
            opening
            for opening in self.openings
            if (
                opening.get("wall") == face
                and opening.get("position") == station
                and opening.get("floor") == story
            )
        ]
        if matching_openings:
            return not any(opening.get("type") == "door" for opening in matching_openings)
        if face in ("left", "right") and bay in (1, 2):
            return True
        return face in ("front", "rear")

    def _regular_stud_quantity(self, wall_length: float, interval_index: int, max_interval: int) -> int:
        if wall_length <= 0.0:
            return 0
        if wall_length / 4.0 >= 13.0:
            return 3
        if wall_length / 3.0 >= 13.0:
            return 2
        if wall_length / 2.0 > 16.0:
            return 1
        if wall_length / 2.0 <= 16.0 and interval_index == max_interval:
            return 1
        if wall_length % (2.0 * self.stud_spacing) >= 22.0:
            return math.ceil(wall_length / (2.0 * self.stud_spacing))
        return math.floor(wall_length / (2.0 * self.stud_spacing))

    def _add_migrated_member(self, parent: SceneNode, datum: FramingMemberDatum) -> None:
        parent.add_child(
            SceneNode(
                datum.component_name,
                "part",
                datum.role,
                local_transform=Transform.translate(*datum.min_corner),
                geometry=box_at(datum.size, (0.0, 0.0, 0.0)),
                blank_geometry=box_at(datum.size, (0.0, 0.0, 0.0)),
                color=cq.Color(0.55, 0.45, 0.33),
                metadata=datum.metadata(),
            )
        )

    @staticmethod
    def _offset_datum(datum: FramingMemberDatum, x_offset: float, y_offset: float) -> FramingMemberDatum:
        if x_offset == 0.0 and y_offset == 0.0:
            return datum
        min_corner = (
            datum.min_corner[0] + x_offset,
            datum.min_corner[1] + y_offset,
            datum.min_corner[2],
        )
        return FramingMemberDatum(
            component_name=datum.component_name,
            role=datum.role,
            size=datum.size,
            min_corner=min_corner,
            face=datum.face,
            index=datum.index,
            story=datum.story,
            corner=datum.corner,
            axis=datum.axis,
        )

    @staticmethod
    def _merge_migrated_framing_scene(scene_root: SceneNode, migrated_scene: SceneNode) -> None:
        target_framing = FramingBuilder._first_child_named(scene_root, "framing")
        source_framing = FramingBuilder._first_child_named(migrated_scene, "framing")
        if target_framing is None or source_framing is None:
            return
        target_framing.metadata.update(source_framing.metadata)
        for child in list(source_framing.children):
            target_framing.add_child(child)

    @staticmethod
    def _first_child_named(scene: SceneNode, name: str) -> Optional[SceneNode]:
        for child in scene.children:
            if child.name == name:
                return child
        return None

    def _member_quantity_and_length(self, dimension: float) -> Tuple[int, float]:
        if dimension <= self.max_member_length:
            return 1, dimension
        quantity = math.ceil(dimension / self.max_member_length)
        return quantity, dimension / quantity

    def _joist_centerlines(self) -> List[float]:
        centerlines: List[float] = []
        position = self.joist_spacing
        while position < self.faces["front"]:
            centerlines.append(position)
            position += self.joist_spacing
        return centerlines

    def _add_sill_bom(self, quantity: int, sill_width: float, sill_height: float) -> None:
        raw_material_id, component_id = add_framing_materials(
            "sill", sill_height / 12, sill_width, sill_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )

    def _add_post_bom(self, quantity: int, post_width: float, post_depth: float, post_height: float) -> None:
        raw_material_id, component_id = add_framing_materials(
            "post", post_width / 12, post_depth, post_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )

    def _add_joist_bom(self, quantity: int, joist_length: float, joist_width: float, joist_height: float) -> None:
        raw_material_id, component_id = add_framing_materials(
            "joist", joist_length / 12, joist_width, joist_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )

    def _add_girt_bom(self, quantity: int, girt_length: float, girt_width: float, girt_depth: float) -> None:
        raw_material_id, component_id = add_framing_materials(
            "girt", girt_length / 12, girt_width, girt_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )

    def _add_vertical_member_bom(
        self,
        member_type: str,
        quantity: int,
        length: float,
        width: float,
        depth: float,
    ) -> None:
        raw_material_id, component_id = add_framing_materials(
            member_type, length / 12, width, depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )

    def _build_member_registry(self, scene_root: SceneNode) -> Dict[str, FramingMember]:
        registry: Dict[str, FramingMember] = {}
        for node in scene_root.iter_nodes():
            member_id = node.metadata.get("component_name")
            if not member_id or node.geometry is None:
                continue
            local_bounds = bounds_for_workplane(node.geometry)
            world_bounds = bounds_for_workplane(node.projected_geometry())
            if local_bounds is None or world_bounds is None:
                continue
            registry[member_id] = FramingMember(
                id=member_id,
                node=node,
                role=node.role,
                face=self._face_for_component(member_id),
                index=self._index_for_component(member_id),
                local_bounds=local_bounds,
                world_bounds=world_bounds,
            )
        return registry

    def _declare_joinery_specs(self) -> List[JointSpec]:
        specs: List[JointSpec] = []
        corners = [
            ("front_left", "sill_front_1", "min", "sill_left_1", "max"),
            ("front_right", self._sill_id("front", "max"), "max", "sill_right_1", "max"),
            ("rear_left", "sill_rear_1", "min", "sill_left_1", "min"),
            ("rear_right", self._sill_id("rear", "max"), "max", "sill_right_1", "min"),
        ]
        for corner, cross_sill_id, cross_end, side_sill_id, side_end in corners:
            post_id = f"post_{corner}"
            if not cross_sill_id:
                continue
            post = self.member_registry.get(post_id)
            cross_sill = self.member_registry.get(cross_sill_id)
            side_sill = self.member_registry.get(side_sill_id)
            if post is None or cross_sill is None or side_sill is None:
                continue
            joint_datums = self._post_sill_joint_datums(corner, post, cross_sill, side_sill)
            if joint_datums is None:
                continue
            tenon_height = float(joint_datums["tenon_height"])
            if tenon_height <= 0.0:
                continue
            specs.append(
                JointSpec(
                    id=f"post_sill_corner_{corner}",
                    joint_type="post_sill_corner",
                    member_a=post_id,
                    member_b=side_sill_id,
                    params={
                        "cross_sill_id": cross_sill_id,
                        "cross_sill_end": cross_end,
                        "side_sill_end": side_end,
                        "tenon_height": tenon_height,
                        "joint_datums": joint_datums,
                    },
                )
            )
        specs.extend(self._declare_joist_sill_specs())
        specs.extend(self._declare_post_girt_specs())
        specs.extend(self._declare_girt_splice_specs())
        return specs

    def _declare_post_girt_specs(self) -> List[JointSpec]:
        specs: List[JointSpec] = []
        corners = [
            ("front_left", "front", "min", "left", "max"),
            ("front_right", "front", "max", "right", "max"),
            ("rear_left", "rear", "min", "left", "min"),
            ("rear_right", "rear", "max", "right", "min"),
        ]
        stories = sorted(
            {
                int(story)
                for member in self.member_registry.values()
                if member.role == "girt"
                for story in [self._member_datum_value(member, "story")]
                if story is not None
            }
        )
        for story in stories:
            for corner, face_a, end_a, face_b, end_b in corners:
                post = self.member_registry.get(f"post_{corner}")
                girt_a = self.member_registry.get(self._girt_id(face_a, story, end_a))
                girt_b = self.member_registry.get(self._girt_id(face_b, story, end_b))
                if post is None:
                    continue
                for girt, end in ((girt_a, end_a), (girt_b, end_b)):
                    if girt is None:
                        continue
                    specs.append(
                        JointSpec(
                            id=f"post_girt_{corner}_{girt.id}",
                            joint_type="post_girt",
                            member_a=girt.id,
                            member_b=post.id,
                            params={
                                "axis": self._member_datum_value(girt, "axis"),
                                "girt_end": end,
                                "tenon_length": self._post_girt_tenon_length(girt, post, end),
                            },
                        )
                    )
        return specs

    def _post_girt_tenon_length(self, girt: FramingMember, post: FramingMember, end: str) -> float:
        params = load_json_config("framing", "FRAMING_CONFIG_PATH").get("joinery", {}).get("post_to_girt", {})
        reveal = float(params.get("tenon_reveal", 0.125))
        axis = self._member_datum_value(girt, "axis")
        if axis == "x":
            if end == "min":
                return abs(girt.world_bounds.min[0] - post.world_bounds.min[0]) + reveal
            return abs(post.world_bounds.max[0] - girt.world_bounds.max[0]) + reveal
        if end == "min":
            return abs(girt.world_bounds.min[1] - post.world_bounds.min[1]) + reveal
        return abs(post.world_bounds.max[1] - girt.world_bounds.max[1]) + reveal

    def _declare_girt_splice_specs(self) -> List[JointSpec]:
        specs: List[JointSpec] = []
        grouped: Dict[Tuple[str, int], List[FramingMember]] = {}
        for member in self.member_registry.values():
            if member.role != "girt" or member.face is None or member.index is None:
                continue
            story = self._member_datum_value(member, "story")
            if story is None:
                continue
            grouped.setdefault((member.face, int(story)), []).append(member)

        for (face, story), girts in grouped.items():
            girts.sort(key=lambda member: member.index or 0)
            for left, right in zip(girts, girts[1:]):
                axis = self._member_datum_value(left, "axis")
                if axis == "x":
                    member_a_end, member_b_end = "max", "min"
                    plate_width = left.local_bounds.size[1]
                else:
                    member_a_end, member_b_end = "min", "max"
                    plate_width = left.local_bounds.size[0]
                splice_position = self._girt_splice_position(left, right, axis)
                specs.append(
                    JointSpec(
                        id=f"girt_splice_{face}_story{story}_{left.index}_{right.index}",
                        joint_type="plate_splice",
                        member_a=left.id,
                        member_b=right.id,
                        params={
                            "axis": axis,
                            "member_a_end": member_a_end,
                            "member_b_end": member_b_end,
                            "member_a_splice_position": splice_position[0],
                            "member_b_splice_position": splice_position[1],
                            "plate_width": plate_width,
                            "plate_height": left.local_bounds.size[2],
                        },
                    )
                )
        return specs

    @staticmethod
    def _girt_splice_position(left: FramingMember, right: FramingMember, axis: str) -> Tuple[float, float]:
        if axis == "x":
            boundary = (left.world_bounds.max[0] + right.world_bounds.min[0]) / 2.0
            left_position = boundary - left.world_bounds.min[0]
            right_position = boundary - right.world_bounds.min[0]
        else:
            boundary = (left.world_bounds.min[1] + right.world_bounds.max[1]) / 2.0
            left_position = boundary - left.world_bounds.min[1]
            right_position = boundary - right.world_bounds.min[1]
        return left_position, right_position

    def _declare_joist_sill_specs(self) -> List[JointSpec]:
        specs: List[JointSpec] = []
        joists = [
            member
            for member in self.member_registry.values()
            if member.role == "joist" and self._member_datum_value(member, "story") == 1
        ]
        joists.sort(key=lambda member: member.index or 0)
        for joist in joists:
            joist_datums = joist.node.metadata.get("framing_datums", {})
            center = joist_datums.get("center")
            min_corner = joist_datums.get("min_corner")
            max_corner = joist_datums.get("max_corner")
            size = joist_datums.get("size")
            if not all(isinstance(value, list) for value in (center, min_corner, max_corner, size)):
                continue

            joist_center_x = float(center[0])
            for face, direction, joist_end_y, joist_end_world_y in (
                ("front", 1, float(size[1]), float(max_corner[1])),
                ("rear", -1, 0.0, float(min_corner[1])),
            ):
                sill = self._sill_for_x(face, joist_center_x)
                if sill is None:
                    continue
                sill_datums = sill.node.metadata.get("framing_datums", {})
                sill_min = sill_datums.get("min_corner")
                sill_size = sill_datums.get("size")
                if not isinstance(sill_min, list) or not isinstance(sill_size, list):
                    continue
                specs.append(
                    JointSpec(
                        id=f"joist_sill_story1_{joist.index}_{face}",
                        joint_type="joist_sill",
                        member_a=joist.id,
                        member_b=sill.id,
                        params={
                            "joint_datums": {
                                "face": face,
                                "direction": direction,
                                "joist_end_y": joist_end_y,
                                "joist_top_z": float(size[2]),
                                "joist_tail_center_x": float(size[0]) / 2.0,
                                "sill_socket_center_x": joist_center_x - float(sill_min[0]),
                                "sill_socket_center_y": joist_end_world_y - float(sill_min[1]),
                                "sill_top_z": float(sill_size[2]),
                            },
                        },
                    )
                )
        return specs

    def _sill_for_x(self, face: str, x: float) -> Optional[FramingMember]:
        for member in self.member_registry.values():
            if member.role != "sill" or member.face != face:
                continue
            datums = member.node.metadata.get("framing_datums", {})
            min_corner = datums.get("min_corner")
            max_corner = datums.get("max_corner")
            if not isinstance(min_corner, list) or not isinstance(max_corner, list):
                continue
            if float(min_corner[0]) <= x <= float(max_corner[0]):
                return member
        return None

    @staticmethod
    def _member_datum_value(member: FramingMember, key: str) -> Any:
        datums = member.node.metadata.get("framing_datums", {})
        if not isinstance(datums, dict):
            return None
        return datums.get(key)

    @staticmethod
    def _post_sill_joint_datums(
        corner: str,
        post: FramingMember,
        cross_sill: FramingMember,
        side_sill: FramingMember,
    ) -> Optional[Dict[str, object]]:
        post_datums = post.node.metadata.get("framing_datums", {})
        cross_datums = cross_sill.node.metadata.get("framing_datums", {})
        side_datums = side_sill.node.metadata.get("framing_datums", {})
        post_bottom_z = post_datums.get("bottom_z")
        cross_sill_top_z = cross_datums.get("top_z")
        side_sill_top_z = side_datums.get("top_z")
        post_center = post_datums.get("center")
        side_min = side_datums.get("min_corner")
        if (
            post_bottom_z is None
            or cross_sill_top_z is None
            or side_sill_top_z is None
            or not isinstance(post_center, list)
            or not isinstance(side_min, list)
        ):
            return None
        sill_top_z = min(float(cross_sill_top_z), float(side_sill_top_z))
        return {
            "corner": corner,
            "post_bottom_z": float(post_bottom_z),
            "cross_sill_top_z": float(cross_sill_top_z),
            "side_sill_top_z": float(side_sill_top_z),
            "side_sill_mortise_center_x": float(post_center[0]) - float(side_min[0]),
            "side_sill_mortise_center_y": float(post_center[1]) - float(side_min[1]),
            "tenon_height": sill_top_z - float(post_bottom_z),
        }

    def _sill_id(self, face: str, end: str) -> Optional[str]:
        sills = [
            member
            for member in self.member_registry.values()
            if member.role == "sill" and member.face == face and member.index is not None
        ]
        if not sills:
            return None
        sills.sort(key=lambda member: member.index or 0)
        return sills[0].id if end == "min" else sills[-1].id

    def _girt_id(self, face: str, story: int, end: str) -> Optional[str]:
        girts = [
            member
            for member in self.member_registry.values()
            if (
                member.role == "girt"
                and member.face == face
                and member.index is not None
                and self._member_datum_value(member, "story") == story
            )
        ]
        if not girts:
            return None
        girts.sort(key=lambda member: member.index or 0)
        return girts[0].id if end == "min" else girts[-1].id

    @staticmethod
    def _face_for_component(component_name: str) -> Optional[str]:
        parts = component_name.split("_")
        if len(parts) >= 3 and parts[0] in ("sill", "girt"):
            return parts[1]
        if len(parts) >= 4 and parts[0] == "bay" and parts[1] == "stud":
            return parts[2]
        if len(parts) >= 4 and parts[0] == "cripple" and parts[1] == "stud":
            return parts[2]
        if len(parts) >= 3 and parts[0] == "stud":
            return parts[1]
        return None

    @staticmethod
    def _index_for_component(component_name: str) -> Optional[int]:
        parts = component_name.split("_")
        if len(parts) >= 3 and parts[0] == "sill":
            try:
                return int(parts[2])
            except ValueError:
                return None
        if len(parts) >= 3 and parts[0] == "joist":
            try:
                return int(parts[2])
            except ValueError:
                return None
        if len(parts) >= 4 and parts[0] == "girt":
            try:
                return int(parts[3])
            except ValueError:
                return None
        if len(parts) >= 5 and parts[0] == "bay" and parts[1] == "stud":
            try:
                return int(parts[4].removeprefix("bay"))
            except ValueError:
                return None
        if len(parts) >= 5 and parts[0] == "cripple" and parts[1] == "stud":
            try:
                return int(parts[4].removeprefix("bay"))
            except ValueError:
                return None
        return None

    @staticmethod
    def _group_name_for_component(component_name: str) -> str:
        parts = component_name.split("_")
        if not parts:
            return "members"
        if parts[0] == "cripple" and len(parts) > 1:
            return "cripple_studs"
        return f"{parts[0]}s"
    
    def _add_sills(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add sills to the assembly."""
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        
        member_type = "sill"
        sill_height = 8
        sill_depth = 10
        # Sill bottom should sit on foundation top (z=0)
        # Since box is centered, raise by half depth so bottom is at z=0
        sill_z_offset = sill_depth / 2
        total_quantity = 0
        
        for face in self.faces:
            dimension = self.faces[face]

            quantity, sill_length = self._member_quantity_and_length(dimension)
            
            for q in range(quantity):
                sill_counter = q + 1
                
                if face == "front":
                    new_x = (sill_length * sill_counter) - (sill_length/2) + x_offset
                    new_y = 0 + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(sill_length, sill_height, sill_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (sill_length * sill_counter) - (sill_length/2) + x_offset
                    new_y = -right_dimension + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(sill_length, sill_height, sill_depth).translate((new_x, new_y, new_z))
                elif face == "left":
                    new_x = 0 + x_offset
                    new_y = -((sill_length * sill_counter) - (sill_length/2)) + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(sill_height, sill_length, sill_depth).translate((new_x, new_y, new_z))
                elif face == "right":
                    new_x = front_dimension + x_offset
                    new_y = -((sill_length * sill_counter) - (sill_length/2)) + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(sill_height, sill_length, sill_depth).translate((new_x, new_y, new_z))
                
                # Add sill with descriptive name including member_type and face
                assembly.add(sill, name=f"{member_type}_{face}_{sill_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                total_quantity += 1
        
        self._add_sill_bom(total_quantity, sill_height, sill_depth)
    
    def _add_posts(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add corner posts to the assembly."""
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]

        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        stories = self.floorplan.stories

        
        post_width = 6
        post_depth = 4
        post_height = ceiling_heights[stories - 1] - floor_heights[0]
        quantity = 4
        member_type = "post"
        post_tenon_depth = 2

        left_x = 0 + x_offset
        right_x = front_dimension + x_offset
        front_y = 0 + y_offset
        rear_y = -right_dimension + y_offset
        new_z = floor_heights[0] - post_tenon_depth + (post_height / 2)
        
        front_left_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((left_x, front_y, new_z))
        rear_left_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((left_x, rear_y, new_z))
        front_right_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((right_x, front_y, new_z))
        rear_right_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((right_x, rear_y, new_z))
        
        # Add posts with descriptive names
        assembly.add(front_left_post, name=f"{member_type}_front_left", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        assembly.add(rear_left_post, name=f"{member_type}_rear_left", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        assembly.add(front_right_post, name=f"{member_type}_front_right", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        assembly.add(rear_right_post, name=f"{member_type}_rear_right", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        self._add_post_bom(quantity, post_width, post_depth, post_height)
    
    def _add_joists(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add joists for a story."""
        joist_width = 3
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        member_type = "joist"
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        joist_spacing = self.joist_spacing
        
        # Set the joist z position based on the story and floor height
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        joist_z = floor_height - (joist_height / 2)
   
        # Set the joist length based on the story and roof overhang
        if story == len(self.joist_heights):
            joist_length = (self.roof_overhang * 2) + right_dimension
        else:
            joist_length = right_dimension
        
        # Set the quantity of joists based on the front dimension and joist spacing
        quantity = math.ceil(front_dimension / joist_spacing)
        
        for q in range(quantity):
            # X position: fixed at depth center (matches original, but seems wrong)
            new_x = x_offset + (right_dimension/2)
            # Y position: spaced - this becomes X spacing after rotation!
            new_y = (q * joist_spacing) + joist_spacing + y_offset
            new_z = joist_z
            joist = cq.Workplane('XY').box(joist_length, joist_width, joist_height).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
            # Add joist with descriptive name including member_type, story, and position
            assembly.add(joist, name=f"{member_type}_story{story}_{q+1}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, joist_length / 12, joist_width, joist_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_braces(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add braces for a story."""
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        right_offset = right_dimension / 2
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        brace_width = 6
        brace_depth = 4
        member_type = "brace"
        total_quantity = 0
        
        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        ceiling_height = ceiling_heights[story - 1]
        next_floor_height = floor_heights[story]
        face_brace_length = (ceiling_height - floor_height)
        side_brace_length = (next_floor_height - floor_height) - 6
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        for face in self.faces:
            brace_centerline = self.centerlines[face][0] if self.centerlines[face] else 64
            index = len(self.centerlines[face]) - 1 if self.centerlines[face] else 0
            dimension = self.faces[face]
            alt_brace_centerline = dimension - (self.centerlines[face][index] if self.centerlines[face] else dimension - 64)
            
            total_quantity += 2
            
            # Calculate brace positions and angles (simplified - full implementation would match original logic)
            if face == "left":
                brace_height = math.ceil(side_brace_length * (2/3))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = 180 - math.degrees(math.atan(brace_centerline / brace_height))
                new_x = brace_centerline / 2 + x_offset
                new_y = 0 + y_offset
                new_z = (brace_height / 2) + floor_height
                
                alt_brace_height = math.ceil(face_brace_length * (2/3))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = 0 + x_offset
                alt_y = -(alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + floor_height
            elif face == "rear":
                brace_height = math.ceil(side_brace_length * (5/8))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = 180 - math.degrees(math.atan(brace_centerline / brace_height))
                new_x = brace_centerline / 2 + x_offset
                new_y = -right_dimension + y_offset
                new_z = (brace_height / 2) + floor_height
                
                alt_brace_height = math.ceil(face_brace_length * (5/8))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = 180 - math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = 0 + x_offset
                alt_y = -right_dimension + (alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + floor_height
            elif face == "right":
                brace_height = math.ceil(side_brace_length * (2/3))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = math.degrees(math.atan(brace_centerline / brace_height))
                new_x = front_dimension - (brace_centerline / 2) + x_offset
                new_y = 0 + y_offset
                new_z = (brace_height / 2) + floor_height
                
                alt_brace_height = math.ceil(face_brace_length * (2/3))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = front_dimension + x_offset
                alt_y = -(alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + floor_height
            elif face == "front":  # front
                brace_height = math.ceil(side_brace_length * (5/8))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = math.degrees(math.atan(brace_centerline / brace_height))
                new_x = front_dimension - (brace_centerline / 2) + x_offset
                new_y = -right_dimension + y_offset
                new_z = (brace_height / 2) + floor_height
                
                alt_brace_height = math.ceil(face_brace_length * (5/8))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = 180 - math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = front_dimension + x_offset
                alt_y = -right_dimension + (alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + floor_height
            
            # Add braces to assembly with descriptive names
            brace = cq.Workplane('XY').box(brace_width, brace_depth, brace_length).translate((new_x, new_y, new_z)).rotateAboutCenter((0, 1, 0), brace_angle)
            alt_brace = cq.Workplane('XY').box(brace_width, brace_depth, alt_brace_length).translate((alt_x, alt_y, alt_z)).rotateAboutCenter((0, 1, 0), alt_brace_angle).rotateAboutCenter((0, 0, 1), 90)
            assembly.add(brace, name=f"{member_type}_{face}_story{story}_primary", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
            assembly.add(alt_brace, name=f"{member_type}_{face}_story{story}_alt", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, brace_length / 12, brace_width, brace_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_bays(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add bay studs for a story."""
        front_dimension = self.faces["front"]
        right_dimension = self.faces["right"]
        bay_stud_width = 5
        bay_stud_height = 4
        cripple_stud_width = 3
        cripple_stud_height = 4
        cripple_stud_length = self.chair_rail_height
        member_type = "bay_stud"
        total_quantity = 0
        cripple_quantity = 0
        stud_tenon_depth = 2
        
        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        ceiling_height = ceiling_heights[story - 1]
        next_floor_height = floor_heights[story]
        face_stud_length = (ceiling_height - floor_height) + (2*stud_tenon_depth)
        side_stud_length = (next_floor_height - floor_height) + (2*stud_tenon_depth) - 6
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        
        for face in self.faces:
            centerline = self.centerlines[face]
            if not centerline:
                continue
                
            self.bay_studs[face] = []
            total_quantity += 2 * len(centerline)

            if story == 1:
                new_z = floor_height - stud_tenon_depth
            else:
                new_z = floor_height - (joist_height + stud_tenon_depth)
            
            # Set base positions for each face
            if face == "front":
                new_x = 0 + x_offset
                new_y = 0 + y_offset
                stud_length = face_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "rear":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset 
                stud_length = face_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "left":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                stud_length = side_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "right":
                new_x = front_dimension + x_offset
                new_y = -right_dimension + y_offset
                stud_length = side_stud_length
                new_z = new_z + (stud_length / 2)
            # Create bay studs for each centerline
            for i, c in enumerate(centerline):
                bay = i + 1
                
                # Check if this bay has a door or window opening on this floor
                has_opening = False
                for opening in self.openings:
                    if (opening.get('wall') == face and 
                        opening.get('position') == c and 
                        opening.get('floor') == story):
                        has_opening = True
                        break
                
                # Determine if cripple stud is needed
                # Cripple studs support window sills, so skip them for door openings (which sit on floor)
                if has_opening:
                    # Check if it's a door (no cripple stud needed)
                    is_door = any(opening.get('wall') == face and 
                                 opening.get('position') == c and 
                                 opening.get('floor') == story and
                                 opening.get('type') == 'door' 
                                 for opening in self.openings)
                    cripple_flag = not is_door  # Windows get cripple studs, doors don't
                elif face in ["left", "right"] and bay in [1, 2]:
                    cripple_flag = True
                elif face in ["rear", "front"]:
                    cripple_flag = True
                else:
                    cripple_flag = False
                
                if face in ["left", "right"]:
                    # Left/right faces: studs positioned along Y axis
                    left_stud_y_position = new_y + c - ((self.bay_spacing + bay_stud_width) / 2)
                    right_stud_y_position = new_y + c + ((self.bay_spacing + bay_stud_width) / 2)
                    left_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, stud_length).translate((new_x, left_stud_y_position, new_z))
                    right_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, stud_length).translate((new_x, right_stud_y_position, new_z))
                    self.bay_studs[face].append(left_stud_y_position)
                    self.bay_studs[face].append(right_stud_y_position)
                    
                    if cripple_flag:
                        cripple_stud_y_position = left_stud_y_position + (-(left_stud_y_position - right_stud_y_position) / 2)
                        cripple_stud_z_position = floor_height + (cripple_stud_length / 2)
                        cripple_stud = cq.Workplane('XY').box(cripple_stud_height, cripple_stud_width, cripple_stud_length).translate((new_x, cripple_stud_y_position, cripple_stud_z_position))
                        self.bay_studs[face].append(cripple_stud_y_position)
                        assembly.add(cripple_stud, name=f"cripple_stud_{face}_story{story}_bay{bay}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                        cripple_quantity += 1
                
                elif face in ["front", "rear"]:
                    # Front/rear faces: studs positioned along X axis
                    left_stud_x_position = new_x + c - ((self.bay_spacing + bay_stud_width) / 2)
                    right_stud_x_position = new_x + c + ((self.bay_spacing + bay_stud_width) / 2)
                    left_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, stud_length).translate((left_stud_x_position, new_y, new_z))
                    right_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, stud_length).translate((right_stud_x_position, new_y, new_z))
                    self.bay_studs[face].append(left_stud_x_position)
                    self.bay_studs[face].append(right_stud_x_position)
                    
                    if cripple_flag:
                        cripple_stud_x_position = left_stud_x_position + ((right_stud_x_position - left_stud_x_position) / 2)
                        cripple_stud_z_position = floor_height + (cripple_stud_length / 2)
                        cripple_stud = cq.Workplane('XY').box(cripple_stud_width, cripple_stud_height, cripple_stud_length).translate((cripple_stud_x_position, new_y, cripple_stud_z_position))
                        self.bay_studs[face].append(cripple_stud_x_position)
                        assembly.add(cripple_stud, name=f"cripple_stud_{face}_story{story}_bay{bay}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                        cripple_quantity += 1
                
                # Add bay studs with descriptive names
                assembly.add(left_stud, name=f"{member_type}_{face}_story{story}_bay{bay}_left", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                assembly.add(right_stud, name=f"{member_type}_{face}_story{story}_bay{bay}_right", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, stud_length / 12, bay_stud_width, bay_stud_height, self.materials
        )
        raw_material_id_cripple, component_id_cripple = add_framing_materials(
            "cripple_stud", cripple_stud_length / 12, cripple_stud_width, cripple_stud_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_production_bom_quantities(
            component_id_cripple, raw_material_id_cripple, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id_cripple, self.structure_hash, cripple_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_studs(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add wall studs for a story."""
        front_dimension = self.faces["front"]
        right_dimension = self.faces["right"]
        bay_stud_width = 5
        stud_width = 3
        stud_height = 4
        member_type = "stud"
        total_quantity = 0
        stud_tenon_depth = 2
        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        ceiling_height = ceiling_heights[story - 1]
        next_floor_height = floor_heights[story]
        face_stud_length = (ceiling_height - floor_height) + (2*stud_tenon_depth)
        side_stud_length = (next_floor_height - floor_height) + (2*stud_tenon_depth) - 6
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        for face in self.faces:
            self.stud_centerlines[face] = []
            stud_positions = self.bay_studs.get(face, []).copy()
            stud_quantity = 0
            
            if story == 1:
                new_z = floor_height - stud_tenon_depth
            else:
                new_z = floor_height - (joist_height + stud_tenon_depth)
            
            # Set base positions for each face
            if face == "front":
                new_x = 0 + x_offset
                new_y = 0 + y_offset
                last_position = front_dimension - 6
                stud_length = face_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "rear":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                last_position = front_dimension - 6
                stud_length = face_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "left":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                last_position = -right_dimension - 4
                stud_length = side_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "right":
                new_x = front_dimension + x_offset
                new_y = -right_dimension + y_offset
                last_position = -right_dimension - 4
                stud_length = side_stud_length
                new_z = new_z + (stud_length / 2)
            # Add the last position for the post
            stud_positions.append(last_position)
            
            # Sort the array of stud positions
            stud_positions.sort()
            
            # Find the max index
            max_index = len(stud_positions) - 1
            
            # Loop through the positions and find how many studs go in each section
            for index, position in enumerate(stud_positions):
                wall_quantity = 0
                
                # Calculate prior and current positions
                if index == 0 and face in ["left", "right"]:
                    prior_position = -right_dimension + 4
                    current_position = position - (bay_stud_width / 2)
                elif index == 0 and face in ["front", "rear"]:
                    prior_position = 6
                    current_position = position - (bay_stud_width / 2)
                else:
                    prior_position = stud_positions[index - 1] + (bay_stud_width / 2)
                    current_position = position - (bay_stud_width / 2)
                
                # Calculate wall length
                if face in ["left", "right"]:
                    wall_length = abs(prior_position - current_position)
                elif face in ["front", "rear"]:
                    wall_length = current_position - prior_position
                
                # Determine the stud spacing using complex algorithm
                if wall_length / 4 >= 13:
                    wall_quantity = 3
                elif wall_length / 3 >= 13:
                    wall_quantity = 2
                elif wall_length / 2 > 16:
                    wall_quantity = 1
                elif wall_length / 2 <= 16 and index == max_index:
                    wall_quantity = 1
                elif wall_length % (2 * self.stud_spacing) >= 22:
                    wall_quantity = math.ceil(wall_length / (2 * self.stud_spacing))
                else:
                    wall_quantity = math.floor(wall_length / (2 * self.stud_spacing))
                
                stud_quantity += wall_quantity
                
                # Create studs for this wall section
                for wall in range(wall_quantity):
                    if face in ["left", "right"]:
                        stud_y_position = prior_position + ((wall_length / (wall_quantity + 1)) * (wall + 1))
                        stud = cq.Workplane('XY').box(stud_height, stud_width, stud_length).translate((new_x, stud_y_position, new_z))
                        assembly.add(stud, name=f"{member_type}_{face}_story{story}_section{index}_wall{wall+1}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                        self.stud_centerlines[face].append(stud_y_position)
                    elif face in ["front", "rear"]:
                        stud_x_position = prior_position + ((wall_length / (wall_quantity + 1)) * (wall + 1))
                        # Special case: skip stud at position 240 for front face, story 1
                        if face == "front" and story == 1 and stud_x_position == 240:
                            stud_quantity = stud_quantity - 1
                            continue
                        else:
                            stud = cq.Workplane('XY').box(stud_width, stud_height, stud_length).translate((stud_x_position, new_y, new_z))
                            assembly.add(stud, name=f"{member_type}_{face}_story{story}_section{index}_wall{wall+1}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                            self.stud_centerlines[face].append(stud_x_position)
            
            total_quantity += stud_quantity
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, stud_length / 12, stud_width, stud_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_girts(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add girts for a story."""
        member_type = "girt"
        total_quantity = 0
        girt_width = float(self.framing_defaults.get("girt_width", 4.0))
        girt_depth = float(self.framing_defaults.get("girt_depth", 6.0))
        
        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        ceiling_height = ceiling_heights[story - 1]
        next_floor_height = floor_heights[story]
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
            
        for face in self.faces:
            dimension = self.faces[face]
            right_dimension = self.faces["right"]
            front_dimension = self.faces["front"]

            if dimension <= self.max_member_length:
                quantity = 1
                girt_length = dimension
            elif dimension >= self.max_member_length:
                quantity = math.ceil(dimension / self.max_member_length)
                girt_length = dimension / quantity
            else:
                quantity = 1
                girt_length = self.max_member_length
            
            total_quantity += quantity
            
            # Create girts for this face
            for q in range(quantity):
                girt_counter = q + 1
                
                if face == "front":
                    new_x = (girt_length * girt_counter) - (girt_length / 2) + x_offset
                    new_y = 0 + y_offset
                    new_z = floor_height - (girt_depth / 2) - joist_height
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (girt_length * girt_counter) - (girt_length / 2) + x_offset
                    new_y = -right_dimension + y_offset
                    new_z = floor_height - (girt_depth / 2) - joist_height
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z))
                elif face == "left":
                    # Left girts run along Y axis (front to rear)
                    # X position: fixed at left wall (x=0)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = (girt_length * girt_counter) - (girt_length / 2) + x_offset
                    new_y = 0 + y_offset
                    new_z = floor_height - (girt_depth / 2)
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
                elif face == "right":
                    # Right girts run along Y axis (front to rear)
                    # X position: fixed at right wall (x=front_dimension)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = (girt_length * girt_counter) - (girt_length / 2) + x_offset
                    new_y = front_dimension + y_offset
                    new_z = floor_height - (girt_depth / 2)
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
                
                # Add the girt to the assembly with descriptive name
                assembly.add(girt, name=f"{member_type}_{face}_story{story}_{girt_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        self._add_girt_bom(total_quantity, girt_length, girt_width, girt_depth)
    
    def _add_plates(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add plates for a story."""
        member_type = "plate"
        plate_width = 4
        plate_depth = 6
        total_quantity = 0
        floor_heights = self.calculated_floor_heights
        next_floor_height = floor_heights[story]
        next_joist_height = self.joist_heights[story] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        
        for face in self.faces:
            dimension = self.faces[face]
            right_dimension = self.faces["right"]
            front_dimension = self.faces["front"]

            if dimension <= self.max_member_length:
                quantity = 1
                plate_length = dimension
            elif dimension >= self.max_member_length:
                quantity = math.ceil(dimension / self.max_member_length)
                plate_length = dimension / quantity
            else:
                quantity = 1
                plate_length = self.max_member_length

            total_quantity += quantity

            for q in range(quantity):
    
                plate_counter = q + 1
                
                if face == "front":
                    new_x = (plate_length * plate_counter) - (plate_length / 2) + x_offset
                    new_y = 0 + y_offset
                    new_z = next_floor_height - (plate_depth / 2) - next_joist_height
                    plate = cq.Workplane('XY').box(plate_length, plate_width, plate_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (plate_length * plate_counter) - (plate_length / 2) + x_offset
                    new_y = -right_dimension + y_offset
                    new_z = next_floor_height - (plate_depth / 2) - next_joist_height
                    plate = cq.Workplane('XY').box(plate_length, plate_width, plate_depth).translate((new_x, new_y, new_z))
                elif face == "left":
                    new_x = (plate_length * plate_counter) - (plate_length / 2) + x_offset
                    new_y = 0 + y_offset
                    new_z = next_floor_height - (plate_depth / 2)
                    plate = cq.Workplane('XY').box(plate_length, plate_width, plate_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1),(0,0,0), 90)
                elif face == "right":
                    new_x = (plate_length * plate_counter) - (plate_length / 2) + x_offset
                    new_y = +(front_dimension) + y_offset
                    new_z = next_floor_height - (plate_depth / 2)
                    plate = cq.Workplane('XY').box(plate_length, plate_width, plate_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1),(0,0,0), 90)

                assembly.add(plate, name=f"{member_type}_{face}_story{story}_{plate_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, plate_length / 12, plate_width, plate_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_false_plates(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add false plates for roof."""
        member_type = "false_plate"
        false_plate_width = 10
        false_plate_depth = 2
        total_quantity = 0
        floor_heights = self.calculated_floor_heights
        stories = self.floorplan.stories
        floor_height = floor_heights[stories]


        for face in ["front", "rear"]:
            dimension = self.faces[face]
            right_dimension = self.faces["right"]
            roof_overhang = self.roof_overhang
            
            if dimension <= self.max_member_length:
                quantity = 1
                false_plate_length = dimension
            elif dimension >= self.max_member_length:
                quantity = math.ceil(dimension / self.max_member_length)
                false_plate_length = dimension / quantity
            else:
                quantity = 1
                false_plate_length = self.max_member_length

            total_quantity += quantity

            for q in range(quantity):
                false_plate_counter = q + 1

                if face == "front":
                    new_x = (false_plate_length * false_plate_counter) - (false_plate_length / 2) + x_offset
                    new_y = (roof_overhang/2)
                    new_z = floor_height + (false_plate_depth / 2)
                    false_plate = cq.Workplane('XY').box(false_plate_length, false_plate_width, false_plate_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (false_plate_length * false_plate_counter) - (false_plate_length / 2) + x_offset
                    new_y = -(right_dimension) - (roof_overhang/2)
                    new_z = floor_height + (false_plate_depth / 2)
                    false_plate = cq.Workplane('XY').box(false_plate_length, false_plate_width, false_plate_depth).translate((new_x, new_y, new_z))
                else: continue

                assembly.add(false_plate, name=f"{member_type}_{face}_{false_plate_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, false_plate_length / 12, false_plate_width, false_plate_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_rafters(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add rafters for roof."""
        member_type = "rafter"
        rafter_width = 3
        rafter_depth = 6
        rafter_spacing = self.rafter_spacing
        roof_overhang = self.roof_overhang
        roof_pitch_degrees = self.roof_pitch_degrees
        total_quantity = 0

        floor_heights = self.calculated_floor_heights
        stories = self.floorplan.stories
        floor_height = floor_heights[stories]
        
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        
        for face in ["front", "rear"]:
            quantity = math.ceil(front_dimension / rafter_spacing) + 1
            total_quantity += quantity
            
            # Rafter extends from ridge to 12" past actual weatherboard outer faces
            # Actual weatherboard positions: front y=2.674, rear y=-250.528
            front_weatherboard_y = 2.674
            rear_weatherboard_y = -250.528
            # Ridge at midpoint between weatherboard outer faces
            centerline_y = (front_weatherboard_y + rear_weatherboard_y) / 2
            
            # Target eave positions: 12" past weatherboard on both faces
            front_eave_target_y = front_weatherboard_y + roof_overhang
            rear_eave_target_y = rear_weatherboard_y - roof_overhang
            
            # Calculate rafter geometry
            roof_pitch_radians = roof_pitch_degrees * (math.pi / 180)
            rafter_cos = math.cos(roof_pitch_radians)
            rafter_sin = math.sin(roof_pitch_radians)
            
            # Both rafters have same run from ridge to their respective eaves
            # Front rafter run: from centerline to front eave target
            front_rafter_run = front_eave_target_y - centerline_y
            # Rear rafter run: from centerline to rear eave target  
            rear_rafter_run = centerline_y - rear_eave_target_y
            
            if face == "front":
                # Front rafter: ridge to front eave (12" past front weatherboard)
                # Target eave should match AG panel eave position
                target_eave_y = front_weatherboard_y + roof_overhang
                rafter_run = target_eave_y - centerline_y
                rafter_length = rafter_run / rafter_cos if rafter_cos > 0 else rafter_run
                # Initial positioning (will be adjusted after calculating tip position)
                new_x = +(right_dimension/2) + x_offset
                roof_pitch = roof_pitch_degrees
                new_z = floor_height + (rafter_length/2 * rafter_sin) - rafter_depth
            elif face == "rear":
                # Rear rafter: ridge to rear eave (12" past rear weatherboard)
                # Target eave should match AG panel eave position
                target_eave_y = rear_weatherboard_y - roof_overhang
                rafter_run = centerline_y - target_eave_y
                rafter_length = rafter_run / rafter_cos if rafter_cos > 0 else rafter_run
                # Initial positioning (will be adjusted after calculating tip position)
                new_x = +(right_dimension/2) + x_offset
                roof_pitch = 180 - roof_pitch_degrees
                new_z = floor_height + (rafter_length/2 * rafter_sin) - rafter_depth

            for q in range(quantity):

                rafter_counter = q + 1

                if rafter_counter == 1:
                    new_y = 0 + y_offset
                else:
                    new_y = (rafter_spacing * (rafter_counter - 1)) + y_offset

                # Create rafter with initial positioning, then adjust to seat tip at eave
                # Rafter transformations: translate, pitch about Y, rotate 90° about Z
                # After these transforms, we need the eave tip at target_eave_y
                rafter_temp = cq.Workplane('XY').box(rafter_length, rafter_width, rafter_depth).translate((new_x, new_y, new_z)).rotateAboutCenter((0, 1, 0), roof_pitch).rotate((0,0,1),(0,0,0),90)
                bbox_temp = rafter_temp.val().BoundingBox()
                
                # Find current eave tip position after transformations
                if face == "front":
                    current_eave_y = bbox_temp.ymax  # Front rafter tip at max Y
                elif face == "rear":
                    current_eave_y = bbox_temp.ymin  # Rear rafter tip at min Y
                
                # Calculate adjustment needed to position tip at target
                x_adjustment = target_eave_y - current_eave_y
                adjusted_new_x = new_x + x_adjustment
                
                # Create final rafter with adjusted position
                rafter = cq.Workplane('XY').box(rafter_length, rafter_width, rafter_depth).translate((adjusted_new_x, new_y, new_z)).rotateAboutCenter((0, 1, 0),roof_pitch).rotate((0,0,1),(0,0,0),90)
                assembly.add(rafter, name=f"{member_type}_{face}_{rafter_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, rafter_length / 12, rafter_width, rafter_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_gable_framing(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add gable end framing for side-gable roofs."""
        member_type = "gable_stud"
        stud_width = 3
        stud_depth = 6
        stud_spacing = 21  # Match rafter spacing
        total_quantity = 0
        
        floor_heights = self.calculated_floor_heights
        stories = self.floorplan.stories
        floor_height = floor_heights[stories]
        
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        roof_overhang = self.roof_overhang
        roof_pitch_degrees = self.roof_pitch_degrees
        roof_pitch_radians = roof_pitch_degrees * (math.pi / 180)
        
        # Calculate ridge height
        ridge_run = right_dimension / 2
        ridge_height = floor_height + (ridge_run * math.tan(roof_pitch_radians))
        
        # Gable ends are at x=0 (left) and x=front_dimension (right)
        # We need studs running up the rake from the wall to the ridge
        # Studs should be spaced along the Y axis (depth of building)
        
        for face in ["left", "right"]:
            # Number of studs along the gable face
            quantity = math.ceil(front_dimension / stud_spacing) + 1
            total_quantity += quantity
            
            # Determine X position based on face
            # Adjust for 12" overhang on each end
            if face == "left":
                face_x = -roof_overhang + x_offset
            else:  # right
                face_x = front_dimension + roof_overhang + x_offset
            
            for q in range(quantity):
                # Y position along the gable face
                stud_y = (q * stud_spacing) + y_offset
                
                # Calculate the height of this stud based on its Y position
                # Distance from center of building (where ridge is)
                distance_from_center = abs(stud_y - y_offset + (right_dimension / 2))
                
                # Height at this point (accounting for roof slope)
                if distance_from_center <= (right_dimension / 2):
                    # Point is under the roof
                    stud_top_z = floor_height + ((right_dimension / 2) - distance_from_center) * math.tan(roof_pitch_radians)
                    stud_length = stud_top_z - floor_height
                    
                    if stud_length > 1:  # Only add stud if it's at least 1" tall
                        stud_z = floor_height + (stud_length / 2)
                        
                        # Create stud
                        stud = cq.Workplane('XY').box(stud_depth, stud_width, stud_length).translate((face_x, stud_y, stud_z))
                        
                        # Add to assembly
                        assembly.add(stud, name=f"{member_type}_{face}_{q+1}", color=cq.Color(0.55, 0.45, 0.33))
        
        # Add BOM tracking
        if total_quantity > 0:
            avg_stud_length = (ridge_height - floor_height) / 2  # Approximate average
            raw_material_id, component_id = add_framing_materials(
                member_type, avg_stud_length / 12, stud_width, stud_depth, self.materials
            )
            add_production_bom_quantities(
                component_id, raw_material_id, 1, 2,
                self.bom_quantities, self.bom_levels, self.bom_components
            )
            add_sales_bom_quantities(
                component_id, self.structure_hash, total_quantity, 3,
                self.bom_quantities, self.bom_levels, self.bom_components
            )
