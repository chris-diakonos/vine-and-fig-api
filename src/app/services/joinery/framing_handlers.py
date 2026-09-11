"""JointSpec handlers for the current framing integration slice."""
from __future__ import annotations

from typing import Dict, Iterable

from app.services.joinery.base import GeometryOperation, JointSpec, box_at
from app.services.joinery.brace_to_post_sill import (
    brace_to_post_sill_local_operations,
    default_brace_to_post_sill_params,
)
from app.services.joinery.joist_to_sill import (
    default_joist_to_girt_params,
    default_joist_to_sill_params,
    joist_to_girt_operations,
    joist_to_sill_operations,
)
from app.services.joinery.mortise_tenon import default_stub_tenon_params
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
    raw_params = dict(spec.params)
    axis = raw_params.pop("axis", None)
    member_a_end = raw_params.pop("member_a_end", "max")
    member_b_end = raw_params.pop("member_b_end", "min")
    member_a_splice_position = raw_params.pop("member_a_splice_position", None)
    member_b_splice_position = raw_params.pop("member_b_splice_position", None)
    params = plate_splice_params(raw_params)
    for op in plate_splice_operations(spec.member_a, spec.member_b, params):
        shape = op.shape
        if axis:
            member = members[op.member_id]
            bounds = bounds_for_workplane(member.geometry)
            if bounds is None:
                continue
            splice_end = member_a_end if op.member_id == spec.member_a else member_b_end
            splice_position = (
                member_a_splice_position
                if op.member_id == spec.member_a
                else member_b_splice_position
            )
            shape = _orient_splice_tool(shape, bounds.size, axis, splice_end, splice_position)
        yield GeometryOperation(op.member_id, op.operation, shape, spec.id)


def _orient_splice_tool(shape, member_size, axis: str, splice_end: str, splice_position=None):
    if axis == "x":
        splice_x = splice_position if splice_position is not None else 0.0 if splice_end == "min" else member_size[0]
        return shape.translate((splice_x, member_size[1] / 2.0, 0.0))

    splice_y = splice_position if splice_position is not None else 0.0 if splice_end == "min" else member_size[1]
    return shape.rotate((0, 0, 0), (0, 0, 1), 90.0).translate((member_size[0] / 2.0, splice_y, 0.0))


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


def post_plate_handler(
    spec: JointSpec,
    members: Dict[str, SceneNode],
) -> Iterable[GeometryOperation]:
    post = members[spec.member_a]
    plate = members[spec.member_b]
    post_datums = post.metadata.get("framing_datums", {})
    plate_datums = plate.metadata.get("framing_datums", {})
    post_min = post_datums.get("min_corner")
    plate_min = plate_datums.get("min_corner")
    joint_datums = spec.params.get("joint_datums", {})
    if not isinstance(post_min, list) or not isinstance(plate_min, list):
        return []

    tenon_origin = joint_datums.get("tenon_origin_world")
    tenon_size = joint_datums.get("tenon_size")
    mortise_origin = joint_datums.get("mortise_origin_world")
    mortise_size = joint_datums.get("mortise_size")
    if not all(isinstance(value, list) for value in (tenon_origin, tenon_size, mortise_origin, mortise_size)):
        return []

    post_tenon = box_at(
        (float(tenon_size[0]), float(tenon_size[1]), float(tenon_size[2])),
        (
            float(tenon_origin[0]) - float(post_min[0]),
            float(tenon_origin[1]) - float(post_min[1]),
            float(tenon_origin[2]) - float(post_min[2]),
        ),
    )
    plate_mortise = box_at(
        (float(mortise_size[0]), float(mortise_size[1]), float(mortise_size[2])),
        (
            float(mortise_origin[0]) - float(plate_min[0]),
            float(mortise_origin[1]) - float(plate_min[1]),
            float(mortise_origin[2]) - float(plate_min[2]),
        ),
    )
    yield GeometryOperation(spec.member_a, "fuse", post_tenon, spec.id)
    yield GeometryOperation(spec.member_b, "cut", plate_mortise, spec.id)


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


def joist_girt_handler(
    spec: JointSpec,
    members: Dict[str, SceneNode],
) -> Iterable[GeometryOperation]:
    params = default_joist_to_girt_params()
    joint_datums = spec.params["joint_datums"]
    for op in joist_to_girt_operations(
        joist_id=spec.member_a,
        girt_id=spec.member_b,
        joist_end_y=float(joint_datums["joist_end_y"]),
        joist_top_z=float(joint_datums["joist_top_z"]),
        joist_tail_center_x=float(joint_datums["joist_tail_center_x"]),
        girt_socket_center=(
            float(joint_datums["girt_socket_center_x"]),
            float(joint_datums["girt_socket_center_y"]),
        ),
        girt_top_z=float(joint_datums["girt_top_z"]),
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
        tenon_length=float(spec.params["tenon_length"]),
        params=params,
    ):
        yield GeometryOperation(op.member_id, op.operation, op.shape, spec.id)


