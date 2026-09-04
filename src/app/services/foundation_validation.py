"""
Deterministic validation for foundation scene nodes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.scene_graph import Bounds, SceneNode, aggregate_local_bounds
from app.services.validation import DEFAULT_TOLERANCE_INCHES, ValidationResult, validation_summary


def validate_foundation_scene(scene: SceneNode, tolerance: float = DEFAULT_TOLERANCE_INCHES) -> Dict[str, Any]:
    """Validate migrated foundation nodes in a scene tree."""

    results: List[ValidationResult] = []
    for node in scene.iter_nodes():
        if node.node_type == "foundation":
            results.extend(_validate_foundation_node(node, tolerance))
    return validation_summary(results, tolerance)


def _validate_foundation_node(foundation_node: SceneNode, tolerance: float) -> List[ValidationResult]:
    results: List[ValidationResult] = []
    metrics = foundation_node.metadata.get("metrics", {})
    bounds = aggregate_local_bounds(foundation_node)
    if bounds is None:
        return [
            ValidationResult(
                code="FOUNDATION_MISSING_GEOMETRY",
                severity="error",
                target=foundation_node.semantic_path,
                message="Foundation has no geometry-bearing descendants.",
                tolerance=tolerance,
            )
        ]

    expected_height = metrics["courses"] * metrics["block_height"] + (metrics["courses"] - 1) * metrics["joint"]
    results.extend(
        _dimension_checks(
            foundation_node.semantic_path,
            bounds,
            expected_width=metrics["foundation_width"],
            expected_depth=metrics["foundation_depth"],
            expected_height=expected_height,
            tolerance=tolerance,
        )
    )

    expected_top_z = -metrics["joint"]
    top_delta = abs(bounds.max[2] - expected_top_z)
    if top_delta > tolerance:
        results.append(
            ValidationResult(
                code="FOUNDATION_REFERENCE_PLANE_MISMATCH",
                severity="error",
                target=foundation_node.semantic_path,
                message="Foundation top reference plane drifted from the legacy parity datum.",
                expected={"top_z": expected_top_z},
                measured={"top_z": bounds.max[2], "delta": top_delta},
                tolerance=tolerance,
            )
        )

    for course in foundation_node.children:
        course_bounds = aggregate_local_bounds(course)
        if course_bounds is None:
            results.append(
                ValidationResult(
                    code="FOUNDATION_COURSE_EMPTY",
                    severity="error",
                    target=course.semantic_path,
                    message="Foundation course has no block geometry.",
                    tolerance=tolerance,
                )
            )

    return results


def _dimension_checks(
    target: str,
    bounds: Bounds,
    expected_width: float,
    expected_depth: float,
    expected_height: float,
    tolerance: float,
) -> List[ValidationResult]:
    results: List[ValidationResult] = []
    checks = [
        ("FOUNDATION_WIDTH_UNDERBUILT", "x", expected_width, bounds.size[0]),
        ("FOUNDATION_DEPTH_UNDERBUILT", "y", expected_depth, bounds.size[1]),
        ("FOUNDATION_HEIGHT_MISMATCH", "z", expected_height, bounds.size[2]),
    ]
    for code, axis, expected, measured in checks:
        underbuilt = measured + tolerance < expected
        mismatched_height = axis == "z" and abs(measured - expected) > tolerance
        if underbuilt or mismatched_height:
            results.append(
                ValidationResult(
                    code=code,
                    severity="error",
                    target=target,
                    message=f"Foundation {axis}-axis bounds do not match required extents.",
                    expected={"axis": axis, "value": expected},
                    measured={"axis": axis, "value": measured, "delta": abs(measured - expected)},
                    tolerance=tolerance,
                )
            )
    return results
