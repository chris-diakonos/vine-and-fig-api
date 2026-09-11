"""
Deterministic validation for framing scene nodes.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.scene_graph import SceneNode, aggregate_local_bounds, bounds_for_workplane
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
        
        if node.role == "rafter":
            datums = node.metadata.get("framing_datums", {})
            if "false_plate_top_z" not in datums:
                continue
            bounds = bounds_for_workplane(node.projected_geometry())
            if bounds is None:
                continue
            expected_top_z = float(datums["false_plate_top_z"])
            if abs(bounds.min[2] - expected_top_z) > tolerance:
                results.append(
                    ValidationResult(
                        code="RAFTER_FALSE_PLATE_BEARING_Z_MISMATCH",
                        severity="warning",
                        target=node.semantic_path,
                        message=f"Rafter tail bottom at z={bounds.min[2]:.2f}, expected false-plate top z={expected_top_z:.2f}",
                        expected={"false_plate_top_z": expected_top_z},
                        measured={"rafter_bottom_z": bounds.min[2]},
                        tolerance=tolerance,
                    )
                )

            position = datums.get("position")
            bearing_key = "front_bearing_y" if position == "front" else "rear_bearing_y" if position == "rear" else None
            if bearing_key is None:
                continue
            expected_bearing_y = float(datums[bearing_key])
            if not (bounds.min[1] - tolerance <= expected_bearing_y <= bounds.max[1] + tolerance):
                results.append(
                    ValidationResult(
                        code="RAFTER_FALSE_PLATE_BEARING_Y_MISMATCH",
                        severity="warning",
                        target=node.semantic_path,
                        message=f"Rafter {position} span does not include false-plate bearing y={expected_bearing_y:.2f}",
                        expected={bearing_key: expected_bearing_y},
                        measured={"rafter_y_min": bounds.min[1], "rafter_y_max": bounds.max[1]},
                        tolerance=tolerance,
                    )
                )
    
    return validation_summary(results, tolerance)
