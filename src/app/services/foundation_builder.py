"""
Foundation builder service using CadQuery.
"""
import cadquery as cq
from typing import Any, Dict, Tuple
from app.models.building import Foundation
from app.models.floorplan import Dimensions
from app.services.config_loader import load_json_config
from app.services.foundation_validation import validate_foundation_scene
from app.services.scene_graph import SceneNode, Transform, collect_component_metadata, project_scene_to_assembly


class FoundationBuilder:
    """Builds foundation geometry using CadQuery."""

    @staticmethod
    def _config() -> Dict[str, Any]:
        return load_json_config("foundation", "FOUNDATION_CONFIG_PATH")

    @staticmethod
    def _color() -> cq.Color:
        return cq.Color(*FoundationBuilder._config()["defaults"]["color"])

    @staticmethod
    def _metrics(foundation: Foundation, dimensions: Dimensions) -> Dict[str, float]:
        defaults = FoundationBuilder._config()["defaults"]
        if foundation.foundation_block_size and len(foundation.foundation_block_size) >= 3:
            block_length = foundation.foundation_block_size[0]
            block_width = foundation.foundation_block_size[1]
            block_height = foundation.foundation_block_size[2]
        else:
            block_length, block_width, block_height = defaults["block_size"]

        return {
            "block_length": block_length,
            "block_width": block_width,
            "block_height": block_height,
            "joint": foundation.foundation_block_joint,
            "courses": foundation.foundation_courses,
            "foundation_width": dimensions.front,
            "foundation_depth": dimensions.left,
        }
    
    @staticmethod
    def build(foundation: Foundation, dimensions: Dimensions) -> cq.Assembly:
        """
        Build the foundation structure.
        
        Args:
            foundation: Foundation specification
            dimensions: Building dimensions
            
        Returns:
            CadQuery Assembly with foundation geometry and color
        """
        scene_root = FoundationBuilder._foundation_scene(foundation, dimensions)
        foundation_assembly = cq.Assembly()
        project_scene_to_assembly(scene_root, foundation_assembly)
        foundation_assembly.scene_root = scene_root
        foundation_assembly.scene_components = collect_component_metadata(scene_root)
        foundation_assembly.validation_results = validate_foundation_scene(scene_root)
        return foundation_assembly

    @staticmethod
    def _foundation_scene(foundation: Foundation, dimensions: Dimensions) -> SceneNode:
        metrics = FoundationBuilder._metrics(foundation, dimensions)
        root = SceneNode("building", "building", "building")
        foundation_node = root.add_child(
            SceneNode(
                "foundation",
                "foundation",
                "foundation",
                metadata={
                    "metrics": metrics,
                    "coordinate_system": "cornerstone",
                },
            )
        )

        block_length = metrics["block_length"]
        block_width = metrics["block_width"]
        block_height = metrics["block_height"]
        joint = metrics["joint"]
        foundation_width = metrics["foundation_width"]
        foundation_depth = metrics["foundation_depth"]
        total_foundation_height = metrics["courses"] * (block_height + joint)

        for course_idx in range(int(metrics["courses"])):
            z_offset = -total_foundation_height + course_idx * (block_height + joint) + block_height / 2
            course_node = foundation_node.add_child(
                SceneNode(
                    f"course_{course_idx}",
                    "assembly",
                    "foundation_course",
                    local_transform=Transform.translate(0.0, 0.0, z_offset),
                )
            )
            FoundationBuilder._add_wall_blocks(
                course_node,
                wall="front",
                course_idx=course_idx,
                block_size=(block_length, block_width, block_height),
                start=0.0,
                limit=foundation_width,
                fixed_center=block_width / 2,
                along_x=True,
            )
            FoundationBuilder._add_wall_blocks(
                course_node,
                wall="rear",
                course_idx=course_idx,
                block_size=(block_length, block_width, block_height),
                start=0.0,
                limit=foundation_width,
                fixed_center=-foundation_depth + block_width / 2,
                along_x=True,
            )
            FoundationBuilder._add_wall_blocks(
                course_node,
                wall="left",
                course_idx=course_idx,
                block_size=(block_width, block_length, block_height),
                start=0.0,
                limit=foundation_depth,
                fixed_center=block_width / 2,
                along_x=False,
            )
            FoundationBuilder._add_wall_blocks(
                course_node,
                wall="right",
                course_idx=course_idx,
                block_size=(block_width, block_length, block_height),
                start=0.0,
                limit=foundation_depth,
                fixed_center=foundation_width - block_width / 2,
                along_x=False,
            )

        return root

    @staticmethod
    def _add_wall_blocks(
        course_node: SceneNode,
        wall: str,
        course_idx: int,
        block_size: Tuple[float, float, float],
        start: float,
        limit: float,
        fixed_center: float,
        along_x: bool,
    ) -> None:
        block_length = max(block_size[0], block_size[1])
        joint = course_node.parent.metadata["metrics"]["joint"] if course_node.parent else 0.0
        wall_node = course_node.add_child(SceneNode(f"{wall}_wall", "assembly", "foundation_wall"))
        position = start
        block_idx = 0
        while position + block_length <= limit:
            FoundationBuilder._add_block(wall_node, wall, course_idx, block_idx, block_size, position, fixed_center, along_x)
            position += block_length + joint
            block_idx += 1

        block_width = min(block_size[0], block_size[1])
        if position < limit - block_width:
            FoundationBuilder._add_block(wall_node, wall, course_idx, block_idx, block_size, position, fixed_center, along_x)

    @staticmethod
    def _add_block(
        wall_node: SceneNode,
        wall: str,
        course_idx: int,
        block_idx: int,
        block_size: Tuple[float, float, float],
        position: float,
        fixed_center: float,
        along_x: bool,
    ) -> None:
        block_x, block_y, block_z = block_size
        center = (
            position + block_x / 2 if along_x else fixed_center,
            fixed_center if along_x else -position - block_y / 2,
            0.0,
        )
        component_name = f"foundation_{wall}_c{course_idx}_b{block_idx}"
        wall_node.add_child(
            SceneNode(
                f"block_{block_idx}",
                "part",
                "foundation_block",
                local_transform=Transform.translate(*center),
                geometry=cq.Workplane("XY").box(block_x, block_y, block_z),
                color=FoundationBuilder._color(),
                metadata={"component_name": component_name},
            )
        )
