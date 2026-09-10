"""Framing placement datums in the cornerstone coordinate convention."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Optional, Tuple


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
        return {
            "component_name": self.component_name,
            "framing_datums": {
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
    ) -> FramingMemberDatum:
        return FramingMemberDatum(
            component_name=f"joist_story{story}_{index}",
            role="joist",
            index=index,
            story=story,
            axis="y",
            size=(joist_width, joist_length, joist_height),
            min_corner=(center_x - joist_width / 2.0, y_min, floor_height - joist_height),
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
    ) -> FramingMemberDatum:
        counter = segment_index + 1
        run_min = segment_index * segment_length
        run_max = (segment_index + 1) * segment_length
        run_length = run_max - run_min
        if face == "front":
            size = (run_length, girt_width, girt_depth)
            min_corner = (
                run_min,
                self.sill_width / 2.0 - girt_width,
                floor_height - joist_height - girt_depth,
            )
            axis: AxisName = "x"
        elif face == "rear":
            size = (run_length, girt_width, girt_depth)
            min_corner = (
                run_min,
                -self.depth - self.sill_width / 2.0,
                floor_height - joist_height - girt_depth,
            )
            axis = "x"
        elif face == "left":
            size = (girt_width, run_length, girt_depth)
            min_corner = (-self.sill_width / 2.0, -run_max, floor_height - girt_depth)
            axis = "y"
        else:
            size = (girt_width, run_length, girt_depth)
            min_corner = (self.width + self.sill_width / 2.0 - girt_width, -run_max, floor_height - girt_depth)
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
