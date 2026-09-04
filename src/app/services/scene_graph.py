"""
Lightweight scene graph primitives for hierarchical CAD placement.

This is intentionally smaller than a full CAD IR. It gives the procedural
generator stable semantic paths, local transforms, and projection into the
existing CadQuery assembly/export pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import cadquery as cq


Matrix4 = Tuple[
    Tuple[float, float, float, float],
    Tuple[float, float, float, float],
    Tuple[float, float, float, float],
    Tuple[float, float, float, float],
]


IDENTITY_MATRIX: Matrix4 = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


@dataclass(frozen=True)
class Rotation:
    """A rotation around one of the global/local principal axes."""

    axis: Tuple[float, float, float]
    angle_degrees: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "axis": list(self.axis),
            "angle_degrees": self.angle_degrees,
        }


@dataclass(frozen=True)
class Transform:
    """Repo-owned transform that can be projected into CadQuery operations."""

    translation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotations: Tuple[Rotation, ...] = ()

    @staticmethod
    def identity() -> "Transform":
        return Transform()

    @staticmethod
    def translate(x: float, y: float, z: float) -> "Transform":
        return Transform(translation=(x, y, z))

    @staticmethod
    def rotate_z(angle_degrees: float, translation: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> "Transform":
        return Transform(translation=translation, rotations=(Rotation((0.0, 0.0, 1.0), angle_degrees),))

    def apply_to_workplane(self, workplane: cq.Workplane) -> cq.Workplane:
        result = workplane
        for rotation in self.rotations:
            result = result.rotate((0, 0, 0), rotation.axis, rotation.angle_degrees)
        if self.translation != (0.0, 0.0, 0.0):
            result = result.translate(self.translation)
        return result

    def matrix(self) -> Matrix4:
        matrix = IDENTITY_MATRIX
        for rotation in self.rotations:
            matrix = _multiply_matrices(_rotation_matrix(rotation), matrix)
        return _multiply_matrices(_translation_matrix(self.translation), matrix)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "translation": list(self.translation),
            "rotations": [rotation.as_dict() for rotation in self.rotations],
        }


@dataclass
class Bounds:
    """Axis-aligned bounds in inches."""

    min: Tuple[float, float, float]
    max: Tuple[float, float, float]

    @property
    def size(self) -> Tuple[float, float, float]:
        return tuple(self.max[idx] - self.min[idx] for idx in range(3))  # type: ignore[return-value]

    def union(self, other: "Bounds") -> "Bounds":
        return Bounds(
            min=tuple(min(self.min[idx], other.min[idx]) for idx in range(3)),  # type: ignore[arg-type]
            max=tuple(max(self.max[idx], other.max[idx]) for idx in range(3)),  # type: ignore[arg-type]
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "min": list(self.min),
            "max": list(self.max),
            "size": list(self.size),
        }


@dataclass
class SceneNode:
    """A semantic occurrence in a generated CAD scene."""

    name: str
    node_type: str
    role: str
    local_transform: Transform = field(default_factory=Transform.identity)
    geometry: Optional[cq.Workplane] = None
    color: Optional[cq.Color] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List["SceneNode"] = field(default_factory=list)
    parent: Optional["SceneNode"] = field(default=None, repr=False, compare=False)

    def add_child(self, child: "SceneNode") -> "SceneNode":
        child.parent = self
        self.children.append(child)
        return child

    @property
    def semantic_path(self) -> str:
        parts = []
        node: Optional[SceneNode] = self
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return "/".join(reversed(parts))

    def iter_nodes(self) -> Iterable["SceneNode"]:
        yield self
        for child in self.children:
            yield from child.iter_nodes()

    def transform_chain_to_root(self) -> List[Transform]:
        chain: List[Transform] = []
        node: Optional[SceneNode] = self
        while node is not None:
            chain.append(node.local_transform)
            node = node.parent
        return chain

    def world_matrix(self) -> Matrix4:
        matrix = IDENTITY_MATRIX
        for transform in reversed(self.transform_chain_to_root()):
            matrix = _multiply_matrices(matrix, transform.matrix())
        return matrix

    def projected_geometry(self) -> Optional[cq.Workplane]:
        if self.geometry is None:
            return None

        result = self.geometry
        for transform in self.transform_chain_to_root():
            result = transform.apply_to_workplane(result)
        return result


def project_scene_to_assembly(scene: SceneNode, assembly: Optional[cq.Assembly] = None) -> cq.Assembly:
    """Project geometry-bearing scene nodes into a flat CadQuery assembly."""

    target = assembly or cq.Assembly()
    for node in scene.iter_nodes():
        geometry = node.projected_geometry()
        if geometry is None:
            continue
        component_name = node.metadata.get("component_name", node.semantic_path)
        target.add(
            geometry,
            name=component_name,
            color=node.color if node.color is not None else cq.Color(0.8, 0.7, 0.6),
        )
    return target


def collect_component_metadata(scene: SceneNode) -> List[Dict[str, Any]]:
    """Collect serializable scene metadata for inspection artifacts."""

    components: List[Dict[str, Any]] = []
    for node in scene.iter_nodes():
        local_bounds = bounds_for_workplane(node.geometry) if node.geometry is not None else None
        projected = node.projected_geometry()
        world_bounds = bounds_for_workplane(projected) if projected is not None else None
        components.append(
            {
                "semantic_path": node.semantic_path,
                "name": node.name,
                "type": node.node_type,
                "role": node.role,
                "parent": node.parent.semantic_path if node.parent is not None else None,
                "component_name": node.metadata.get("component_name"),
                "local_transform": node.local_transform.as_dict(),
                "world_matrix": node.world_matrix(),
                "local_bounds": local_bounds.as_dict() if local_bounds else None,
                "world_bounds": world_bounds.as_dict() if world_bounds else None,
                "metadata": _serializable_metadata(node.metadata),
            }
        )
    return components


def aggregate_local_bounds(node: SceneNode) -> Optional[Bounds]:
    """Return local aggregate bounds for geometry below a node."""

    aggregate: Optional[Bounds] = None
    for child in node.iter_nodes():
        if child.geometry is None:
            continue
        bounds = bounds_for_workplane(child.geometry)
        if bounds is None:
            continue
        aggregate = bounds if aggregate is None else aggregate.union(bounds)
    return aggregate


def bounds_for_workplane(workplane: Optional[cq.Workplane]) -> Optional[Bounds]:
    if workplane is None:
        return None
    try:
        value = workplane.val()
        if value is None:
            return None
        box = value.BoundingBox()
        return Bounds(
            min=(box.xmin, box.ymin, box.zmin),
            max=(box.xmax, box.ymax, box.zmax),
        )
    except Exception:
        return None


def _translation_matrix(translation: Tuple[float, float, float]) -> Matrix4:
    x, y, z = translation
    return (
        (1.0, 0.0, 0.0, x),
        (0.0, 1.0, 0.0, y),
        (0.0, 0.0, 1.0, z),
        (0.0, 0.0, 0.0, 1.0),
    )


def _rotation_matrix(rotation: Rotation) -> Matrix4:
    x, y, z = rotation.axis
    angle = math.radians(rotation.angle_degrees)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    if (x, y, z) == (1.0, 0.0, 0.0):
        return (
            (1.0, 0.0, 0.0, 0.0),
            (0.0, cos_a, -sin_a, 0.0),
            (0.0, sin_a, cos_a, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    if (x, y, z) == (0.0, 1.0, 0.0):
        return (
            (cos_a, 0.0, sin_a, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (-sin_a, 0.0, cos_a, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    if (x, y, z) == (0.0, 0.0, 1.0):
        return (
            (cos_a, -sin_a, 0.0, 0.0),
            (sin_a, cos_a, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    raise ValueError(f"Unsupported rotation axis: {rotation.axis}")


def _multiply_matrices(left: Matrix4, right: Matrix4) -> Matrix4:
    rows: List[Tuple[float, float, float, float]] = []
    for row in range(4):
        values = []
        for col in range(4):
            values.append(sum(left[row][idx] * right[idx][col] for idx in range(4)))
        rows.append(tuple(values))  # type: ignore[arg-type]
    return tuple(rows)  # type: ignore[return-value]


def _serializable_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in metadata.items():
        if key == "component_name":
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
        elif isinstance(value, dict):
            result[key] = _serializable_metadata(value)
        elif isinstance(value, (list, tuple)):
            result[key] = list(value)
    return result
