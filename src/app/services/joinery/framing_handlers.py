"""JointSpec handlers for the current framing integration slice."""
from __future__ import annotations

from typing import Dict, Iterable

from app.services.joinery.base import GeometryOperation, JointSpec
from app.services.joinery.plate_splice import plate_splice_operations, plate_splice_params
from app.services.scene_graph import SceneNode


def plate_splice_handler(
    spec: JointSpec,
    members: Dict[str, SceneNode],
) -> Iterable[GeometryOperation]:
    params = plate_splice_params(spec.params)
    for op in plate_splice_operations(spec.member_a, spec.member_b, params):
        yield GeometryOperation(op.member_id, op.operation, op.shape, spec.id)


FRAMING_JOINERY_HANDLERS = {
    "plate_splice": plate_splice_handler,
}
