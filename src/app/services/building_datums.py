"""Shared placement datums derived from migrated framing scene metadata."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.models.floorplan import Dimensions
from app.services.coordinate_system import CornerstonePoint, WindowPlacement, window_placement_for_wall
from app.services.scene_graph import Transform

BoundsDict = Dict[str, List[float]]


@dataclass(frozen=True)
class FloorSurfaceDatum:
    floor_index: int
    top_z: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    source: str

    @property
    def length_x(self) -> float:
        return self.x_max - self.x_min

    @property
    def length_y(self) -> float:
        return self.y_max - self.y_min


@dataclass(frozen=True)
class BuildingDatumContext:
    """Placement anchors shared by non-framing builders."""

    dimensions: Dimensions
    wall_exterior_planes: Dict[str, float]
    floor_surfaces: Dict[int, FloorSurfaceDatum]
    ceiling_joist_bounds: Optional[BoundsDict]
    source: str = "framing_datums"

    @staticmethod
    def from_framing_components(
        components: Iterable[Dict[str, Any]],
        dimensions: Dimensions,
        floor_heights: Optional[List[float]] = None,
    ) -> "BuildingDatumContext":
        components_list = list(components)
        wall_planes = _wall_exterior_planes(components_list, dimensions)
        floor_surfaces = _floor_surfaces(components_list, dimensions, floor_heights or [])
        ceiling_bounds = _aggregate_role_bounds(
            components_list,
            role="joist",
            metadata_filter=lambda datums: datums.get("joist_kind") == "ceiling",
        )
        return BuildingDatumContext(
            dimensions=dimensions,
            wall_exterior_planes=wall_planes,
            floor_surfaces=floor_surfaces,
            ceiling_joist_bounds=ceiling_bounds,
        )

    def wall_exterior_plane(self, face: str, fallback_stud_depth: float = 4.0) -> float:
        if face in self.wall_exterior_planes:
            return self.wall_exterior_planes[face]
        return _fallback_wall_plane(self.dimensions, face, fallback_stud_depth)

    def wall_length(self, face: str) -> float:
        return self.dimensions.front if face in ("front", "rear") else self.dimensions.left

    def wall_centerline(self, face: str) -> Tuple[float, float]:
        if face == "front":
            return (self.dimensions.front / 2.0, self.wall_exterior_plane(face))
        if face == "rear":
            return (self.dimensions.front / 2.0, self.wall_exterior_plane(face))
        if face == "left":
            return (self.wall_exterior_plane(face), -self.dimensions.left / 2.0)
        if face == "right":
            return (self.wall_exterior_plane(face), -self.dimensions.right / 2.0)
        raise ValueError(f"Unsupported wall face: {face}")

    def floor_surface(self, floor_index: int, fallback_top_z: float) -> FloorSurfaceDatum:
        if floor_index in self.floor_surfaces:
            return self.floor_surfaces[floor_index]
        return FloorSurfaceDatum(
            floor_index=floor_index,
            top_z=fallback_top_z,
            x_min=0.0,
            x_max=self.dimensions.front,
            y_min=-self.dimensions.left,
            y_max=0.0,
            source="legacy_dimensions",
        )

    def ceiling_joist_end_plane(self, face: str, fallback_stud_depth: float = 4.0) -> float:
        if self.ceiling_joist_bounds is None:
            return self.wall_exterior_plane(face, fallback_stud_depth)
        bounds = self.ceiling_joist_bounds
        if face == "front":
            return bounds["max"][1]
        if face == "rear":
            return bounds["min"][1]
        if face == "left":
            return bounds["min"][0]
        if face == "right":
            return bounds["max"][0]
        raise ValueError(f"Unsupported wall face: {face}")

    def window_placement_for_wall(
        self,
        wall: str,
        position: float,
        sill_z: float,
        opening_width: float,
    ) -> WindowPlacement:
        placement = window_placement_for_wall(wall, position, sill_z, opening_width, self.dimensions)
        half_width = opening_width / 2.0
        plane = self.wall_exterior_plane(wall)
        if wall == "front":
            transform = Transform.translate(position - half_width, plane, sill_z)
            origin = CornerstonePoint(position - half_width, plane, sill_z)
        elif wall == "rear":
            transform = Transform.rotate_z(180.0, translation=(position + half_width, plane, sill_z))
            origin = CornerstonePoint(position + half_width, -plane, sill_z)
        elif wall == "left":
            transform = Transform.rotate_z(-90.0, translation=(plane, -position + half_width, sill_z))
            origin = CornerstonePoint(plane, position - half_width, sill_z)
        elif wall == "right":
            transform = Transform.rotate_z(90.0, translation=(plane, -position - half_width, sill_z))
            origin = CornerstonePoint(plane, position + half_width, sill_z)
        else:
            return placement
        return WindowPlacement(wall, position, opening_width, sill_z, origin, transform)

    def door_transform(
        self,
        wall: str,
        position: float,
        width: float,
        thickness: float,
        sill_z: float,
    ) -> Transform:
        plane = self.wall_exterior_plane(wall)
        if wall in ("front", "rear"):
            return Transform.translate(position - width / 2.0, plane, sill_z)
        if wall == "left":
            return Transform.translate(plane, -position, sill_z)
        if wall == "right":
            return Transform.translate(plane, -position, sill_z)
        return Transform.translate(position - width / 2.0, thickness / 2.0, sill_z)


def _component_role(component: Dict[str, Any]) -> Optional[str]:
    metadata = component.get("metadata") or {}
    datums = metadata.get("framing_datums") or {}
    return datums.get("role") or component.get("role")


def _component_face(component: Dict[str, Any]) -> Optional[str]:
    metadata = component.get("metadata") or {}
    datums = metadata.get("framing_datums") or {}
    return datums.get("face")


def _component_story(component: Dict[str, Any]) -> Optional[int]:
    metadata = component.get("metadata") or {}
    datums = metadata.get("framing_datums") or {}
    story = datums.get("story")
    return int(story) if story is not None else None


def _wall_exterior_planes(components: List[Dict[str, Any]], dimensions: Dimensions) -> Dict[str, float]:
    wall_roles = {"sill", "post", "girt", "plate", "bay_stud", "cripple_stud", "stud"}
    planes: Dict[str, float] = {}
    for face in ("front", "rear", "left", "right"):
        face_bounds = [
            component["world_bounds"]
            for component in components
            if component.get("world_bounds")
            and _component_face(component) == face
            and _component_role(component) in wall_roles
        ]
        if not face_bounds:
            continue
        if face == "front":
            planes[face] = max(bounds["max"][1] for bounds in face_bounds)
        elif face == "rear":
            planes[face] = min(bounds["min"][1] for bounds in face_bounds)
        elif face == "left":
            planes[face] = min(bounds["min"][0] for bounds in face_bounds)
        elif face == "right":
            planes[face] = max(bounds["max"][0] for bounds in face_bounds)
    for face in ("front", "rear", "left", "right"):
        planes.setdefault(face, _fallback_wall_plane(dimensions, face, 4.0))
    return planes


def _floor_surfaces(
    components: List[Dict[str, Any]],
    dimensions: Dimensions,
    floor_heights: List[float],
) -> Dict[int, FloorSurfaceDatum]:
    surfaces: Dict[int, FloorSurfaceDatum] = {}
    for floor_index, fallback_height in enumerate(floor_heights):
        story = floor_index + 1
        joist_bounds = [
            component["world_bounds"]
            for component in components
            if component.get("world_bounds")
            and _component_role(component) == "joist"
            and _component_story(component) == story
        ]
        if not joist_bounds:
            continue
        surfaces[floor_index] = FloorSurfaceDatum(
            floor_index=floor_index,
            top_z=max(bounds["max"][2] for bounds in joist_bounds),
            x_min=min(bounds["min"][0] for bounds in joist_bounds),
            x_max=max(bounds["max"][0] for bounds in joist_bounds),
            y_min=min(bounds["min"][1] for bounds in joist_bounds),
            y_max=max(bounds["max"][1] for bounds in joist_bounds),
            source="framing_datums",
        )
    for floor_index, fallback_height in enumerate(floor_heights):
        surfaces.setdefault(
            floor_index,
            FloorSurfaceDatum(
                floor_index=floor_index,
                top_z=fallback_height,
                x_min=0.0,
                x_max=dimensions.front,
                y_min=-dimensions.left,
                y_max=0.0,
                source="legacy_dimensions",
            ),
        )
    return surfaces


def _aggregate_role_bounds(
    components: List[Dict[str, Any]],
    role: str,
    metadata_filter,
) -> Optional[BoundsDict]:
    matching = []
    for component in components:
        metadata = component.get("metadata") or {}
        datums = metadata.get("framing_datums") or {}
        if _component_role(component) == role and component.get("world_bounds") and metadata_filter(datums):
            matching.append(component["world_bounds"])
    if not matching:
        return None
    return {
        "min": [
            min(bounds["min"][axis] for bounds in matching)
            for axis in range(3)
        ],
        "max": [
            max(bounds["max"][axis] for bounds in matching)
            for axis in range(3)
        ],
        "size": [
            max(bounds["max"][axis] for bounds in matching) - min(bounds["min"][axis] for bounds in matching)
            for axis in range(3)
        ],
    }


def _fallback_wall_plane(dimensions: Dimensions, face: str, stud_depth: float) -> float:
    if face == "front":
        return stud_depth
    if face == "rear":
        return -dimensions.right - stud_depth
    if face == "left":
        return -stud_depth / 2.0
    if face == "right":
        return dimensions.front + stud_depth / 2.0
    raise ValueError(f"Unsupported wall face: {face}")
