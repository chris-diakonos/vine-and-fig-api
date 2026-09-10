"""JointSpec handlers for the current framing integration slice."""
from __future__ import annotations

from typing import Dict, Iterable

from app.services.joinery.base import GeometryOperation, JointSpec
from app.services.joinery.joist_to_sill import (
    default_joist_to_sill_params,
    joist_to_sill_operations,
)
from app.services.joinery.plate_splice import plate_splice_operations, plate_splice_params
from app.services.joinery.post_to_girt import (
    default_post_to_girt_params,
    post_to_girt_operations,
)
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
    joint_datums = spec.params.get("joint_datums", {})
    side_mortise_center = None
    if "side_sill_mortise_center_x" in joint_datums and "side_sill_mortise_center_y" in joint_datums:
        side_mortise_center = (
            float(joint_datums["side_sill_mortise_center_x"]),
            float(joint_datums["side_sill_mortise_center_y"]),
        )
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
        side_mortise_center=side_mortise_center,
        params=params,
    ):
        yield GeometryOperation(op.member_id, op.operation, op.shape, spec.id)


def joist_sill_handler(
    spec: JointSpec,
    members: Dict[str, SceneNode],
) -> Iterable[GeometryOperation]:
    params = default_joist_to_sill_params()
    joint_datums = spec.params["joint_datums"]
    for op in joist_to_sill_operations(
        joist_id=spec.member_a,
        sill_id=spec.member_b,
        joist_end_y=float(joint_datums["joist_end_y"]),
        joist_top_z=float(joint_datums["joist_top_z"]),
        joist_tail_center_x=float(joint_datums["joist_tail_center_x"]),
        sill_socket_center=(
            float(joint_datums["sill_socket_center_x"]),
            float(joint_datums["sill_socket_center_y"]),
        ),
        sill_top_z=float(joint_datums["sill_top_z"]),
        direction=int(joint_datums["direction"]),
        params=params,
    ):
        yield GeometryOperation(op.member_id, op.operation, op.shape, spec.id)


def post_girt_handler(
    spec: JointSpec,
    members: Dict[str, SceneNode],
) -> Iterable[GeometryOperation]:
    girt = members[spec.member_a]
    post = members[spec.member_b]
    girt_bounds = bounds_for_workplane(girt.geometry)
    post_bounds = bounds_for_workplane(post.geometry)
    if girt_bounds is None or post_bounds is None:
        return []

    girt_datums = girt.metadata.get("framing_datums", {})
    post_datums = post.metadata.get("framing_datums", {})
    girt_center = girt_datums.get("center")
    post_min = post_datums.get("min_corner")
    if not isinstance(girt_center, list) or not isinstance(post_min, list):
        return []

    axis = spec.params["axis"]
    if axis == "x":
        mortise_center = (
            float(girt_center[1]) - float(post_min[1]),
            float(girt_center[2]) - float(post_min[2]),
        )
    else:
        mortise_center = (
            float(girt_center[0]) - float(post_min[0]),
            float(girt_center[2]) - float(post_min[2]),
        )

    params = default_post_to_girt_params()
    for op in post_to_girt_operations(
        girt_id=spec.member_a,
        post_id=spec.member_b,
        girt_size=girt_bounds.size,
        post_size=post_bounds.size,
        axis=axis,
        girt_end=spec.params["girt_end"],
        mortise_center=mortise_center,
        params=params,
    ):
        yield GeometryOperation(op.member_id, op.operation, op.shape, spec.id)


FRAMING_JOINERY_HANDLERS = {
    "plate_splice": plate_splice_handler,
    "joist_sill": joist_sill_handler,
    "post_girt": post_girt_handler,
    "post_sill_corner": post_sill_corner_handler,
}
