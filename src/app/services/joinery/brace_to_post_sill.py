"""Angled brace tenons and receiving post/sill mortises."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Tuple

import cadquery as cq

from app.services.joinery.base import GeometryOperation, box_at
from app.services.joinery.config import joinery_defaults


Point3 = Tuple[float, float, float]


@dataclass(frozen=True)
class BraceToPostSillParams:
    tenon_length: float
    tenon_thickness: float
    tenon_overlap: float
    mortise_clearance: float
    mortise_extra_depth: float
    mortise_overlap: float


def default_brace_to_post_sill_params() -> BraceToPostSillParams:
    return BraceToPostSillParams(**joinery_defaults("brace_to_post_sill"))


def brace_to_post_sill_local_operations(
    brace_id: str,
    post_id: str,
    lower_receiver_id: str,
    brace_length: float,
    brace_thickness: float,
    brace_depth: float,
    brace_angle_degrees: float,
    params: BraceToPostSillParams | None = None,
) -> Dict[str, List[GeometryOperation]]:
    """Return brace-local operations for the brace, post, and lower receiver.

    The returned post and lower-receiver cutters are still in brace-local
    coordinates; framing handlers transform them into each receiver's local
    coordinate system.
    """
    params = params or default_brace_to_post_sill_params()
    shoulders = brace_shoulder_points(brace_length, brace_depth, brace_angle_degrees)
    lower_run = abs(shoulders["lower_x_bottom"] - shoulders["lower_x_top"])
    upper_run = abs(shoulders["upper_x_top"] - shoulders["upper_x_bottom"])
    lower_tenon_root_x = shoulders["lower_x_bottom"]
    upper_tenon_root_x = shoulders["upper_x_bottom"]
    tenon_y0 = -params.tenon_thickness / 2.0
    tenon_y1 = params.tenon_thickness / 2.0
    tenon_z0 = -brace_depth / 2.0
    tenon_z1 = brace_depth / 2.0
    mortise_y0 = tenon_y0 - params.mortise_clearance / 2.0
    mortise_y1 = tenon_y1 + params.mortise_clearance / 2.0
    mortise_z0 = tenon_z0 - params.mortise_clearance / 2.0
    mortise_z1 = tenon_z1 + params.mortise_clearance / 2.0

    lower_tenon = _brace_local_prism(
        lower_tenon_root_x - lower_run,
        lower_tenon_root_x + params.tenon_overlap,
        tenon_y0,
        tenon_y1,
        tenon_z0,
        tenon_z1,
    )
    upper_tenon = _brace_local_prism(
        upper_tenon_root_x - params.tenon_overlap,
        upper_tenon_root_x + upper_run,
        tenon_y0,
        tenon_y1,
        tenon_z0,
        tenon_z1,
    )
    lower_mortise = _brace_local_prism(
        lower_tenon_root_x - lower_run - params.mortise_extra_depth,
        lower_tenon_root_x + params.mortise_overlap,
        mortise_y0,
        mortise_y1,
        mortise_z0,
        mortise_z1,
    )
    upper_mortise = _brace_local_prism(
        upper_tenon_root_x - params.mortise_overlap,
        upper_tenon_root_x + upper_run + params.mortise_extra_depth,
        mortise_y0,
        mortise_y1,
        mortise_z0,
        mortise_z1,
    )
    return {
        "brace": [
            GeometryOperation(brace_id, "fuse", lower_tenon),
            GeometryOperation(brace_id, "fuse", upper_tenon),
        ],
        "post": [GeometryOperation(post_id, "cut", upper_mortise)],
        "lower_receiver": [GeometryOperation(lower_receiver_id, "cut", lower_mortise)],
    }


def angled_brace_body(brace_length: float, brace_thickness: float, brace_depth: float, brace_angle_degrees: float):
    """Return the notebook-derived brace blank with sloped post/sill shoulders."""

    shoulders = brace_shoulder_points(brace_length, brace_depth, brace_angle_degrees)
    z_bottom = -brace_depth / 2.0
    z_top = brace_depth / 2.0
    return (
        cq.Workplane("XZ")
        .moveTo(shoulders["lower_x_bottom"], z_bottom)
        .lineTo(shoulders["lower_x_top"], z_top)
        .lineTo(shoulders["upper_x_top"], z_top)
        .lineTo(shoulders["upper_x_bottom"], z_bottom)
        .close()
        .extrude(brace_thickness / 2.0, both=True)
    )


def brace_shoulder_points(brace_length: float, brace_depth: float, brace_angle_degrees: float) -> Dict[str, float]:
    angle = math.radians(brace_angle_degrees)
    tangent = math.tan(angle)
    if abs(tangent) < 1e-9:
        raise ValueError("Brace angle is too shallow for shoulder geometry")
    z_bottom = -brace_depth / 2.0
    z_top = brace_depth / 2.0
    return {
        "lower_x_bottom": -z_bottom / tangent,
        "lower_x_top": -z_top / tangent,
        "upper_x_bottom": brace_length + z_bottom * tangent,
        "upper_x_top": brace_length + z_top * tangent,
    }


def _brace_local_prism(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float):
    return box_at((x1 - x0, y1 - y0, z1 - z0), (x0, y0, z0))
