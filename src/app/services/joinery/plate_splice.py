"""Reciprocal half-lap plate splice with tenons, open mortises, and peg bores."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cadquery as cq

from app.services.joinery.base import GeometryOperation, apply_operations, box_at
from app.services.joinery.config import joinery_defaults
from app.services.joinery.half_lap import HalfLapParams, lower_half_lap, upper_half_lap
from app.services.joinery.peg_bore import PegBoreParams, peg_bore


@dataclass(frozen=True)
class PlateSpliceParams:
    plate_width: float
    plate_height: float
    lap_length: float
    tenon_width: float
    tenon_length: float
    mortise_clearance: float
    mortise_overlap: float
    peg_diameter: float
    peg_offset: float
    fixture_left_length: float
    fixture_right_length: float

    @property
    def lap_depth(self) -> float:
        return self.plate_height / 2.0

    @property
    def tenon_height(self) -> float:
        return self.lap_depth


def default_plate_splice_params() -> PlateSpliceParams:
    return PlateSpliceParams(**joinery_defaults("plate_splice"))


def plate_splice_params(overrides: Optional[dict] = None) -> PlateSpliceParams:
    values = joinery_defaults("plate_splice")
    if overrides:
        values.update(overrides)
    return PlateSpliceParams(**values)


def plate_splice_operations(
    left_member_id: str,
    right_member_id: str,
    params: Optional[PlateSpliceParams] = None,
) -> List[GeometryOperation]:
    params = params or default_plate_splice_params()
    lap_x0 = -params.lap_length / 2.0
    lap_x1 = params.lap_length / 2.0
    lap = HalfLapParams(params.lap_length, params.lap_depth, params.plate_width)

    right_tenon_x0 = lap_x0 - params.tenon_length
    left_tenon_x0 = lap_x1
    tenon_y0 = -params.tenon_width / 2.0

    right_tenon = box_at(
        (params.tenon_length, params.tenon_width, params.tenon_height),
        (right_tenon_x0, tenon_y0, params.plate_height - params.tenon_height),
    )
    left_tenon = box_at(
        (params.tenon_length, params.tenon_width, params.tenon_height),
        (left_tenon_x0, tenon_y0, 0.0),
    )

    mortise_width = params.tenon_width + params.mortise_clearance
    left_open_mortise = box_at(
        (
            params.tenon_length + params.mortise_overlap + params.mortise_clearance / 2.0,
            mortise_width,
            params.tenon_height + params.mortise_clearance,
        ),
        (
            right_tenon_x0 - params.mortise_clearance / 2.0,
            -mortise_width / 2.0,
            params.plate_height - params.tenon_height - params.mortise_clearance / 2.0,
        ),
    )
    right_open_mortise = box_at(
        (
            params.tenon_length + params.mortise_overlap + params.mortise_clearance / 2.0,
            mortise_width,
            params.tenon_height + params.mortise_clearance,
        ),
        (
            left_tenon_x0 - params.mortise_overlap,
            -mortise_width / 2.0,
            -params.mortise_clearance / 2.0,
        ),
    )

    bore_params = PegBoreParams(params.peg_diameter, joinery_defaults("peg_bore")["margin"])
    upper_bore_center = (
        lap_x0 - params.peg_offset,
        0.0,
        params.plate_height - params.tenon_height / 2.0,
    )
    lower_bore_center = (
        lap_x1 + params.peg_offset,
        0.0,
        params.tenon_height / 2.0,
    )
    bore_length = params.plate_width

    return [
        upper_half_lap(left_member_id, lap_x0, lap, params.plate_height),
        lower_half_lap(right_member_id, lap_x0, lap, 0.0),
        GeometryOperation(right_member_id, "fuse", right_tenon),
        GeometryOperation(left_member_id, "fuse", left_tenon),
        GeometryOperation(left_member_id, "cut", left_open_mortise),
        GeometryOperation(right_member_id, "cut", right_open_mortise),
        peg_bore(left_member_id, upper_bore_center, (0.0, 1.0, 0.0), bore_length, bore_params),
        peg_bore(left_member_id, lower_bore_center, (0.0, 1.0, 0.0), bore_length, bore_params),
        peg_bore(right_member_id, upper_bore_center, (0.0, 1.0, 0.0), bore_length, bore_params),
        peg_bore(right_member_id, lower_bore_center, (0.0, 1.0, 0.0), bore_length, bore_params),
    ]


def plate_splice_fixture(
    left_length: Optional[float] = None,
    right_length: Optional[float] = None,
    params: Optional[PlateSpliceParams] = None,
) -> Tuple[cq.Workplane, cq.Workplane]:
    params = params or default_plate_splice_params()
    left_length = left_length if left_length is not None else params.fixture_left_length
    right_length = right_length if right_length is not None else params.fixture_right_length
    left_blank = box_at(
        (left_length + params.lap_length / 2.0, params.plate_width, params.plate_height),
        (-left_length, -params.plate_width / 2.0, 0.0),
    )
    right_blank = box_at(
        (right_length + params.lap_length / 2.0, params.plate_width, params.plate_height),
        (-params.lap_length / 2.0, -params.plate_width / 2.0, 0.0),
    )

    operations = plate_splice_operations("left", "right", params)
    left = apply_operations(left_blank, [op for op in operations if op.member_id == "left"])
    right = apply_operations(right_blank, [op for op in operations if op.member_id == "right"])
    return left, right
