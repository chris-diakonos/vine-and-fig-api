"""
Floor builder service using CadQuery.
"""
import cadquery as cq
from typing import Any, Dict, List
from app.models.building import Flooring
from app.models.floorplan import Dimensions
from app.services.config_loader import load_json_config
from app.services.floor_validation import validate_floor_scene
from app.services.scene_graph import SceneNode, Transform, collect_component_metadata, project_scene_to_assembly


class FloorBuilder:
    """Builds floor geometry using CadQuery."""

    @staticmethod
    def _config() -> Dict[str, Any]:
        return load_json_config("flooring", "FLOORING_CONFIG_PATH")

    @staticmethod
    def _color() -> cq.Color:
        return cq.Color(*FloorBuilder._config()["defaults"]["color"])

    @staticmethod
    def _default_flooring() -> Flooring:
        defaults = FloorBuilder._config()["defaults"]
        return Flooring(
            flooring_type=defaults["flooring_type"],
            flooring_species=defaults["flooring_species"],
            flooring_thickness=defaults["flooring_thickness"],
            flooring_width=defaults["flooring_width"],
            flooring_exposure=defaults["flooring_exposure"],
        )
    
    @staticmethod
    def build(
        flooring: List[Flooring],
        dimensions: Dimensions,
        stories: int,
        floor_heights: List[float]
    ) -> cq.Assembly:
        """
        Build floor structures for all stories using individual tongue-and-groove planks.
        
        Args:
            flooring: List of flooring specifications (one per story + attic)
            dimensions: Building dimensions
            stories: Number of stories
            floor_heights: Pre-calculated floor heights for each story
            
        Returns:
            CadQuery Assembly with individual planks as separate components
        """
        
        scene_root = FloorBuilder._floor_scene(flooring, dimensions, stories, floor_heights)
        floor_assembly = cq.Assembly()
        project_scene_to_assembly(scene_root, floor_assembly)
        floor_assembly.scene_root = scene_root
        floor_assembly.scene_components = collect_component_metadata(scene_root)
        floor_assembly.validation_results = validate_floor_scene(scene_root)
        return floor_assembly
    
    @staticmethod
    def _floor_scene(
        flooring: List[Flooring],
        dimensions: Dimensions,
        stories: int,
        floor_heights: List[float],
    ) -> SceneNode:
        root = SceneNode("building", "building", "building")
        floors_node = root.add_child(SceneNode("floors", "assembly", "floors"))
        default_flooring = FloorBuilder._default_flooring()

        for floor_index in range(stories + 1):
            flooring_config = flooring[floor_index] if floor_index < len(flooring) else default_flooring
            floor_height = floor_heights[floor_index]
            floor_thickness = flooring_config.flooring_thickness
            floor_node = floors_node.add_child(
                SceneNode(
                    f"floor_{floor_index}",
                    "floor",
                    "floor",
                    local_transform=Transform.translate(0.0, 0.0, floor_height + floor_thickness / 2),
                    metadata={
                        "metrics": {
                            "floor_length": dimensions.front,
                            "plank_length": dimensions.left,
                            "floor_thickness": floor_thickness,
                        },
                        "coordinate_system": "cornerstone",
                    },
                )
            )
            FloorBuilder._add_floor_planks(floor_node, flooring_config, dimensions, floor_index)
        return root

    @staticmethod
    def _add_floor_planks(
        floor_node: SceneNode,
        flooring_config: Flooring,
        dimensions: Dimensions,
        floor_index: int,
    ) -> None:
        flooring_width = flooring_config.flooring_width
        flooring_exposure = flooring_config.flooring_exposure
        floor_thickness = flooring_config.flooring_thickness
        plank_length = dimensions.left
        defaults = FloorBuilder._config()["defaults"]
        plank_gap = defaults["plank_gap"]
        overlap = flooring_width - flooring_exposure
        tongue_width = overlap / 2
        groove_width = overlap / 2

        floor_length = dimensions.front
        spacing = flooring_exposure + plank_gap
        num_planks = int(floor_length / spacing) + 2

        for i in range(num_planks):
            plank_x = (flooring_width / 2) + (i * spacing)
            plank = FloorBuilder._create_tongue_groove_plank(
                flooring_width,
                plank_length,
                floor_thickness,
                tongue_width,
                groove_width
            )
            plank_name = f"floor_plank_floor{floor_index}_plank{i}"
            floor_node.add_child(
                SceneNode(
                    f"plank_{i}",
                    "part",
                    "floor_plank",
                    local_transform=Transform.translate(plank_x, -plank_length / 2, 0.0),
                    geometry=plank,
                    color=FloorBuilder._color(),
                    metadata={"component_name": plank_name},
                )
            )
    
    @staticmethod
    def _create_tongue_groove_plank(
        width: float,
        length: float,
        thickness: float,
        tongue_width: float,
        groove_width: float
    ) -> cq.Workplane:
        """
        Create a single tongue-and-groove plank.
        
        The plank has:
        - A tongue on one edge (extending beyond the main body)
        - A groove on the other edge (recessed into the main body)
        
        Args:
            width: Width of the plank (including tongue/groove)
            length: Length of the plank
            thickness: Thickness of the plank
            tongue_width: Width of the tongue extension
            groove_width: Width of the groove recess
            
        Returns:
            CadQuery Workplane with the plank geometry
        """
        main_width = width - tongue_width - groove_width
        defaults = FloorBuilder._config()["defaults"]

        main_body = (
            cq.Workplane("XY")
            .box(main_width, length, thickness)
        )
        tongue = (
            cq.Workplane("XY")
            .box(tongue_width, length, thickness)
            .translate((main_width / 2 + tongue_width / 2, 0, 0))
        )
        groove_cutout = (
            cq.Workplane("XY")
            .box(groove_width, length, thickness * defaults["groove_depth_ratio"])
            .translate((-(main_width / 2 + groove_width / 2), 0, -thickness * defaults["groove_vertical_offset_ratio"]))
        )
        plank = main_body.union(tongue).cut(groove_cutout)
        return plank
