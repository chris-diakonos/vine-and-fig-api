"""Framing placement datums in the cornerstone coordinate convention."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, Literal, Optional, Tuple

from app.services.scene_graph import Rotation, Transform


WallFace = Literal["front", "rear", "left", "right"]
CornerName = Literal["front_left", "front_right", "rear_left", "rear_right"]
AxisName = Literal["x", "y", "z"]
Point3 = Tuple[float, float, float]


@dataclass(frozen=True)
class FramingMemberDatum:
    """A member's placement expressed as a min-corner local datum."""

    component_name: str
    role: str
    size: Point3
    min_corner: Point3
    face: Optional[WallFace] = None
    index: Optional[int] = None
    story: Optional[int] = None
    corner: Optional[CornerName] = None
    axis: AxisName = "z"
    metadata_extra: Dict[str, object] = field(default_factory=dict)

    @property
    def max_corner(self) -> Point3:
        return (
            self.min_corner[0] + self.size[0],
            self.min_corner[1] + self.size[1],
            self.min_corner[2] + self.size[2],
        )

    @property
    def center(self) -> Point3:
        return (
            self.min_corner[0] + self.size[0] / 2.0,
            self.min_corner[1] + self.size[1] / 2.0,
            self.min_corner[2] + self.size[2] / 2.0,
        )

    def metadata(self) -> Dict[str, object]:
        framing_datums = {
            "coordinate_system": "cornerstone_legacy_y",
            "role": self.role,
            "face": self.face,
            "index": self.index,
            "story": self.story,
            "corner": self.corner,
            "axis": self.axis,
            "size": list(self.size),
            "min_corner": list(self.min_corner),
            "max_corner": list(self.max_corner),
            "center": list(self.center),
            "top_z": self.max_corner[2],
            "bottom_z": self.min_corner[2],
        }
        framing_datums.update(self.metadata_extra)
        return {
            "component_name": self.component_name,
            "framing_datums": framing_datums,
        }


@dataclass(frozen=True)
class FramingBraceDatum:
    """A diagonal brace expressed as a local X-axis member plus transform."""

    component_name: str
    role: str
    size: Point3
    local_transform: Transform
    face: WallFace
    story: int
    corner: CornerName
    hand: str
    lower_anchor: Point3
    upper_anchor: Point3
    angle_degrees: float
    length: float
    post_mortise_tier: str
    lower_receiver_role: str
    lower_receiver_id: str
    post_id: str
    crossed_studs: Tuple[str, ...] = ()

    def metadata(self) -> Dict[str, object]:
        return {
            "component_name": self.component_name,
            "framing_datums": {
                "coordinate_system": "cornerstone_legacy_y",
                "role": self.role,
                "face": self.face,
                "story": self.story,
                "corner": self.corner,
                "hand": self.hand,
                "axis": "diagonal",
                "size": list(self.size),
                "lower_anchor": list(self.lower_anchor),
                "upper_anchor": list(self.upper_anchor),
                "angle_degrees": self.angle_degrees,
                "length": self.length,
                "post_mortise_tier": self.post_mortise_tier,
                "lower_receiver_role": self.lower_receiver_role,
                "lower_receiver_id": self.lower_receiver_id,
                "post_id": self.post_id,
                "crossed_studs": list(self.crossed_studs),
            },
        }


