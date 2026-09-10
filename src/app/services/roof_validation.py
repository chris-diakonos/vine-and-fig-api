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
            else:
                # Validate gable overhang extent for side-gable roofs
                # Corner posts are 6" wide centered at x=0 and x=480
                # Post outer faces at x=-3 and x=483
                # Roof should extend 12" past post faces: x=-15 to x=495
                if bounds:
                    roof_x_min = bounds.min[0]
                    roof_x_max = bounds.max[0]
                    expected_x_min = -15.0  # 12" past left post outer face at x=-3
                    expected_x_max = 495.0  # 12" past right post outer face at x=483
                    overhang_tolerance = 2.0  # Allow 2" tolerance for discrete panel constraints
                    
                    if roof_x_min > expected_x_min + overhang_tolerance:
                        results.append(
                            ValidationResult(
                                code="GABLE_OVERHANG_LEFT_SHORT",
                                severity="warning",
                                target=node.semantic_path,
                                message=f"Left gable overhang short: roof at x={roof_x_min:.2f}, expected ~{expected_x_min:.2f} (12\" past post face at x=-3)",
                                expected={"x_min": expected_x_min},
                                measured={"x_min": roof_x_min},
                                tolerance=overhang_tolerance,
                            )
                        )
                    
                    if roof_x_max < expected_x_max - overhang_tolerance:
                        results.append(
                            ValidationResult(
                                code="GABLE_OVERHANG_RIGHT_SHORT",
                                severity="warning",
                                target=node.semantic_path,
                                message=f"Right gable overhang short: roof at x={roof_x_max:.2f}, expected ~{expected_x_max:.2f} (12\" past post face at x=483)",
                                expected={"x_max": expected_x_max},
                                measured={"x_max": roof_x_max},
                                tolerance=overhang_tolerance,
                            )
                        )
    return validation_summary(results, tolerance)
