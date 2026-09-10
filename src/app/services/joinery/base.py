"""Core types and helpers for deterministic joinery compilation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Literal, Optional, Tuple

import cadquery as cq


OperationKind = Literal["cut", "fuse"]
Point3 = Tuple[float, float, float]


class JoineryError(ValueError):
    """Raised when a declared joint cannot be compiled."""


@dataclass(frozen=True)
class GeometryOperation:
    member_id: str
    operation: OperationKind
    shape: cq.Workplane
    joint_id: Optional[str] = None


@dataclass(frozen=True)
class JointSpec:
    id: str
    joint_type: str
    member_a: str
    member_b: str
    anchor: Any = None
    params: Dict[str, Any] = field(default_factory=dict)


def box_at(size: Point3, origin: Point3) -> cq.Workplane:
    """Return a box whose minimum corner is at origin."""

    solid = cq.Solid.makeBox(size[0], size[1], size[2], cq.Vector(*origin))
    return cq.Workplane("XY").add(solid)


def centered_box(size: Point3, center: Point3) -> cq.Workplane:
    origin = (
        center[0] - size[0] / 2.0,
        center[1] - size[1] / 2.0,
        center[2] - size[2] / 2.0,
    )
    return box_at(size, origin)


def cylinder_between(radius: float, height: float, center: Point3, axis: Point3) -> cq.Workplane:
    start = (
        center[0] - axis[0] * height / 2.0,
        center[1] - axis[1] * height / 2.0,
        center[2] - axis[2] * height / 2.0,
    )
    solid = cq.Solid.makeCylinder(radius, height, cq.Vector(*start), cq.Vector(*axis))
    return cq.Workplane("XY").add(solid)


def apply_operations(blank: cq.Workplane, operations: Iterable[GeometryOperation]) -> cq.Workplane:
    result = blank.val()
    for op in operations:
        tool = op.shape.val()
        if op.operation == "cut":
            result = result.cut(tool)
        elif op.operation == "fuse":
            result = result.fuse(tool)
        else:
            raise JoineryError(f"Unknown geometry operation: {op.operation}")
    return cq.Workplane("XY").add(result.clean())


def workplane_volume(workplane: cq.Workplane) -> float:
    return float(workplane.val().Volume())


def workplane_bounds(workplane: cq.Workplane) -> Tuple[Point3, Point3]:
    box = workplane.val().BoundingBox()
    return (box.xmin, box.ymin, box.zmin), (box.xmax, box.ymax, box.zmax)
