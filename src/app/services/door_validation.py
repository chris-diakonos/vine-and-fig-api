"""
Deterministic validation for door scene nodes.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.scene_graph import SceneNode, aggregate_local_bounds
from app.services.validation import DEFAULT_TOLERANCE_INCHES, ValidationResult, validation_summary


def validate_door_scene(scene: SceneNode, tolerance: float = DEFAULT_TOLERANCE_INCHES) -> Dict[str, Any]:
    """Validate migrated door nodes in a scene tree."""

    results: List[ValidationResult] = []
    for node in scene.iter_nodes():
        if node.node_type == "door":
            results.extend(_validate_door_node(node, tolerance))
    return validation_summary(results, tolerance)


def _validate_door_node(door_node: SceneNode, tolerance: float) -> List[ValidationResult]:
    bounds = aggregate_local_bounds(door_node)
    if bounds is None:
        return [
            ValidationResult(
                code="DOOR_MISSING_GEOMETRY",
                severity="error",
                target=door_node.semantic_path,
                message="Door has no geometry-bearing descendants.",
                tolerance=tolerance,
            )
        ]

    metrics = door_node.metadata.get("metrics", {})
    results: List[ValidationResult] = []
    for code, axis, expected, measured in [
        ("DOOR_WIDTH_MISMATCH", "x", metrics["width"], bounds.size[0]),
        ("DOOR_HEIGHT_MISMATCH", "z", metrics["height"], bounds.size[2]),
    ]:
        delta = abs(expected - measured)
        if delta > tolerance:
            results.append(
                ValidationResult(
                    code=code,
                    severity="error",
                    target=door_node.semantic_path,
                    message=f"Door {axis}-axis dimension does not match expected local size.",
                    expected={"axis": axis, "value": expected},
                    measured={"axis": axis, "value": measured, "delta": delta},
                    tolerance=tolerance,
                )
            )

    sill_delta = abs(bounds.min[2])
    if sill_delta > tolerance:
        results.append(
            ValidationResult(
                code="DOOR_SILL_DATUM_MISMATCH",
                severity="error",
                target=door_node.semantic_path,
                message="Door local bounds do not start at the sill datum.",
                expected={"min_z": 0.0},
                measured={"min_z": bounds.min[2], "delta": sill_delta},
                tolerance=tolerance,
            )
        )
    return results
