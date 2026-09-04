import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.models.structure import BuildingRequest, ComponentVisibility  # noqa: E402
from app.services.building_builder import BuildingBuilder  # noqa: E402
from app.services.coordinate_system import window_placement_for_wall  # noqa: E402
from app.services.model_generator import ModelGenerator  # noqa: E402


class WindowSceneGraphTest(unittest.TestCase):
    def _load_request(self, path: Path) -> BuildingRequest:
        with open(path, "r", encoding="utf-8") as handle:
            return BuildingRequest(**json.load(handle))

    def _window_only_visibility(self) -> ComponentVisibility:
        return ComponentVisibility(
            foundation=False,
            framing=False,
            floors=False,
            sheathing=False,
            roof=False,
            windows=True,
            doors=False,
        )

    def test_minimal_window_fixture_emits_scene_metadata_and_validation(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            request.structure_hash,
            self._window_only_visibility(),
        )

        self.assertTrue(hasattr(model, "scene_components"))
        self.assertTrue(hasattr(model, "validation_results"))
        self.assertEqual(model.validation_results["status"], "passed")

        paths = {component["semantic_path"] for component in model.scene_components}
        self.assertIn("building/windows/front_wall/story_1/window_120/lower_sash/left_stile", paths)
        self.assertIn("building/windows/front_wall/story_1/window_120/upper_sash/right_stile", paths)
        self.assertIn("building/windows/front_wall/story_1/window_120/lower_sash/glass_0_0", paths)
        self.assertIn("building/windows/front_wall/story_1/window_120/upper_sash/glass_0_0", paths)

        window_results = model.validation_results["results"]
        self.assertTrue(all(not result["warnings"] for result in window_results))

    def test_example_request_window_validation_passes(self):
        request = self._load_request(ROOT / "example_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            request.structure_hash,
            self._window_only_visibility(),
        )

        self.assertEqual(model.validation_results["status"], "passed")
        window_components = [
            component
            for component in model.scene_components
            if component["type"] == "window"
        ]
        self.assertGreaterEqual(len(window_components), 1)

    def test_cornerstone_window_placement_projects_to_legacy_front_wall(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")
        window = request.structure.windows[0]
        metrics = {"opening_width": 40.5}

        placement = window_placement_for_wall(
            "front",
            window.position,
            40.0,
            metrics["opening_width"],
            request.structure.floorplan.dimensions,
        )

        self.assertEqual(placement.cornerstone_origin.as_tuple(), (99.75, 0.0, 40.0))
        self.assertEqual(placement.legacy_transform.translation, (99.75, 0.0, 40.0))

    def test_headless_artifact_generation_writes_scene_files(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = ModelGenerator.generate_glb_artifacts(
                request.structure,
                Path(temp_dir),
                structure_hash="window-scene-test",
                component_visibility=self._window_only_visibility(),
            )

            self.assertTrue(artifacts["components_path"].exists())
            self.assertTrue(artifacts["validation_path"].exists())

            with open(artifacts["validation_path"], "r", encoding="utf-8") as handle:
                validation = json.load(handle)
            self.assertEqual(validation["status"], "passed")
        self.assertTrue(all(not result["warnings"] for result in validation["results"]))


if __name__ == "__main__":
    unittest.main()
