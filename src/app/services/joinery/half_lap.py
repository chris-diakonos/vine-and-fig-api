"""Half-lap and bearing-notch helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.joinery.base import GeometryOperation, box_at
from app.services.joinery.config import joinery_defaults


@dataclass(frozen=True)
class HalfLapParams:
    length: float
    depth: float
    width: float


def upper_half_lap(member_id: str, x0: float, params: HalfLapParams, z_top: float) -> GeometryOperation:
    cutter = box_at(
        (params.length, params.width, params.depth),
        (x0, -params.width / 2.0, z_top - params.depth),
    )
    return GeometryOperation(member_id, "cut", cutter)


def lower_half_lap(member_id: str, x0: float, params: HalfLapParams, z_bottom: float) -> GeometryOperation:
    cutter = box_at(
        (params.length, params.width, params.depth),
        (x0, -params.width / 2.0, z_bottom),
    )
    return GeometryOperation(member_id, "cut", cutter)


@dataclass(frozen=True)
class BearingNotchParams:
    plate_width: float
    plate_height: float
    notch_depth: float
    clearance: float


def default_bearing_notch_params() -> BearingNotchParams:
    return BearingNotchParams(**joinery_defaults("bearing_notch"))


def joist_bearing_notch(
    member_id: str,
    plate_x0: float,
    joist_y0: float,
    joist_thickness: float,
    joist_bottom_z: float,
    params: Optional[BearingNotchParams] = None,
) -> GeometryOperation:
    params = params or default_bearing_notch_params()
    cutter = box_at(
        (
            params.plate_width + params.clearance,
            joist_thickness + params.clearance,
            params.notch_depth + params.clearance,
        ),
        (
            plate_x0 - params.clearance / 2.0,
            joist_y0 - params.clearance / 2.0,
            joist_bottom_z - params.clearance / 2.0,
        ),
    )
    return GeometryOperation(member_id, "cut", cutter)
