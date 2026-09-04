"""
Deterministic validation for framing scene nodes.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.scene_graph import SceneNode, aggregate_local_bounds
from app.services.validation import DEFAULT_TOLERANCE_INCHES, ValidationResult, validation_summary


def validate_framing_scene(scene: SceneNode, tolerance: float = DEFAULT_TOLERANCE_INCHES) -> Dict[str, Any]:
    """Validate migrated framing nodes in a scene tree."""

    results: List[ValidationResult] = []
    for node in scene.iter_nodes():
        if node.node_type == "framing":
            bounds = aggregate_local_bounds(node)
            if bounds is None:
                results.append(
                    ValidationResult(
                        code="FRAMING_MISSING_GEOMETRY",
                        severity="error",
                        target=node.semantic_path,
                        message="Framing has no member geometry.",
                        tolerance=tolerance,
                    )
                )
            elif not node.children:
                results.append(
                    ValidationResult(
                        code="FRAMING_GROUPS_MISSING",
                        severity="error",
                        target=node.semantic_path,
                        message="Framing members are not grouped under semantic scene nodes.",
                        tolerance=tolerance,
                    )
                )
        
        # Validate rafter eave overhang
        if node.role == "rafter" and "front" in node.name:
            bounds = aggregate_local_bounds(node)
            if bounds:
                # Front rafters should extend to approximately y=14.674 (2.674 + 12)
                expected_front_eave_y = 14.674
                measured_y_max = bounds.max[1]
                eave_tolerance = 2.0
                
                if abs(measured_y_max - expected_front_eave_y) > eave_tolerance:
                    results.append(
                        ValidationResult(
                            code="RAFTER_FRONT_EAVE_MISMATCH",
                            severity="warning",
                            target=node.semantic_path,
                            message=f"Front rafter eave position: y={measured_y_max:.2f}, expected ~{expected_front_eave_y:.2f}",
                            expected={"eave_y": expected_front_eave_y},
                            measured={"eave_y": measured_y_max},
                            tolerance=eave_tolerance,
                        )
                    )
        
        if node.role == "rafter" and "rear" in node.name:
            bounds = aggregate_local_bounds(node)
            if bounds:
                # Rear rafters should extend to approximately y=-262.528 (-250.528 - 12)
                expected_rear_eave_y = -262.528
                measured_y_min = bounds.min[1]
                eave_tolerance = 2.0
                
                if abs(measured_y_min - expected_rear_eave_y) > eave_tolerance:
                    results.append(
                        ValidationResult(
                            code="RAFTER_REAR_EAVE_MISMATCH",
                            severity="warning",
                            target=node.semantic_path,
                            message=f"Rear rafter eave position: y={measured_y_min:.2f}, expected ~{expected_rear_eave_y:.2f}",
                            expected={"eave_y": expected_rear_eave_y},
                            measured={"eave_y": measured_y_min},
                            tolerance=eave_tolerance,
                        )
                    )
    
    return validation_summary(results, tolerance)
