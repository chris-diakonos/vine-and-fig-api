"""Through-tenon post-to-girt joinery based on the drop-girt reference."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

from app.services.joinery.base import GeometryOperation, box_at
from app.services.joinery.config import joinery_defaults


GirtAxis = Literal["x", "y"]
GirtEnd = Literal["min", "max"]


@dataclass(frozen=True)
class PostToGirtParams:
    tenon_thickness: float
    tenon_height: float
    mortise_clearance: float
    through_clearance: float


def default_post_to_girt_params() -> PostToGirtParams:
    return PostToGirtParams(**joinery_defaults("post_to_girt"))


def post_to_girt_operations(
    girt_id: str,
    post_id: str,
    girt_size: Tuple[float, float, float],
    post_size: Tuple[float, float, float],
    axis: GirtAxis,
    girt_end: GirtEnd,
    mortise_center: Tuple[float, float],
    params: Optional[PostToGirtParams] = None,
) -> List[GeometryOperation]:
    """Return operations for a girt through-tenon and matching post mortise."""
    params = params or default_post_to_girt_params()
    tenon_length = post_size[0] if axis == "x" else post_size[1]
    tenon = _girt_tenon(girt_size, axis, girt_end, tenon_length, params)
    mortise = _post_mortise(post_size, axis, mortise_center, params)
    return [
        GeometryOperation(post_id, "cut", mortise),
        GeometryOperation(girt_id, "fuse", tenon),
    ]


def _girt_tenon(
    girt_size: Tuple[float, float, float],
    axis: GirtAxis,
    girt_end: GirtEnd,
    tenon_length: float,
    params: PostToGirtParams,
):
    girt_x, girt_y, girt_z = girt_size
    tenon_height = min(params.tenon_height, girt_z)
    z0 = (girt_z - tenon_height) / 2.0
    if axis == "x":
        y0 = (girt_y - params.tenon_thickness) / 2.0
        x0 = -tenon_length if girt_end == "min" else girt_x
        return box_at((tenon_length, params.tenon_thickness, tenon_height), (x0, y0, z0))

    x0 = (girt_x - params.tenon_thickness) / 2.0
    y0 = -tenon_length if girt_end == "min" else girt_y
    return box_at((params.tenon_thickness, tenon_length, tenon_height), (x0, y0, z0))


def _post_mortise(
    post_size: Tuple[float, float, float],
    axis: GirtAxis,
    mortise_center: Tuple[float, float],
    params: PostToGirtParams,
):
    post_x, post_y, _ = post_size
    thickness = params.tenon_thickness + params.mortise_clearance
    height = params.tenon_height + params.mortise_clearance
    through_extra = params.through_clearance
    cross_center, z_center = mortise_center
    if axis == "x":
        return box_at(
            (post_x + through_extra, thickness, height),
            (-through_extra / 2.0, cross_center - thickness / 2.0, z_center - height / 2.0),
        )
    return box_at(
        (thickness, post_y + through_extra, height),
        (cross_center - thickness / 2.0, -through_extra / 2.0, z_center - height / 2.0),
    )
