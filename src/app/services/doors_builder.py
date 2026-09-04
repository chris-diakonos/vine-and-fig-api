"""
Doors builder service using CadQuery.
"""
import cadquery as cq
from typing import Any, Dict, List, Optional
from app.models.openings import Door
from app.models.floorplan import Dimensions
from app.services.config_loader import load_json_config
from app.services.door_validation import validate_door_scene
from app.services.scene_graph import SceneNode, Transform, aggregate_local_bounds, collect_component_metadata, project_scene_to_assembly


class DoorsBuilder:
    """Builds door geometry using CadQuery."""

    @staticmethod
    def _config() -> Dict[str, Any]:
        return load_json_config("doors", "DOORS_CONFIG_PATH")

    @staticmethod
    def _color() -> cq.Color:
        return cq.Color(*DoorsBuilder._config()["defaults"]["color"])
    
    @staticmethod
    def build(doors: List[Door], dimensions: Dimensions, floor_heights: Optional[List[float]] = None) -> Optional[cq.Assembly]:
        """
        Build door openings and frames.
        
        Args:
            doors: List of door specifications
            dimensions: Building dimensions
            
        Returns:
            CadQuery Assembly with door geometry and colors, or None if no doors
        """
        if not doors:
            return None

        scene_root = DoorsBuilder._door_scene(doors, dimensions, floor_heights or [])
        doors_assembly = cq.Assembly()
        project_scene_to_assembly(scene_root, doors_assembly)
        doors_assembly.scene_root = scene_root
        doors_assembly.scene_components = collect_component_metadata(scene_root)
        doors_assembly.validation_results = validate_door_scene(scene_root)
        return doors_assembly if doors_assembly.children else None

    @staticmethod
    def _door_scene(doors: List[Door], dimensions: Dimensions, floor_heights: List[float]) -> SceneNode:
        root = SceneNode("building", "building", "building")
        doors_root = root.add_child(SceneNode("doors", "assembly", "doors"))

        for i, door in enumerate(doors):
            if not (door.wall and door.position is not None):
                continue
            width, height = DoorsBuilder._door_size(door)
            door_obj = DoorsBuilder._door_geometry(door, width, height)
            floor = door.floor if door.floor is not None else 1
            transform = DoorsBuilder._door_transform(
                door.wall,
                door.position,
                floor,
                dimensions,
                width,
                door.thickness,
                height,
                floor_heights,
            )
            semantic_name = f"{door.wall}_wall/story_{floor}/door_{door.position:g}"
            door_node = doors_root.add_child(
                SceneNode(
                    semantic_name,
                    "door",
                    "door",
                    local_transform=transform,
                    metadata={
                        "metrics": {
                            "width": width,
                            "height": height,
                            "thickness": door.thickness,
                            "floor": floor,
                        },
                        "coordinate_system": "door-local",
                    },
                )
            )
            door_node.add_child(
                SceneNode(
                    "slab",
                    "part",
                    "door_slab",
                    geometry=door_obj.translate((width / 2, door.thickness / 2, height / 2)),
                    color=DoorsBuilder._color(),
                    metadata={"component_name": f"door_{i}"},
                )
            )
            local_bounds = aggregate_local_bounds(door_node)
            if local_bounds is not None:
                door_node.metadata["local_bounds_datum"] = local_bounds.as_dict()
        return root

    @staticmethod
    def _door_size(door: Door) -> tuple[float, float]:
        defaults = DoorsBuilder._config()["defaults"]
        size_parts = door.size.split("x")
        if len(size_parts) == 2:
            return float(size_parts[0]), float(size_parts[1])
        return defaults["width"], defaults["height"]

    @staticmethod
    def _door_geometry(door: Door, width: float, height: float) -> cq.Workplane:
        if door.configuration == "six-panel" and door.panel_type == "raised-panel":
            return DoorsBuilder._build_six_panel_raised_door(door, width, height)
        return cq.Workplane("XY").box(width, door.thickness, height)
    
    @staticmethod
    def _build_six_panel_raised_door(
        door: Door,
        width: float,
        height: float
    ) -> cq.Workplane:
        """
        Build a six-panel raised-panel door.
        
        Args:
            door: Door specification with stile_widths, rail_widths, panel_widths
            width: Door width
            height: Door height
            
        Returns:
            CadQuery Workplane with door geometry
        """
        thickness = door.thickness
        
        # Extract stile and rail dimensions
        left_stile = door.stile_widths[0]
        mid_stile = door.stile_widths[1]
        right_stile = door.stile_widths[2]
        
        top_rail = door.rail_widths[0]
        upper_mid_rail = door.rail_widths[1]
        lower_mid_rail = door.rail_widths[2]
        bottom_rail = door.rail_widths[3]
        
        left_panel_width = door.panel_widths[0]
        right_panel_width = door.panel_widths[1]
        
        # Create base door slab
        door_slab = cq.Workplane("XY").box(width, thickness, height)
        
        # Calculate panel positions and heights
        # Three rows of panels
        defaults = DoorsBuilder._config()["defaults"]
        panel_depth = defaults["panel_recess_depth"]
        raised_height = defaults["raised_panel_height"]
        
        # Calculate vertical positions for three rows
        top_panel_start = height / 2 - top_rail
        upper_mid_panel_start = top_panel_start - (height - top_rail - upper_mid_rail - lower_mid_rail - bottom_rail) / 3
        lower_mid_panel_start = upper_mid_panel_start - (height - top_rail - upper_mid_rail - lower_mid_rail - bottom_rail) / 3
        
        # Calculate panel heights
        panel_height = (height - top_rail - upper_mid_rail - lower_mid_rail - bottom_rail) / 3
        
        # Create panels for all six positions (3 rows x 2 columns)
        for row in range(3):
            if row == 0:
                panel_z = top_panel_start - panel_height / 2
            elif row == 1:
                panel_z = upper_mid_panel_start - panel_height / 2
            else:
                panel_z = lower_mid_panel_start - panel_height / 2
            
            # Left panel - cut recess and add raised center
            left_panel_x = -width / 2 + left_stile + left_panel_width / 2
            
            # Cut panel recess from door
            panel_recess = (
                cq.Workplane("XY")
                .box(left_panel_width, panel_depth * 2, panel_height)
                .translate((left_panel_x, thickness / 2 - panel_depth, panel_z))
            )
            door_slab = door_slab.cut(panel_recess)
            
            # Add raised panel center
            raised_panel = (
                cq.Workplane("XY")
                .box(left_panel_width - 2, raised_height, panel_height - 2)
                .translate((left_panel_x, thickness / 2 - panel_depth + raised_height / 2, panel_z))
            )
            door_slab = door_slab.union(raised_panel)
            
            # Right panel - cut recess and add raised center
            right_panel_x = width / 2 - right_stile - right_panel_width / 2
            
            # Cut panel recess from door
            panel_recess = (
                cq.Workplane("XY")
                .box(right_panel_width, panel_depth * 2, panel_height)
                .translate((right_panel_x, thickness / 2 - panel_depth, panel_z))
            )
            door_slab = door_slab.cut(panel_recess)
            
            # Add raised panel center
            raised_panel = (
                cq.Workplane("XY")
                .box(right_panel_width - 2, raised_height, panel_height - 2)
                .translate((right_panel_x, thickness / 2 - panel_depth + raised_height / 2, panel_z))
            )
            door_slab = door_slab.union(raised_panel)
        
        return door_slab
    
    @staticmethod
    def _door_transform(
        wall: str,
        position: float,
        floor: int,
        dimensions: Dimensions,
        width: float,
        thickness: float,
        door_height: float,
        floor_heights: List[float],
    ) -> Transform:
        """
        Position a door on a specific wall.
        
        Args:
            wall: Wall identifier (front, rear, left, right)
            position: Position along wall from left
            floor: Floor number (1-indexed)
            dimensions: Building dimensions
            width: Width of the door
            thickness: Thickness of the door
            door_height: Height of the door
            floor_heights: Shared floor datum elevations
            
        Returns:
            Transform from door-local lower-left sill datum to legacy building space
        """
        defaults = DoorsBuilder._config()["defaults"]
        if floor_heights and 0 <= floor - 1 < len(floor_heights):
            sill_z = floor_heights[floor - 1] + defaults["finished_floor_offset"]
        else:
            sill_z = (floor - 1) * defaults["story_height"] + 11.0
        center_z = sill_z + door_height / 2

        if wall == "front":
            x_pos = position
            y_pos = thickness / 2
        elif wall == "rear":
            x_pos = position
            y_pos = -dimensions.right + thickness / 2
        elif wall == "left":
            x_pos = thickness / 2
            y_pos = -position
        elif wall == "right":
            x_pos = dimensions.front + thickness / 2
            y_pos = -position
        else:
            x_pos = position
            y_pos = thickness / 2

        return Transform.translate(x_pos - width / 2, y_pos - thickness / 2, center_z - door_height / 2)

