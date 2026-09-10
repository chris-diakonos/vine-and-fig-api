"""Housed dovetail joist-to-sill joinery."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cadquery as cq

from app.services.joinery.base import GeometryOperation
from app.services.joinery.config import joinery_defaults


@dataclass(frozen=True)
class JoistToSillParams:
    profile_height: float
    bottom_width: float
    profile_angle: float
    male_insertion_depth: float
    female_insertion_depth: float
    cutter_angle: float
    side_clearance: float
    vertical_clearance: float

    @property
    def top_width(self) -> float:
        return self.bottom_width + 2.0 * self.profile_height * math.tan(math.radians(self.profile_angle))


def default_joist_to_sill_params() -> JoistToSillParams:
    return JoistToSillParams(**joinery_defaults("joist_to_sill"))


def joist_to_sill_operations(
    joist_id: str,
    sill_id: str,
    joist_end_y: float,
    joist_top_z: float,
    sill_socket_center: Tuple[float, float],
    sill_top_z: float,
    direction: int,
    params: Optional[JoistToSillParams] = None,
) -> List[GeometryOperation]:
    """Return operations for a joist tail housed into a sill socket."""
    params = params or default_joist_to_sill_params()
    tail = _oriented_tail(
        params.profile_height,
        params.male_insertion_depth,
        params.top_width,
        params.bottom_width,
        params.cutter_angle,
        direction,
    ).translate((0.0, joist_end_y, joist_top_z))
    socket = _oriented_tail(
        params.profile_height + params.vertical_clearance,
        params.female_insertion_depth,
        params.top_width + 2.0 * params.side_clearance,
        params.bottom_width + 2.0 * params.side_clearance,
        params.cutter_angle,
        direction,
    ).translate((sill_socket_center[0], sill_socket_center[1], sill_top_z))
    return [
        GeometryOperation(sill_id, "cut", socket),
        GeometryOperation(joist_id, "fuse", tail),
    ]


def _oriented_tail(
    height: float,
    depth: float,
    top_width: float,
    bottom_width: float,
    cutter_angle: float,
    direction: int,
) -> cq.Workplane:
    tail = _housed_dovetail_tail(height, depth, top_width, bottom_width, cutter_angle)
    if direction < 0:
        tail = tail.rotate((0, 0, 0), (0, 0, 1), 180.0)
    return tail


def _housed_dovetail_tail(
    height: float,
    depth: float,
    top_width: float,
    bottom_width: float,
    cutter_angle: float,
) -> cq.Workplane:
    draft = depth * math.tan(math.radians(cutter_angle))
    outer_plane = cq.Plane(origin=(0, 0, 0), xDir=(1, 0, 0), normal=(0, -1, 0))
    inner_plane = cq.Plane(origin=(0, depth, 0), xDir=(1, 0, 0), normal=(0, -1, 0))
    solid = cq.Solid.makeLoft(
        [
            _rounded_tail_wire(outer_plane, top_width, bottom_width, height),
            _rounded_tail_wire(inner_plane, top_width + 2.0 * draft, bottom_width + 2.0 * draft, height),
        ],
        ruled=True,
    )
    return cq.Workplane("XY").add(solid)


def _rounded_tail_wire(plane: cq.Plane, top_width: float, bottom_width: float, height: float) -> cq.Wire:
    radius = bottom_width / 2.0
    return (
        cq.Workplane(plane)
        .moveTo(-top_width / 2.0, 0.0)
        .lineTo(top_width / 2.0, 0.0)
        .lineTo(bottom_width / 2.0, -height + radius)
        .threePointArc((0.0, -height), (-bottom_width / 2.0, -height + radius))
        .close()
        .val()
    )
