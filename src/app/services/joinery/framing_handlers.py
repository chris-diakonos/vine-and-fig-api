"""JointSpec handlers for the current framing integration slice."""
from __future__ import annotations

from typing import Dict, Iterable

from app.services.joinery.base import GeometryOperation, JointSpec
from app.services.joinery.plate_splice import plate_splice_operations, plate_splice_params
from app.services.joinery.post_to_sill_corner import (
    default_post_sill_corner_params,
    post_sill_corner_operations,
)
from app.services.scene_graph import bounds_for_workplane
from app.services.scene_graph import SceneNode


def plate_splice_handler(
    spec: JointSpec,
    members: Dict[str, SceneNode],
) -> Iterable[GeometryOperation]:
    params = plate_splice_params(spec.params)
    for op in plate_splice_operations(spec.member_a, spec.member_b, params):
        yield GeometryOperation(op.member_id, op.operation, op.shape, spec.id)


def post_sill_corner_handler(
    spec: JointSpec,
    members: Dict[str, SceneNode],
) -> Iterable[GeometryOperation]:
    post = members[spec.member_a]
    side_sill = members[spec.member_b]
    cross_sill_id = spec.params["cross_sill_id"]
    cross_sill = members[cross_sill_id]
    post_bounds = bounds_for_workplane(post.geometry)
    side_bounds = bounds_for_workplane(side_sill.geometry)
    cross_bounds = bounds_for_workplane(cross_sill.geometry)
    if post_bounds is None or side_bounds is None or cross_bounds is None:
        return []

    params = default_post_sill_corner_params()
    for op in post_sill_corner_operations(
        post_id=spec.member_a,
        cross_sill_id=cross_sill_id,
        side_sill_id=spec.member_b,
        cross_sill_size=cross_bounds.size,
        side_sill_size=side_bounds.size,
        post_size=post_bounds.size,
        cross_sill_end=spec.params["cross_sill_end"],
        side_sill_end=spec.params["side_sill_end"],
        tenon_height=spec.params["tenon_height"],
        params=params,
    ):
        yield GeometryOperation(op.member_id, op.operation, op.shape, spec.id)


FRAMING_JOINERY_HANDLERS = {
    "plate_splice": plate_splice_handler,
    "post_sill_corner": post_sill_corner_handler,
}
