"""
Shared validation primitives for scene-graph backed builders.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


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


def validation_summary(results: List[ValidationResult], tolerance: float = DEFAULT_TOLERANCE_INCHES) -> Dict[str, Any]:
    """Create the common validation artifact shape for a subsystem."""

    errors = [result.as_dict() for result in results if result.severity == "error"]
    warnings = [result.as_dict() for result in results if result.severity == "warning"]
    return {
        "status": "passed" if not errors else "failed",
        "tolerance": tolerance,
        "errors": errors,
        "warnings": warnings,
        "results": [result.as_dict() for result in results],
    }
