"""Post-to-sill corner fixture refactored from the reference notebook."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import cadquery as cq

from app.services.joinery.base import GeometryOperation, apply_operations, box_at
from app.services.joinery.config import joinery_defaults
from app.services.joinery.half_lap import HalfLapParams, lower_half_lap, upper_half_lap
from app.services.joinery.mortise_tenon import PostTenonParams, post_bottom_tenon, post_tenon_mortise


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
