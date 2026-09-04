"""
Cornerstone coordinate helpers and legacy CadQuery compatibility mappings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Tuple

from app.models.floorplan import Dimensions
from app.services.scene_graph import Transform


WallFace = Literal["front", "rear", "left", "right"]


@dataclass(frozen=True)
class CornerstonePoint:
    """A point in the global cornerstone coordinate system."""

    x: float
    y: float
    z: float

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass(frozen=True)
class WindowPlacement:
    """Window placement expressed in cornerstone and legacy CadQuery terms."""

    wall: WallFace
    position: float
    opening_width: float
    sill_z: float
    cornerstone_origin: CornerstonePoint
    legacy_transform: Transform

    def as_dict(self) -> Dict[str, object]:
        return {
            "wall": self.wall,
            "position": self.position,
            "opening_width": self.opening_width,
            "sill_z": self.sill_z,
            "cornerstone_origin": list(self.cornerstone_origin.as_tuple()),
            "legacy_transform": self.legacy_transform.as_dict(),
        }


def window_placement_for_wall(
    wall: WallFace,
    position: float,
    sill_z: float,
    opening_width: float,
    dimensions: Dimensions,
) -> WindowPlacement:
    """
    Place a canonical local window on a wall.

    New code reasons from a cornerstone coordinate system with positive building
    depth. The returned transform projects that placement into the current
    legacy CadQuery convention used by the existing builders.
    """

    half_width = opening_width / 2

    if wall == "front":
        cornerstone_origin = CornerstonePoint(position - half_width, 0.0, sill_z)
        legacy_transform = Transform.translate(position - half_width, 0.0, sill_z)
    elif wall == "rear":
        cornerstone_origin = CornerstonePoint(position + half_width, dimensions.right, sill_z)
        legacy_transform = Transform.rotate_z(
            180.0,
            translation=(position + half_width, -dimensions.right, sill_z),
        )
    elif wall == "left":
        cornerstone_origin = CornerstonePoint(0.0, position - half_width, sill_z)
        legacy_transform = Transform.rotate_z(
            -90.0,
            translation=(0.0, -position + half_width, sill_z),
        )
    elif wall == "right":
        cornerstone_origin = CornerstonePoint(dimensions.front, position + half_width, sill_z)
        legacy_transform = Transform.rotate_z(
            90.0,
            translation=(dimensions.front, -position - half_width, sill_z),
        )
    else:
        raise ValueError(f"Unsupported wall face: {wall}")

    return WindowPlacement(
        wall=wall,
        position=position,
        opening_width=opening_width,
        sill_z=sill_z,
        cornerstone_origin=cornerstone_origin,
        legacy_transform=legacy_transform,
    )
