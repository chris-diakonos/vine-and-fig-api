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
SIDE_ELEVATION_VIEW = ViewProjection(
    direction=(0, 1, 0),
    name="Side Elevation View",
    description="Side elevation (looking along Y-axis)"
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
        view_mode: One of 'plan', 'section', 'elevation'
        
    Returns:
        ViewProjection settings
        
    Raises:
        ValueError: If view_mode is not recognized
    """
    projections = {
        "plan": PLAN_VIEW,
        "section": SECTION_VIEW,
        "elevation": ELEVATION_VIEW,
        "side": SIDE_ELEVATION_VIEW,
        "rear": REAR_ELEVATION_VIEW,
        "isometric": ISOMETRIC_VIEW,
    }
    
    if view_mode not in projections:
        raise ValueError(
            f"Invalid view_mode: {view_mode}. "
            f"Must be one of: {', '.join(projections.keys())}"
        )
    
    return projections[view_mode]
