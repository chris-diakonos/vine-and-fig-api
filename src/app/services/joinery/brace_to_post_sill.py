"""Angled brace tenons and receiving post/sill mortises."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

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
    brace_width: float,
    params: BraceToPostSillParams | None = None,
) -> Dict[str, List[GeometryOperation]]:
    """Return brace-local operations for the brace, post, and lower receiver.

    The returned post and lower-receiver cutters are still in brace-local
    coordinates; framing handlers transform them into each receiver's local
    coordinate system.
    """
    params = params or default_brace_to_post_sill_params()
    lower_tenon = _brace_local_prism(
        -params.tenon_length,
        params.tenon_overlap,
        -params.tenon_thickness / 2.0,
        params.tenon_thickness / 2.0,
        -brace_width / 2.0,
        brace_width / 2.0,
    )
    upper_tenon = _brace_local_prism(
        brace_length - params.tenon_overlap,
        brace_length + params.tenon_length,
        -params.tenon_thickness / 2.0,
        params.tenon_thickness / 2.0,
        -brace_width / 2.0,
        brace_width / 2.0,
    )
    lower_mortise = _brace_local_prism(
        -params.tenon_length - params.mortise_extra_depth,
        params.mortise_overlap,
        -(params.tenon_thickness + params.mortise_clearance) / 2.0,
        (params.tenon_thickness + params.mortise_clearance) / 2.0,
        -(brace_width + params.mortise_clearance) / 2.0,
        (brace_width + params.mortise_clearance) / 2.0,
    )
    upper_mortise = _brace_local_prism(
        brace_length - params.mortise_overlap,
        brace_length + params.tenon_length + params.mortise_extra_depth,
        -(params.tenon_thickness + params.mortise_clearance) / 2.0,
        (params.tenon_thickness + params.mortise_clearance) / 2.0,
        -(brace_width + params.mortise_clearance) / 2.0,
        (brace_width + params.mortise_clearance) / 2.0,
    )
    return {
        "brace": [
            GeometryOperation(brace_id, "fuse", lower_tenon),
            GeometryOperation(brace_id, "fuse", upper_tenon),
        ],
        "post": [GeometryOperation(post_id, "cut", upper_mortise)],
        "lower_receiver": [GeometryOperation(lower_receiver_id, "cut", lower_mortise)],
    }


def _brace_local_prism(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float):
    return box_at((x1 - x0, y1 - y0, z1 - z0), (x0, y0, z0))
