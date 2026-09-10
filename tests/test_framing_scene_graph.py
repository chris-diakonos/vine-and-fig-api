import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.models.structure import BuildingRequest, ComponentVisibility  # noqa: E402
from app.services.joinery.base import workplane_volume  # noqa: E402
from app.services.building_builder import BuildingBuilder  # noqa: E402
from app.services.framing_builder import FramingBuilder  # noqa: E402


class FramingSceneGraphTest(unittest.TestCase):
    def _load_request(self, path: Path) -> BuildingRequest:
        with open(path, "r", encoding="utf-8") as handle:
            return BuildingRequest(**json.load(handle))

    def _framing_only_visibility(self) -> ComponentVisibility:
        return ComponentVisibility(
            foundation=False,
            framing=True,
            floors=False,
            sheathing=False,
            roof=False,
            windows=False,
            doors=False,
        )

    def test_framing_emits_scene_metadata_and_preserves_bom(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        model, bom_data = BuildingBuilder.build(
            request.structure,
            request.structure_hash or "framing-scene-test",
            self._framing_only_visibility(),
        )

        self.assertIsNotNone(bom_data)
        self.assertEqual(model.validation_results["status"], "passed")
        paths = {component["semantic_path"] for component in model.scene_components}
        self.assertTrue(any(path.startswith("building/framing/sills/") for path in paths))

    def test_framing_joinery_compile_flag_preserves_existing_names(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")
        builder = FramingBuilder(request.structure, request.structure_hash or "joinery-flag-test")
        floorplan = request.structure.floorplan
        ceiling_heights = BuildingBuilder.calculate_ceiling_heights(
            floorplan.stories,
            floorplan.joist_heights or [10, 9, 8],
            floorplan.ceiling_heights or [120, 108],
        )
        floor_heights = BuildingBuilder.calculate_floor_heights(
            floorplan.stories,
            floorplan.joist_heights or [10, 9, 8],
            floorplan.ceiling_heights or [120, 108],
        )

        model, bom_data = builder.build(ceiling_heights, floor_heights, compile_joinery=True)

        self.assertIsNotNone(bom_data)
        self.assertTrue(model.scene_root.metadata["compile_joinery"])
        self.assertEqual(model.scene_root.metadata["joinery_joint_count"], 4)
        self.assertEqual(model.scene_root.metadata["joinery_operation_count"], 28)
        components = {component["component_name"]: component for component in model.scene_components}
        names = set(components)
        self.assertIn("sill_front_1", names)
        self.assertTrue(components["sill_front_1"]["has_joined_geometry"])
        self.assertTrue(components["sill_left_1"]["has_joined_geometry"])
        self.assertTrue(components["post_front_left"]["has_joined_geometry"])
        specs = builder._declare_joinery_specs()
        self.assertEqual(len(specs), 4)
        for spec in specs:
            self.assertIn("joint_datums", spec.params)
            self.assertEqual(spec.params["joint_datums"]["tenon_height"], 2.0)

        unjoined_builder = FramingBuilder(request.structure, request.structure_hash or "joinery-flag-test")
        unjoined_model, _ = unjoined_builder.build(ceiling_heights, floor_heights, compile_joinery=False)
        joined_post = self._scene_node(model.scene_root, "post_front_left")
        unjoined_post = self._scene_node(unjoined_model.scene_root, "post_front_left")
        joined_sill = self._scene_node(model.scene_root, "sill_left_1")
        unjoined_sill = self._scene_node(unjoined_model.scene_root, "sill_left_1")

        self.assertLess(workplane_volume(joined_post.geometry), workplane_volume(unjoined_post.geometry))
        self.assertLess(workplane_volume(joined_sill.geometry), workplane_volume(unjoined_sill.geometry))

    def test_cornerstone_sills_and_posts_match_legacy_reference_bounds(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")
        floorplan = request.structure.floorplan
        ceiling_heights = BuildingBuilder.calculate_ceiling_heights(
            floorplan.stories,
            floorplan.joist_heights or [10, 9, 8],
            floorplan.ceiling_heights or [120, 108],
        )
        floor_heights = BuildingBuilder.calculate_floor_heights(
            floorplan.stories,
            floorplan.joist_heights or [10, 9, 8],
            floorplan.ceiling_heights or [120, 108],
        )

        legacy_model = FramingBuilder(request.structure, "legacy-reference-test").build_legacy_reference(
            ceiling_heights,
            floor_heights,
            compile_joinery=False,
        )
        cornerstone_model, _ = FramingBuilder(request.structure, "cornerstone-reference-test").build(
            ceiling_heights,
            floor_heights,
            compile_joinery=False,
        )

        legacy_components = {component["component_name"]: component for component in legacy_model.scene_components}
        cornerstone_components = {component["component_name"]: component for component in cornerstone_model.scene_components}
        migrated_names = {
            name for name in cornerstone_components
            if name and (name.startswith("sill_") or name.startswith("post_"))
        }

        self.assertEqual(
            migrated_names,
            {name for name in legacy_components if name and (name.startswith("sill_") or name.startswith("post_"))},
        )
        for name in migrated_names:
            self._assert_bounds_almost_equal(
                cornerstone_components[name]["world_bounds"],
                legacy_components[name]["world_bounds"],
            )
            cornerstone_node = self._scene_node(cornerstone_model.scene_root, name)
            legacy_node = self._scene_node(legacy_model.scene_root, name)
            self.assertAlmostEqual(
                workplane_volume(cornerstone_node.geometry),
                workplane_volume(legacy_node.geometry),
                places=5,
            )
            self.assertIn("framing_datums", cornerstone_node.metadata)

    def test_side_sills_follow_left_and_right_wall_lines(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")
        floorplan = request.structure.floorplan
        ceiling_heights = BuildingBuilder.calculate_ceiling_heights(
            floorplan.stories,
            floorplan.joist_heights or [10, 9, 8],
            floorplan.ceiling_heights or [120, 108],
        )
        floor_heights = BuildingBuilder.calculate_floor_heights(
            floorplan.stories,
            floorplan.joist_heights or [10, 9, 8],
            floorplan.ceiling_heights or [120, 108],
        )

        model, _ = FramingBuilder(request.structure, "side-sill-placement-test").build(
            ceiling_heights,
            floor_heights,
            compile_joinery=False,
        )

        components = {component["component_name"]: component for component in model.scene_components}
        self._assert_bounds_almost_equal(
            components["sill_left_1"]["world_bounds"],
            {"min": [-4.0, -240.0, 0.0], "max": [4.0, 0.0, 10.0], "size": [8.0, 240.0, 10.0]},
        )
        self._assert_bounds_almost_equal(
            components["sill_right_1"]["world_bounds"],
            {"min": [236.0, -240.0, 0.0], "max": [244.0, 0.0, 10.0], "size": [8.0, 240.0, 10.0]},
        )

    def _scene_node(self, scene_root, component_name):
        for node in scene_root.iter_nodes():
            if node.metadata.get("component_name") == component_name:
                return node
        self.fail(f"Missing scene node: {component_name}")

    def _assert_bounds_almost_equal(self, actual, expected, places=5):
        for key in ("min", "max", "size"):
            for actual_value, expected_value in zip(actual[key], expected[key]):
                self.assertAlmostEqual(actual_value, expected_value, places=places)


if __name__ == "__main__":
    unittest.main()
