"""
Deterministic validation for sheathing scene nodes.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.scene_graph import SceneNode, aggregate_local_bounds
from app.services.validation import DEFAULT_TOLERANCE_INCHES, ValidationResult, validation_summary


def validate_sheathing_scene(scene: SceneNode, tolerance: float = DEFAULT_TOLERANCE_INCHES) -> Dict[str, Any]:
    """Validate migrated sheathing nodes in a scene tree."""

    results: List[ValidationResult] = []
    for node in scene.iter_nodes():
        if node.node_type == "sheathing":
            results.extend(_validate_sheathing_node(node, tolerance))
    return validation_summary(results, tolerance)


def _validate_sheathing_node(sheathing_node: SceneNode, tolerance: float) -> List[ValidationResult]:
    bounds = aggregate_local_bounds(sheathing_node)
    if bounds is None:
        return [
            ValidationResult(
                code="SHEATHING_MISSING_GEOMETRY",
                severity="error",
                target=sheathing_node.semantic_path,
                message="Sheathing has no board geometry.",
                tolerance=tolerance,
            )
        ]

    results: List[ValidationResult] = []
    for group in sheathing_node.children:
        group_bounds = aggregate_local_bounds(group)
        if group_bounds is None:
            results.append(
                ValidationResult(
                    code="SHEATHING_GROUP_EMPTY",
                    severity="error",
                    target=group.semantic_path,
                    message="Sheathing wall/gable group has no board geometry.",
                    tolerance=tolerance,
                )
            )
    return results
