"""Peg bore cutters for timber joinery."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from app.services.joinery.base import GeometryOperation, Point3, cylinder_between
from app.services.joinery.config import joinery_defaults


@dataclass(frozen=True)
class PegBoreParams:
    diameter: float
    margin: float


def default_peg_bore_params() -> PegBoreParams:
    return PegBoreParams(**joinery_defaults("peg_bore"))


def peg_bore(
    member_id: str,
    center: Point3,
    axis: Tuple[float, float, float],
    length: float,
    params: Optional[PegBoreParams] = None,
) -> GeometryOperation:
    params = params or default_peg_bore_params()
    cutter = cylinder_between(params.diameter / 2.0, length + 2.0 * params.margin, center, axis)
    return GeometryOperation(member_id, "cut", cutter)
