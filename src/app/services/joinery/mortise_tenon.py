"""Rectangular mortise-and-tenon joinery derived from reference notebooks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cadquery as cq

from app.services.joinery.base import GeometryOperation, box_at
from app.services.joinery.config import joinery_defaults


@dataclass(frozen=True)
class StubTenonParams:
    width: float
    thickness: float
    length: float
    clearance: float


@dataclass(frozen=True)
class PostTenonParams:
    width: float
    depth: float
    length: float
    mortise_clearance: float
    mortise_extra_depth: float


@dataclass(frozen=True)
class StudToSillFixtureParams:
    stud_width: float
    stud_depth: float
    stud_length: float
    sill_width: float
    sill_depth: float
    sill_height: float
    girder_width: float
    girder_depth: float
    girder_height: float


def default_stub_tenon_params() -> StubTenonParams:
    return StubTenonParams(**joinery_defaults("stub_tenon"))


def default_post_tenon_params() -> PostTenonParams:
    return PostTenonParams(**joinery_defaults("post_tenon"))


def default_stud_to_sill_fixture_params() -> StudToSillFixtureParams:
    return StudToSillFixtureParams(**joinery_defaults("stud_to_sill_fixture"))


def vertical_stub_tenon_pair(
    member_id: str,
    stud_width: float,
    stud_depth: float,
    shoulder_length: float,
    params: Optional[StubTenonParams] = None,
) -> List[GeometryOperation]:
    params = params or default_stub_tenon_params()
    x0 = -params.width / 2.0
    y0 = -params.thickness / 2.0
    bottom = box_at((params.width, params.thickness, params.length), (x0, y0, -params.length))
    top = box_at((params.width, params.thickness, params.length), (x0, y0, shoulder_length))
    return [
        GeometryOperation(member_id, "fuse", bottom),
        GeometryOperation(member_id, "fuse", top),
    ]


def vertical_stub_mortise(
    member_id: str,
    center: Tuple[float, float],
    z0: float,
    params: Optional[StubTenonParams] = None,
) -> GeometryOperation:
    params = params or default_stub_tenon_params()
    width = params.width + params.clearance
    thickness = params.thickness + params.clearance
    cutter = box_at(
        (width, thickness, params.length),
        (center[0] - width / 2.0, center[1] - thickness / 2.0, z0),
    )
    return GeometryOperation(member_id, "cut", cutter)


def post_top_tenon(
    member_id: str,
    post_width: float,
    post_depth: float,
    post_height: float,
    params: Optional[PostTenonParams] = None,
) -> GeometryOperation:
    params = params or default_post_tenon_params()
    x0 = -params.width / 2.0
    y0 = -params.depth / 2.0
    tenon = box_at((params.width, params.depth, params.length), (x0, y0, post_height))
    return GeometryOperation(member_id, "fuse", tenon)


def post_bottom_tenon(
    member_id: str,
    post_width: float,
    post_depth: float,
    params: Optional[PostTenonParams] = None,
) -> GeometryOperation:
    params = params or default_post_tenon_params()
    x0 = -params.width / 2.0
    y0 = -params.depth / 2.0
    tenon = box_at((params.width, params.depth, params.length), (x0, y0, -params.length))
    return GeometryOperation(member_id, "fuse", tenon)


def post_tenon_mortise(
    member_id: str,
    center: Tuple[float, float],
    z0: float,
    params: Optional[PostTenonParams] = None,
) -> GeometryOperation:
    params = params or default_post_tenon_params()
    width = params.width + params.mortise_clearance
    depth = params.depth + params.mortise_clearance
    length = params.length + params.mortise_extra_depth
    mortise = box_at(
        (width, depth, length),
        (center[0] - width / 2.0, center[1] - depth / 2.0, z0),
    )
    return GeometryOperation(member_id, "cut", mortise)


def stud_to_sill_fixture(
    params: Optional[StubTenonParams] = None,
    fixture_params: Optional[StudToSillFixtureParams] = None,
) -> Tuple[cq.Workplane, cq.Workplane, cq.Workplane]:
    params = params or default_stub_tenon_params()
    fixture_params = fixture_params or default_stud_to_sill_fixture_params()

    stud = box_at(
        (fixture_params.stud_width, fixture_params.stud_depth, fixture_params.stud_length),
        (-fixture_params.stud_width / 2.0, -fixture_params.stud_depth / 2.0, 0.0),
    )
    stud = apply_fixture_ops(
        stud,
        vertical_stub_tenon_pair(
            "stud",
            fixture_params.stud_width,
            fixture_params.stud_depth,
            fixture_params.stud_length,
            params,
        ),
    )
    sill = box_at(
        (fixture_params.sill_width, fixture_params.sill_depth, fixture_params.sill_height),
        (-fixture_params.sill_width / 2.0, -fixture_params.sill_depth / 2.0, -fixture_params.sill_height),
    )
    girder = box_at(
        (fixture_params.girder_width, fixture_params.girder_depth, fixture_params.girder_height),
        (
            -fixture_params.girder_width / 2.0,
            -fixture_params.girder_depth / 2.0,
            fixture_params.stud_length,
        ),
    )
    sill = sill.cut(vertical_stub_mortise("sill", (0.0, 0.0), -params.length, params).shape)
    girder = girder.cut(vertical_stub_mortise("girder", (0.0, 0.0), fixture_params.stud_length, params).shape)
    return stud, sill, girder


def apply_fixture_ops(blank: cq.Workplane, operations: List[GeometryOperation]) -> cq.Workplane:
    result = blank
    for op in operations:
        result = result.union(op.shape) if op.operation == "fuse" else result.cut(op.shape)
    return cq.Workplane("XY").add(result.val().clean())
