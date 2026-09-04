"""
Deterministic validation for the window scene-graph slice.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.services.scene_graph import Bounds, SceneNode, aggregate_local_bounds, bounds_for_workplane


DEFAULT_TOLERANCE_INCHES = 0.01


@dataclass
class ValidationResult:
    """Machine-readable geometric validation result."""

    code: str
    severity: str
    target: str
    message: str
    expected: Optional[Dict[str, Any]] = None
    measured: Optional[Dict[str, Any]] = None
    tolerance: float = DEFAULT_TOLERANCE_INCHES

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "target": self.target,
            "message": self.message,
            "expected": self.expected,
            "measured": self.measured,
            "tolerance": self.tolerance,
        }


def validate_window_scene(scene: SceneNode, tolerance: float = DEFAULT_TOLERANCE_INCHES) -> Dict[str, Any]:
    """Validate all window nodes in a scene tree."""

    results: List[ValidationResult] = []
    for node in scene.iter_nodes():
        if node.node_type != "window":
            continue
        results.extend(_validate_window_node(node, tolerance))

    errors = [result.as_dict() for result in results if result.severity == "error"]
    warnings = [result.as_dict() for result in results if result.severity == "warning"]
    return {
        "status": "passed" if not errors else "failed",
        "tolerance": tolerance,
        "errors": errors,
        "warnings": warnings,
        "results": [result.as_dict() for result in results],
    }


def _validate_window_node(window_node: SceneNode, tolerance: float) -> List[ValidationResult]:
    results: List[ValidationResult] = []
    metrics = window_node.metadata.get("metrics", {})
    expected_width = metrics.get("opening_width")
    expected_height = metrics.get("opening_height")

    bounds = aggregate_local_bounds(window_node)
    if bounds is None:
        return [
            ValidationResult(
                code="WINDOW_MISSING_GEOMETRY",
                severity="error",
                target=window_node.semantic_path,
                message="Window has no geometry-bearing descendants.",
                tolerance=tolerance,
            )
        ]

    if expected_width is not None:
        results.append(
            _validate_dimension(
                target=window_node.semantic_path,
                code="WINDOW_WIDTH_MISMATCH",
                axis="x",
                expected=float(expected_width),
                measured=bounds.size[0],
                tolerance=tolerance,
            )
        )

    if expected_height is not None:
        results.append(
            _validate_dimension(
                target=window_node.semantic_path,
                code="WINDOW_HEIGHT_MISMATCH",
                axis="z",
                expected=float(expected_height),
                measured=bounds.size[2],
                tolerance=tolerance,
            )
        )

    results.extend(_validate_named_group_containment(window_node, "lower_sash", bounds, tolerance))
    results.extend(_validate_named_group_containment(window_node, "upper_sash", bounds, tolerance))
    results.extend(_validate_glazing_plane(window_node, tolerance))

    return [result for result in results if result is not None]


def _validate_dimension(
    target: str,
    code: str,
    axis: str,
    expected: float,
    measured: float,
    tolerance: float,
) -> Optional[ValidationResult]:
    delta = abs(expected - measured)
    if delta <= tolerance:
        return None
    return ValidationResult(
        code=code,
        severity="error",
        target=target,
        message=f"Window {axis}-axis dimension does not match expected local assembly size.",
        expected={"axis": axis, "value": expected},
        measured={"axis": axis, "value": measured, "delta": delta},
        tolerance=tolerance,
    )


def _validate_named_group_containment(
    window_node: SceneNode,
    group_name: str,
    window_bounds: Bounds,
    tolerance: float,
) -> List[ValidationResult]:
    group = next((child for child in window_node.children if child.name == group_name), None)
    if group is None:
        return [
            ValidationResult(
                code="WINDOW_GROUP_MISSING",
                severity="error",
                target=window_node.semantic_path,
                message=f"Window is missing required group '{group_name}'.",
                expected={"group": group_name},
                tolerance=tolerance,
            )
        ]

    group_bounds = aggregate_local_bounds(group)
    if group_bounds is None:
        return [
            ValidationResult(
                code="WINDOW_GROUP_EMPTY",
                severity="error",
                target=group.semantic_path,
                message=f"Window group '{group_name}' has no geometry.",
                tolerance=tolerance,
            )
        ]

    if _bounds_contained(group_bounds, window_bounds, tolerance):
        return []

    return [
        ValidationResult(
            code="WINDOW_GROUP_OUTSIDE_ENVELOPE",
            severity="error",
            target=group.semantic_path,
            message=f"Window group '{group_name}' extends outside the local window envelope.",
            expected={"container": window_bounds.as_dict()},
            measured={"bounds": group_bounds.as_dict()},
            tolerance=tolerance,
        )
    ]


def _validate_glazing_plane(window_node: SceneNode, tolerance: float) -> List[ValidationResult]:
    results: List[ValidationResult] = []
    for group_name in ["upper_sash", "lower_sash"]:
        group = next((child for child in window_node.children if child.name == group_name), None)
        if group is None:
            continue
        results.extend(_validate_group_glazing_plane(group, tolerance))
    return results


def _validate_group_glazing_plane(sash_node: SceneNode, tolerance: float) -> List[ValidationResult]:
    glass_bounds = []
    for node in sash_node.iter_nodes():
        if "glass" not in node.role or node.geometry is None:
            continue
        bounds = bounds_for_workplane(node.geometry)
        if bounds is not None:
            glass_bounds.append((node, bounds))

    if not glass_bounds:
        return [
            ValidationResult(
                code="WINDOW_GLAZING_MISSING",
                severity="error",
                target=sash_node.semantic_path,
                message="Sash has no glass panes to validate.",
                tolerance=tolerance,
            )
        ]

    axis = _common_thickness_axis([bounds for _, bounds in glass_bounds])
    centers = [((bounds.min[axis] + bounds.max[axis]) / 2) for _, bounds in glass_bounds]
    average = sum(centers) / len(centers)
    max_delta = max(abs(center - average) for center in centers)
    if max_delta <= tolerance:
        return []

    return [
        ValidationResult(
            code="WINDOW_GLAZING_PLANE_MISMATCH",
            severity="error",
            target=sash_node.semantic_path,
            message="Glass panes are not aligned to a common sash-local glazing plane.",
            expected={"axis": axis, "average": average},
            measured={"max_delta": max_delta},
            tolerance=tolerance,
        )
    ]


def _bounds_contained(inner: Bounds, outer: Bounds, tolerance: float) -> bool:
    for idx in range(3):
        if inner.min[idx] < outer.min[idx] - tolerance:
            return False
        if inner.max[idx] > outer.max[idx] + tolerance:
            return False
    return True


def _common_thickness_axis(bounds_list: List[Bounds]) -> int:
    """Choose the axis that most consistently represents pane thickness."""

    average_sizes = []
    for axis in range(3):
        average_sizes.append(sum(bounds.size[axis] for bounds in bounds_list) / len(bounds_list))
    return min(range(3), key=lambda axis: average_sizes[axis])
