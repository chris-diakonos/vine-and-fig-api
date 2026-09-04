"""
Shared building layout datums derived from the cornerstone coordinate system.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from app.models.floorplan import Dimensions
from app.models.structure import Structure
from app.services.config_loader import load_json_config


@dataclass(frozen=True)
class BuildingLayout:
    """Reusable dimensions and datum elevations for component builders."""

    dimensions: Dimensions
    stories: int
    ceiling_heights: List[float]
    floor_heights: List[float]
    chair_rail_heights: List[float]
    bay_heights: List[float]
    bay_widths: List[float]
    openings: List[Dict[str, Any]]
    tolerance: float

    @classmethod
    def from_structure(cls, structure: Structure) -> "BuildingLayout":
        config = load_json_config("building", "BUILDING_CONFIG_PATH")
        defaults = config["defaults"]
        floorplan = structure.floorplan
        dimensions = floorplan.dimensions
        stories = floorplan.stories
        ceiling_heights = calculate_ceiling_heights(
            stories,
            floorplan.joist_heights,
            floorplan.ceiling_heights,
            defaults["sill_height"],
        )
        floor_heights = calculate_floor_heights(
            stories,
            floorplan.joist_heights,
            floorplan.ceiling_heights,
            defaults["sill_height"],
        )

        chair_rail_heights: List[float] = []
        bay_heights: List[float] = []
        bay_widths: List[float] = []
        for idx, floor_height in enumerate(floor_heights):
            chair_rail_height = floor_height + defaults["chair_rail_height"]
            chair_rail_heights.append(chair_rail_height)
            bay_heights.append(chair_rail_height + defaults["bay_height_above_chair_rail"])
            if structure.windows:
                window_idx = min(idx, len(structure.windows) - 1)
                bay_widths.append(structure.windows[window_idx].bay_width)
            else:
                bay_widths.append(0)

        return cls(
            dimensions=dimensions,
            stories=stories,
            ceiling_heights=ceiling_heights,
            floor_heights=floor_heights,
            chair_rail_heights=chair_rail_heights,
            bay_heights=bay_heights,
            bay_widths=bay_widths,
            openings=collect_openings(structure, defaults),
            tolerance=defaults["tolerance"],
        )


def calculate_ceiling_heights(
    stories: int,
    joist_heights: List[float],
    ceiling_heights: List[float],
    sill_height: float,
) -> List[float]:
    """Calculate cumulative ceiling elevations for each story."""

    heights = []
    height = 0.0
    for story in range(1, stories + 1):
        if story == 1:
            height = sill_height + ceiling_heights[0]
        else:
            height = height + joist_heights[story - 1] + ceiling_heights[story - 1]
        heights.append(height)
    return heights


def calculate_floor_heights(
    stories: int,
    joist_heights: List[float],
    ceiling_heights: List[float],
    sill_height: float,
) -> List[float]:
    """Calculate floor elevations, including the attic/deck level."""

    heights = []
    height = 0.0
    for story in range(1, stories + 2):
        if story == 1:
            height = sill_height
        else:
            height = height + ceiling_heights[story - 2] + joist_heights[story - 1]
        heights.append(height)
    return heights


def collect_openings(structure: Structure, defaults: Dict[str, float]) -> List[Dict[str, Any]]:
    """Collect door and window openings in shared wall/floor terms."""

    openings: List[Dict[str, Any]] = []
    for door in structure.doors:
        if door.wall and door.position is not None:
            width, height = _parse_size(door.size, defaults["door_width"], defaults["door_height"])
            openings.append(
                {
                    "wall": door.wall,
                    "position": door.position,
                    "floor": door.floor if door.floor is not None else 1,
                    "type": "door",
                    "width": width,
                    "height": height,
                }
            )

    if not structure.windows:
        return openings

    has_explicit_locations = any(
        window.wall and window.position is not None and window.floor is not None
        for window in structure.windows
    )
    if has_explicit_locations:
        for window in structure.windows:
            if window.wall and window.position is not None and window.floor is not None:
                width, height = _parse_size(window.size, defaults["window_width"], defaults["window_height"])
                openings.append(
                    {
                        "wall": window.wall,
                        "position": window.position,
                        "floor": window.floor,
                        "type": "window",
                        "width": width,
                        "height": height,
                    }
                )
        return openings

    door_locations = {
        (opening["wall"], opening["position"], opening["floor"])
        for opening in openings
        if opening["type"] == "door"
    }
    for story_idx in range(structure.floorplan.stories):
        if story_idx >= len(structure.windows):
            break
        window = structure.windows[story_idx]
        floor_number = story_idx + 1
        width, height = _parse_size(window.size, defaults["window_width"], defaults["window_height"])
        for face in ["front", "rear", "left", "right"]:
            bays = getattr(structure.floorplan.bays, face, []) if structure.floorplan.bays else []
            for bay_position in bays:
                if (face, bay_position, floor_number) in door_locations:
                    continue
                openings.append(
                    {
                        "wall": face,
                        "position": bay_position,
                        "floor": floor_number,
                        "type": "window",
                        "width": width,
                        "height": height,
                    }
                )
    return openings


def _parse_size(size: str, default_width: float, default_height: float) -> tuple[float, float]:
    size_parts = size.split("x")
    if len(size_parts) != 2:
        return default_width, default_height
    return float(size_parts[0]), float(size_parts[1])
