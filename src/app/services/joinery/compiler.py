"""Apply declared joinery operations to scene members."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, Iterable, List

from app.services.joinery.base import GeometryOperation, JointSpec, JoineryError, apply_operations
from app.services.scene_graph import SceneNode


JointHandler = Callable[[JointSpec, Dict[str, SceneNode]], Iterable[GeometryOperation]]


def compile_joinery(
    scene: SceneNode,
    joint_specs: Iterable[JointSpec],
    handlers: Dict[str, JointHandler],
) -> List[GeometryOperation]:
    members = _members_by_id(scene)
    operations_by_member: Dict[str, List[GeometryOperation]] = defaultdict(list)
    all_operations: List[GeometryOperation] = []

    for spec in joint_specs:
        handler = handlers.get(spec.joint_type)
        if handler is None:
            raise JoineryError(f"Unknown joint type: {spec.joint_type}")
        for op in handler(spec, members):
            if op.member_id not in members:
                raise JoineryError(f"Joint {spec.id} targets unknown member: {op.member_id}")
            operations_by_member[op.member_id].append(op)
            all_operations.append(op)

    for member_id, operations in operations_by_member.items():
        member = members[member_id]
        blank = member.blank_geometry or member.geometry
        if blank is None:
            raise JoineryError(f"Member has no blank geometry: {member_id}")
        member.blank_geometry = blank
        member.joined_geometry = apply_operations(blank, operations)
        member.geometry = member.joined_geometry
        member.metadata["joinery"] = {
            "operation_count": len(operations),
            "joint_ids": [op.joint_id for op in operations if op.joint_id],
        }

    return all_operations


def _members_by_id(scene: SceneNode) -> Dict[str, SceneNode]:
    members: Dict[str, SceneNode] = {}
    for node in scene.iter_nodes():
        member_id = node.metadata.get("component_name")
        if member_id and node.geometry is not None:
            members[member_id] = node
    return members
