"""Post-to-sill corner fixture refactored from the reference notebook."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

import cadquery as cq

from app.services.joinery.base import GeometryOperation, apply_operations, box_at
from app.services.joinery.config import joinery_defaults
from app.services.joinery.half_lap import HalfLapParams, lower_half_lap, upper_half_lap
from app.services.joinery.mortise_tenon import PostTenonParams, post_bottom_tenon, post_tenon_mortise


CornerEnd = Literal["min", "max"]


@dataclass(frozen=True)
class PostSillCornerParams:
    sill_width: float
    sill_height: float
    sill_x_length: float
    sill_y_length: float
    post_width: float
    post_depth: float
    post_height: float
    tenon_width: float
    tenon_depth: float
    mortise_clearance: float
    mortise_extra_depth: float

    @property
    def lap_depth(self) -> float:
        return self.sill_height / 2.0

    @property
    def tenon_length(self) -> float:
        return self.sill_height / 2.0


def default_post_sill_corner_params() -> PostSillCornerParams:
    return PostSillCornerParams(**joinery_defaults("post_sill_corner"))


def post_sill_corner_operations(
    post_id: str,
    cross_sill_id: str,
    side_sill_id: str,
    cross_sill_size: Tuple[float, float, float],
    side_sill_size: Tuple[float, float, float],
    post_size: Tuple[float, float, float],
    cross_sill_end: CornerEnd,
    side_sill_end: CornerEnd,
    tenon_height: float,
    params: Optional[PostSillCornerParams] = None,
) -> List[GeometryOperation]:
    params = params or default_post_sill_corner_params()
    lap_depth = side_sill_size[2] / 2.0
    tenon_height = min(tenon_height, side_sill_size[2])

    cross_x0, cross_x1 = _end_interval(cross_sill_size[0], cross_sill_end, side_sill_size[0])
    side_y0, side_y1 = _end_interval(side_sill_size[1], side_sill_end, cross_sill_size[1])

    operations = [
        GeometryOperation(
            cross_sill_id,
            "cut",
            box_at(
                (cross_x1 - cross_x0, cross_sill_size[1], lap_depth),
                (cross_x0, 0.0, cross_sill_size[2] - lap_depth),
            ),
        ),
        GeometryOperation(
            side_sill_id,
            "cut",
            box_at(
                (side_sill_size[0], side_y1 - side_y0, lap_depth),
                (0.0, side_y0, 0.0),
            ),
        ),
        _side_sill_mortise(side_sill_id, side_sill_size, side_sill_end, tenon_height, params),
    ]
    operations.extend(_post_bottom_tenon_shoulder_cuts(post_id, post_size, tenon_height, params))
    return operations


def _end_interval(length: float, end: CornerEnd, zone_length: float) -> Tuple[float, float]:
    if end == "min":
        return 0.0, min(zone_length, length)
    return max(0.0, length - zone_length), length


def _side_sill_mortise(
    side_sill_id: str,
    side_sill_size: Tuple[float, float, float],
    side_sill_end: CornerEnd,
    tenon_height: float,
    params: PostSillCornerParams,
) -> GeometryOperation:
    mortise_width = params.tenon_width + params.mortise_clearance
    mortise_depth = params.tenon_depth + params.mortise_clearance
    mortise_height = tenon_height + params.mortise_extra_depth
    center_x = side_sill_size[0] / 2.0
    center_y = 0.0 if side_sill_end == "min" else side_sill_size[1]
    return GeometryOperation(
        side_sill_id,
        "cut",
        box_at(
            (mortise_width, mortise_depth, mortise_height),
            (
                center_x - mortise_width / 2.0,
                center_y - mortise_depth / 2.0,
                side_sill_size[2] - tenon_height,
            ),
        ),
    )


def _post_bottom_tenon_shoulder_cuts(
    post_id: str,
    post_size: Tuple[float, float, float],
    tenon_height: float,
    params: PostSillCornerParams,
) -> List[GeometryOperation]:
    post_width, post_depth, _ = post_size
    tenon_x0 = (post_width - params.tenon_width) / 2.0
    tenon_x1 = tenon_x0 + params.tenon_width
    tenon_y0 = (post_depth - params.tenon_depth) / 2.0
    tenon_y1 = tenon_y0 + params.tenon_depth
    cuts: List[GeometryOperation] = []

    if tenon_x0 > 0.0:
        cuts.append(GeometryOperation(post_id, "cut", box_at((tenon_x0, post_depth, tenon_height), (0.0, 0.0, 0.0))))
    if tenon_x1 < post_width:
        cuts.append(
            GeometryOperation(
                post_id,
                "cut",
                box_at((post_width - tenon_x1, post_depth, tenon_height), (tenon_x1, 0.0, 0.0)),
            )
        )
    if tenon_y0 > 0.0:
        cuts.append(
            GeometryOperation(
                post_id,
                "cut",
                box_at((params.tenon_width, tenon_y0, tenon_height), (tenon_x0, 0.0, 0.0)),
            )
        )
    if tenon_y1 < post_depth:
        cuts.append(
            GeometryOperation(
                post_id,
                "cut",
                box_at((params.tenon_width, post_depth - tenon_y1, tenon_height), (tenon_x0, tenon_y1, 0.0)),
            )
        )

    return cuts


def post_to_sill_corner_fixture(
    params: Optional[PostSillCornerParams] = None,
) -> Tuple[cq.Workplane, cq.Workplane, cq.Workplane]:
    params = params or default_post_sill_corner_params()
    sill_x = box_at(
        (params.sill_x_length, params.sill_width, params.sill_height),
        (0.0, -params.sill_width / 2.0, 0.0),
    )
    sill_y = box_at(
        (params.sill_width, params.sill_y_length, params.sill_height),
        (-params.sill_width / 2.0, 0.0, 0.0),
    )
    post = box_at(
        (params.post_width, params.post_depth, params.post_height),
        (-params.post_width / 2.0, -params.post_depth / 2.0, params.sill_height),
    )

    lap = HalfLapParams(params.sill_width, params.lap_depth, params.sill_width)
    sill_x = apply_operations(sill_x, [upper_half_lap("sill_x", -params.sill_width / 2.0, lap, params.sill_height)])
    sill_y = apply_operations(sill_y, [lower_half_lap("sill_y", -params.sill_width / 2.0, lap, 0.0)])

    tenon_params = PostTenonParams(
        width=params.tenon_width,
        depth=params.tenon_depth,
        length=params.tenon_length,
        mortise_clearance=params.mortise_clearance,
        mortise_extra_depth=params.mortise_extra_depth,
    )
    post = apply_operations(
        post,
        [
            GeometryOperation(
                "post",
                "fuse",
                post_bottom_tenon("post", params.post_width, params.post_depth, tenon_params).shape.translate(
                    (0.0, 0.0, params.sill_height)
                ),
            )
        ],
    )
    sill_y = apply_operations(
        sill_y,
        [
            post_tenon_mortise(
                "sill_y",
                (0.0, 0.0),
                params.sill_height - tenon_params.length,
                tenon_params,
            )
        ],
    )

    return sill_x, sill_y, post