@dataclass(frozen=True)
class FramingPlacementDatums:
    """Cornerstone wall lines and framing member cross sections."""

    width: float
    depth: float
    sill_width: float
    sill_height: float
    post_width: float
    post_depth: float
    post_tenon_depth: float

    def sill(self, face: WallFace, segment_index: int, segment_length: float) -> FramingMemberDatum:
        counter = segment_index + 1
        run_min = segment_index * segment_length
        run_max = (segment_index + 1) * segment_length
        if segment_index == 0:
            run_min -= self.sill_width / 2.0
        if run_max >= self._wall_length(face):
            run_max += self.sill_width / 2.0
        run_length = run_max - run_min

        if face == "front":
            size = (run_length, self.sill_width, self.sill_height)
            min_corner = (run_min, -self.sill_width / 2.0, 0.0)
            axis: AxisName = "x"
        elif face == "rear":
            size = (run_length, self.sill_width, self.sill_height)
            min_corner = (run_min, -self.depth - self.sill_width / 2.0, 0.0)
            axis = "x"
        elif face == "left":
            size = (self.sill_width, run_length, self.sill_height)
            min_corner = (-self.sill_width / 2.0, -run_max, 0.0)
            axis = "y"
        else:
            size = (self.sill_width, run_length, self.sill_height)
            min_corner = (self.width - self.sill_width / 2.0, -run_max, 0.0)
            axis = "y"

        return FramingMemberDatum(
            component_name=f"sill_{face}_{counter}",
            role="sill",
            face=face,
            index=counter,
            axis=axis,
            size=size,
            min_corner=min_corner,
        )

    def joist(
        self,
        story: int,
        index: int,
        center_x: float,
        y_min: float,
        joist_length: float,
        joist_width: float,
        joist_height: float,
        floor_height: float,
        metadata_extra: Optional[Dict[str, object]] = None,
    ) -> FramingMemberDatum:
        return FramingMemberDatum(
            component_name=f"joist_story{story}_{index}",
            role="joist",
            index=index,
            story=story,
            axis="y",
            size=(joist_width, joist_length, joist_height),
            min_corner=(center_x - joist_width / 2.0, y_min, floor_height - joist_height),
            metadata_extra=metadata_extra or {},
        )

    def plate(
        self,
        face: WallFace,
        story: int,
        segment_index: int,
        segment_length: float,
        ceiling_joist_bottom_z: float,
        joist_notch_depth: float,
        plate_width: float,
        plate_depth: float,
    ) -> FramingMemberDatum:
        counter = segment_index + 1
        run_min = segment_index * segment_length
        run_max = (segment_index + 1) * segment_length
        plate_top_z = ceiling_joist_bottom_z + joist_notch_depth
        min_z = plate_top_z - plate_depth

        if face == "front":
            size = (segment_length, plate_width, plate_depth)
            min_corner = (run_min, self.sill_width / 2.0 - plate_width, min_z)
            axis: AxisName = "x"
        elif face == "rear":
            size = (segment_length, plate_width, plate_depth)
            min_corner = (run_min, -self.depth - self.sill_width / 2.0, min_z)
            axis = "x"
        elif face == "left":
            size = (plate_width, segment_length, plate_depth)
            min_corner = (-self.sill_width / 2.0, -run_max, min_z)
            axis = "y"
        else:
            size = (plate_width, segment_length, plate_depth)
            min_corner = (self.width + self.sill_width / 2.0 - plate_width, -run_max, min_z)
            axis = "y"

        return FramingMemberDatum(
            component_name=f"plate_{face}_story{story}_{counter}",
            role="plate",
            face=face,
            index=counter,
            story=story,
            axis=axis,
            size=size,
            min_corner=min_corner,
            metadata_extra={
                "ceiling_joist_bottom_z": ceiling_joist_bottom_z,
                "top_plate_notch_depth": joist_notch_depth,
            },
        )

    def false_plate(
        self,
        face: WallFace,
        segment_index: int,
        segment_length: float,
        ceiling_joist_top_z: float,
        roof_overhang: float,
        false_plate_end_offset: float,
        false_plate_width: float,
        false_plate_depth: float,
    ) -> FramingMemberDatum:
        counter = segment_index + 1
        run_min = segment_index * segment_length
        if face == "front":
            size = (segment_length, false_plate_width, false_plate_depth)
            min_corner = (
                run_min,
                roof_overhang - false_plate_end_offset - false_plate_width,
                ceiling_joist_top_z,
            )
            axis: AxisName = "x"
        elif face == "rear":
            size = (segment_length, false_plate_width, false_plate_depth)
            min_corner = (
                run_min,
                -self.depth - roof_overhang + false_plate_end_offset,
                ceiling_joist_top_z,
            )
            axis = "x"
        else:
            raise ValueError(f"False plates are only defined on front/rear faces: {face}")

        return FramingMemberDatum(
            component_name=f"false_plate_{face}_{counter}",
            role="false_plate",
            face=face,
            index=counter,
            axis=axis,
            size=size,
            min_corner=min_corner,
            metadata_extra={
                "ceiling_joist_top_z": ceiling_joist_top_z,
                "false_plate_end_offset": false_plate_end_offset,
            },
        )

    def girt(
        self,
        face: WallFace,
        story: int,
        segment_index: int,
        segment_length: float,
        floor_height: float,
        joist_height: float,
        girt_width: float,
        girt_depth: float,
        start_extension: float = 0.0,
        end_extension: float = 0.0,
    ) -> FramingMemberDatum:
        counter = segment_index + 1
        run_min = segment_index * segment_length
        run_max = (segment_index + 1) * segment_length
        run_length = run_max - run_min + start_extension + end_extension
        if face == "front":
            size = (run_length, girt_width, girt_depth)
            min_corner = (
                run_min - start_extension,
                self.sill_width / 2.0 - girt_width,
                floor_height - joist_height - girt_depth,
            )
            axis: AxisName = "x"
        elif face == "rear":
            size = (run_length, girt_width, girt_depth)
            min_corner = (
                run_min - start_extension,
                -self.depth - self.sill_width / 2.0,
                floor_height - joist_height - girt_depth,
            )
            axis = "x"
        elif face == "left":
            size = (girt_width, run_length, girt_depth)
            min_corner = (-self.sill_width / 2.0, -run_max - end_extension, floor_height - girt_depth)
            axis = "y"
        else:
            size = (girt_width, run_length, girt_depth)
            min_corner = (
                self.width + self.sill_width / 2.0 - girt_width,
                -run_max - end_extension,
                floor_height - girt_depth,
            )
            axis = "y"

        return FramingMemberDatum(
            component_name=f"girt_{face}_story{story}_{counter}",
            role="girt",
            face=face,
            index=counter,
            story=story,
            axis=axis,
            size=size,
            min_corner=min_corner,
        )

    def bay_stud(
        self,
        face: WallFace,
        story: int,
        bay: int,
        side: str,
        station: float,
        bottom_z: float,
        length: float,
        stud_width: float,
        stud_depth: float,
    ) -> FramingMemberDatum:
        return self._vertical_wall_member(
            component_name=f"bay_stud_{face}_story{story}_bay{bay}_{side}",
            role="bay_stud",
            face=face,
            story=story,
            index=bay,
            station=station,
            bottom_z=bottom_z,
            length=length,
            stud_width=stud_width,
            stud_depth=stud_depth,
            metadata_extra={"bay": bay, "side": side, "station": station},
        )

    def cripple_stud(
        self,
        face: WallFace,
        story: int,
        bay: int,
        station: float,
        bottom_z: float,
        length: float,
        stud_width: float,
        stud_depth: float,
    ) -> FramingMemberDatum:
        return self._vertical_wall_member(
            component_name=f"cripple_stud_{face}_story{story}_bay{bay}",
            role="cripple_stud",
            face=face,
            story=story,
            index=bay,
            station=station,
            bottom_z=bottom_z,
            length=length,
            stud_width=stud_width,
            stud_depth=stud_depth,
            metadata_extra={"bay": bay, "station": station},
        )

    def stud(
        self,
        face: WallFace,
        story: int,
        section: int,
        wall: int,
        station: float,
        bottom_z: float,
        length: float,
        stud_width: float,
        stud_depth: float,
    ) -> FramingMemberDatum:
        return self._vertical_wall_member(
            component_name=f"stud_{face}_story{story}_section{section}_wall{wall}",
            role="stud",
            face=face,
            story=story,
            index=wall,
            station=station,
            bottom_z=bottom_z,
            length=length,
            stud_width=stud_width,
            stud_depth=stud_depth,
            metadata_extra={"section": section, "wall": wall, "station": station},
        )

    def _vertical_wall_member(
        self,
        component_name: str,
        role: str,
        face: WallFace,
        story: int,
        index: int,
        station: float,
        bottom_z: float,
        length: float,
        stud_width: float,
        stud_depth: float,
        metadata_extra: Dict[str, object],
    ) -> FramingMemberDatum:
        if face == "front":
            size = (stud_width, stud_depth, length)
            min_corner = (station - stud_width / 2.0, self.sill_width / 2.0 - stud_depth, bottom_z)
            axis: AxisName = "x"
        elif face == "rear":
            size = (stud_width, stud_depth, length)
            min_corner = (station - stud_width / 2.0, -self.depth - self.sill_width / 2.0, bottom_z)
            axis = "x"
        elif face == "left":
            size = (stud_depth, stud_width, length)
            min_corner = (-self.sill_width / 2.0, -station - stud_width / 2.0, bottom_z)
            axis = "y"
        else:
            size = (stud_depth, stud_width, length)
            min_corner = (
                self.width + self.sill_width / 2.0 - stud_depth,
                -station - stud_width / 2.0,
                bottom_z,
            )
            axis = "y"

        return FramingMemberDatum(
            component_name=component_name,
            role=role,
            face=face,
            index=index,
            story=story,
            axis=axis,
            size=size,
            min_corner=min_corner,
            metadata_extra=metadata_extra,
        )

    def brace(
        self,
        face: WallFace,
        story: int,
        corner: CornerName,
        hand: str,
        lower_anchor: Point3,
        upper_anchor: Point3,
        brace_width: float,
        brace_depth: float,
        post_mortise_tier: str,
        lower_receiver_role: str,
        lower_receiver_id: str,
        post_id: str,
        crossed_studs: Tuple[str, ...] = (),
    ) -> FramingBraceDatum:
        dx = upper_anchor[0] - lower_anchor[0]
        dy = upper_anchor[1] - lower_anchor[1]
        dz = upper_anchor[2] - lower_anchor[2]
        horizontal_run = math.hypot(dx, dy)
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        pitch = math.degrees(math.atan2(dz, horizontal_run))
        yaw = math.degrees(math.atan2(dy, dx))
        local_transform = Transform(
            translation=lower_anchor,
            rotations=(
                Rotation((0.0, 1.0, 0.0), -pitch),
                Rotation((0.0, 0.0, 1.0), yaw),
            ),
        )
        return FramingBraceDatum(
            component_name=f"brace_{corner}_{face}_story{story}_{post_mortise_tier}",
            role="brace",
            face=face,
            story=story,
            corner=corner,
            hand=hand,
            size=(length, brace_depth, brace_width),
            local_transform=local_transform,
            lower_anchor=lower_anchor,
            upper_anchor=upper_anchor,
            angle_degrees=pitch,
            length=length,
            post_mortise_tier=post_mortise_tier,
            lower_receiver_role=lower_receiver_role,
            lower_receiver_id=lower_receiver_id,
            post_id=post_id,
            crossed_studs=crossed_studs,
        )

    def _wall_length(self, face: WallFace) -> float:
        return self.width if face in ("front", "rear") else self.depth

    def post(self, corner: CornerName, floor_height: float, post_height: float) -> FramingMemberDatum:
        if corner.endswith("right"):
            x = self.width + self.sill_width / 2.0 - self.post_width
        else:
            x = -self.sill_width / 2.0
        if corner.startswith("rear"):
            y = -self.depth - self.sill_width / 2.0
        else:
            y = self.sill_width / 2.0 - self.post_depth
        min_corner = (
            x,
            y,
            floor_height - self.post_tenon_depth,
        )
        return FramingMemberDatum(
            component_name=f"post_{corner}",
            role="post",
            corner=corner,
            size=(self.post_width, self.post_depth, post_height),
            min_corner=min_corner,
            story=1,
        )