def stud_stub_tenon_handler(
    spec: JointSpec,
    members: Dict[str, SceneNode],
) -> Iterable[GeometryOperation]:
    stud = members[spec.member_a]
    receiver = members[spec.member_b]
    stud_bounds = bounds_for_workplane(stud.geometry)
    receiver_bounds = bounds_for_workplane(receiver.geometry)
    if stud_bounds is None or receiver_bounds is None:
        return []

    axis = spec.params["axis"]
    endpoint = spec.params["endpoint"]
    receiver_surface = spec.params["receiver_surface"]
    mortise_center = spec.params["mortise_center"]
    params = default_stub_tenon_params()

    yield GeometryOperation(
        spec.member_a,
        "fuse",
        _stud_tenon_shape(stud_bounds.size, axis, endpoint, params.width, params.thickness, params.length),
        spec.id,
    )
    yield GeometryOperation(
        spec.member_b,
        "cut",
        _stud_mortise_shape(
            receiver_bounds.size,
            axis,
            receiver_surface,
            (float(mortise_center[0]), float(mortise_center[1])),
            params.width + params.clearance,
            params.thickness + params.clearance,
            params.length,
        ),
        spec.id,
    )


def _stud_tenon_shape(member_size, axis: str, endpoint: str, width: float, thickness: float, length: float):
    center_x = member_size[0] / 2.0
    center_y = member_size[1] / 2.0
    z0 = -length if endpoint == "bottom" else member_size[2]
    if axis == "x":
        origin = (center_x - width / 2.0, center_y - thickness / 2.0, z0)
        size = (width, thickness, length)
    else:
        origin = (center_x - thickness / 2.0, center_y - width / 2.0, z0)
        size = (thickness, width, length)
    return box_at(size, origin)


def _stud_mortise_shape(
    receiver_size,
    axis: str,
    receiver_surface: str,
    center,
    width: float,
    thickness: float,
    length: float,
):
    z0 = receiver_size[2] - length if receiver_surface == "top" else 0.0
    if axis == "x":
        origin = (center[0] - width / 2.0, center[1] - thickness / 2.0, z0)
        size = (width, thickness, length)
    else:
        origin = (center[0] - thickness / 2.0, center[1] - width / 2.0, z0)
        size = (thickness, width, length)
    return box_at(size, origin)


def brace_post_receiver_handler(
    spec: JointSpec,
    members: Dict[str, SceneNode],
) -> Iterable[GeometryOperation]:
    brace = members[spec.member_a]
    post = members[spec.params["post_id"]]
    lower_receiver = members[spec.member_b]
    brace_datums = brace.metadata.get("framing_datums", {})
    brace_size = brace_datums.get("size")
    brace_length = brace_datums.get("length")
    brace_angle = brace_datums.get("angle_degrees")
    if not isinstance(brace_size, list) or brace_length is None or brace_angle is None:
        return []

    params = default_brace_to_post_sill_params()
    local_operations = brace_to_post_sill_local_operations(
        brace_id=spec.member_a,
        post_id=post.metadata["component_name"],
        lower_receiver_id=spec.member_b,
        brace_length=float(brace_length),
        brace_thickness=float(brace_size[1]),
        brace_depth=float(brace_size[2]),
        brace_angle_degrees=float(brace_angle),
        params=params,
    )
    for op in local_operations["brace"]:
        yield GeometryOperation(op.member_id, op.operation, op.shape, spec.id)
    for op in local_operations["post"]:
        yield GeometryOperation(
            op.member_id,
            op.operation,
            _transform_shape_between_nodes(op.shape, brace, post),
            spec.id,
        )
    for op in local_operations["lower_receiver"]:
        yield GeometryOperation(
            op.member_id,
            op.operation,
            _transform_shape_between_nodes(op.shape, brace, lower_receiver),
            spec.id,
        )


def _transform_shape_between_nodes(shape, source: SceneNode, target: SceneNode):
    result = shape
    for transform in source.transform_chain_to_root():
        result = transform.apply_to_workplane(result)
    for transform in reversed(target.transform_chain_to_root()):
        result = transform.inverse().apply_to_workplane(result)
    return result


FRAMING_JOINERY_HANDLERS = {
    "brace_post_receiver": brace_post_receiver_handler,
    "plate_splice": plate_splice_handler,
    "post_plate": post_plate_handler,
    "joist_sill": joist_sill_handler,
    "joist_girt": joist_girt_handler,
    "post_girt": post_girt_handler,
    "post_sill_corner": post_sill_corner_handler,
    "stud_stub_tenon": stud_stub_tenon_handler,
}
