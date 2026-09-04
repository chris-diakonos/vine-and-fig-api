import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.models.structure import BuildingRequest, ComponentVisibility  # noqa: E402
from app.services.building_builder import BuildingBuilder  # noqa: E402


class FoundationSceneGraphTest(unittest.TestCase):
    def _load_request(self, path: Path) -> BuildingRequest:
        with open(path, "r", encoding="utf-8") as handle:
            return BuildingRequest(**json.load(handle))

    def _foundation_only_visibility(self) -> ComponentVisibility:
        return ComponentVisibility(
            foundation=True,
            framing=False,
            floors=False,
            sheathing=False,
            roof=False,
            windows=False,
            doors=False,
        )

    def test_foundation_emits_scene_metadata_and_validation(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            request.structure_hash,
            self._foundation_only_visibility(),
        )

        self.assertEqual(model.validation_results["status"], "passed")
        paths = {component["semantic_path"] for component in model.scene_components}
        self.assertIn("building/foundation/course_0/front_wall/block_0", paths)
        self.assertIn("building/foundation/course_0/rear_wall/block_0", paths)
        self.assertIn("building/foundation/course_0/left_wall/block_0", paths)
        self.assertIn("building/foundation/course_0/right_wall/block_0", paths)

        components = {component["semantic_path"]: component for component in model.scene_components}
        block = components["building/foundation/course_0/front_wall/block_0"]
        self.assertNotEqual(block["local_transform"]["translation"], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(block["local_bounds"]["min"][0], -20.0)
        self.assertAlmostEqual(block["local_bounds"]["max"][0], 20.0)


if __name__ == "__main__":
    unittest.main()
