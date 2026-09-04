"""
Deterministic validation for floor scene nodes.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.scene_graph import SceneNode, aggregate_local_bounds
from app.services.validation import DEFAULT_TOLERANCE_INCHES, ValidationResult, validation_summary


def validate_floor_scene(scene: SceneNode, tolerance: float = DEFAULT_TOLERANCE_INCHES) -> Dict[str, Any]:
    """Validate migrated floor nodes in a scene tree."""

    results: List[ValidationResult] = []
    for node in scene.iter_nodes():
        if node.node_type == "floor":
            results.extend(_validate_floor_node(node, tolerance))
    return validation_summary(results, tolerance)


def _validate_floor_node(floor_node: SceneNode, tolerance: float) -> List[ValidationResult]:
    bounds = aggregate_local_bounds(floor_node)
    if bounds is None:
        return [
            ValidationResult(
                code="FLOOR_MISSING_GEOMETRY",
                severity="error",
                target=floor_node.semantic_path,
                message="Floor has no plank geometry.",
                tolerance=tolerance,
            )
        ]

    metrics = floor_node.metadata.get("metrics", {})
    results: List[ValidationResult] = []
    checks = [
        ("FLOOR_WIDTH_UNDERBUILT", "x", metrics["floor_length"], bounds.size[0], True),
        ("FLOOR_DEPTH_MISMATCH", "y", metrics["plank_length"], bounds.size[1], False),
        ("FLOOR_THICKNESS_MISMATCH", "z", metrics["floor_thickness"], bounds.size[2], False),
    ]
    for code, axis, expected, measured, allow_overbuild in checks:
        delta = abs(measured - expected)
        failed = measured + tolerance < expected if allow_overbuild else delta > tolerance
        if failed:
            results.append(
                ValidationResult(
                    code=code,
                    severity="error",
                    target=floor_node.semantic_path,
                    message=f"Floor {axis}-axis bounds do not match required extents.",
                    expected={"axis": axis, "value": expected},
                    measured={"axis": axis, "value": measured, "delta": delta},
                    tolerance=tolerance,
                )
            )
    return results
