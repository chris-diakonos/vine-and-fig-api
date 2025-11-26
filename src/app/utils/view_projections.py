"""
View projection settings for 2D drawing generation.
"""
from typing import Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class ViewProjection:
    """Camera projection settings for different view modes."""
    direction: Tuple[float, float, float]
    name: str
    description: str
    
    def to_cadquery_opts(self) -> Dict[str, Any]:
        """Convert to CadQuery export options."""
        return {
            "projectionDir": self.direction
        }


# Define standard architectural views
PLAN_VIEW = ViewProjection(
    direction=(0, 0, 1),
    name="Plan View",
    description="Top-down view (looking down Z-axis)"
)

SECTION_VIEW = ViewProjection(
    direction=(0, 1, 0),
    name="Section View",
    description="Cross-section view (looking along Y-axis)"
)

ELEVATION_VIEW = ViewProjection(
    direction=(1, 0, 0),
    name="Elevation View",
    description="Front elevation (looking along X-axis)"
)

# Alternative elevation views
LEFT_ELEVATION_VIEW = ViewProjection(
    direction=(0, 1, 0),
    name="Left Elevation View",
    description="Left elevation (looking along Y-axis, positive direction)"
)

RIGHT_ELEVATION_VIEW = ViewProjection(
    direction=(0, -1, 0),
    name="Right Elevation View",
    description="Right elevation (looking along Y-axis, negative direction)"
)

REAR_ELEVATION_VIEW = ViewProjection(
    direction=(-1, 0, 0),
    name="Rear Elevation View",
    description="Rear elevation (looking opposite X-axis)"
)

# Isometric view (useful for 2D drawings with depth)
ISOMETRIC_VIEW = ViewProjection(
    direction=(1, 1, 1),
    name="Isometric View",
    description="Isometric projection (equal angles)"
)


def get_projection_settings(view_mode: str) -> ViewProjection:
    """
    Get the projection settings for a given view mode.
    
    Args:
        view_mode: One of 'plan', 'section', 'elevation', 'elevation-front', 
                   'elevation-rear', 'elevation-left', 'elevation-right'
        
    Returns:
        ViewProjection settings
        
    Raises:
        ValueError: If view_mode is not recognized
    """
    # Normalize view_mode for elevation variants
    normalized_mode = view_mode
    if view_mode.startswith("elevation-"):
        # Extract the face from "elevation-front", "elevation-rear", etc.
        face = view_mode.split("-", 1)[1]
        if face == "front":
            normalized_mode = "elevation"
        elif face == "rear":
            normalized_mode = "rear"
        elif face == "left":
            normalized_mode = "left"
        elif face == "right":
            normalized_mode = "right"
        else:
            normalized_mode = "elevation"  # Default to front elevation
    
    projections = {
        "plan": PLAN_VIEW,
        "section": SECTION_VIEW,
        "elevation": ELEVATION_VIEW,
        "left": LEFT_ELEVATION_VIEW,
        "right": RIGHT_ELEVATION_VIEW,
        "rear": REAR_ELEVATION_VIEW,
        "isometric": ISOMETRIC_VIEW,
    }
    
    if normalized_mode not in projections:
        raise ValueError(
            f"Invalid view_mode: {view_mode} (normalized: {normalized_mode}). "
            f"Must be one of: {', '.join(projections.keys())}"
        )
    
    return projections[normalized_mode]
