"""
Deterministic validation for roof scene nodes.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.scene_graph import SceneNode, aggregate_local_bounds
from app.services.validation import DEFAULT_TOLERANCE_INCHES, ValidationResult, validation_summary


def validate_roof_scene(scene: SceneNode, tolerance: float = DEFAULT_TOLERANCE_INCHES) -> Dict[str, Any]:
    """Validate migrated roof nodes in a scene tree."""

    results: List[ValidationResult] = []
    for node in scene.iter_nodes():
        if node.node_type == "roof":
            bounds = aggregate_local_bounds(node)
            if bounds is None:
                results.append(
                    ValidationResult(
                        code="ROOF_MISSING_GEOMETRY",
                        severity="error",
                        target=node.semantic_path,
                        message="Roof has no panel geometry.",
                        tolerance=tolerance,
                    )
                )
            elif not node.children:
                results.append(
                    ValidationResult(
                        code="ROOF_PANELS_MISSING",
                        severity="error",
                        target=node.semantic_path,
                        message="Roof panels are not represented by semantic scene nodes.",
                        tolerance=tolerance,
                    )
                )
    return validation_summary(results, tolerance)
