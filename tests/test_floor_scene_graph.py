import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.models.structure import BuildingRequest, ComponentVisibility  # noqa: E402
from app.services.building_builder import BuildingBuilder  # noqa: E402


class FloorSceneGraphTest(unittest.TestCase):
    def _load_request(self, path: Path) -> BuildingRequest:
        with open(path, "r", encoding="utf-8") as handle:
            return BuildingRequest(**json.load(handle))

    def _floor_only_visibility(self) -> ComponentVisibility:
        return ComponentVisibility(
            foundation=False,
            framing=False,
            floors=True,
            sheathing=False,
            roof=False,
            windows=False,
            doors=False,
        )

    def test_floors_emit_scene_metadata_and_validation(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            request.structure_hash,
            self._floor_only_visibility(),
        )

        self.assertEqual(model.validation_results["status"], "passed")
        paths = {component["semantic_path"] for component in model.scene_components}
        self.assertIn("building/floors/floor_0/plank_0", paths)

        components = {component["semantic_path"]: component for component in model.scene_components}
        floor = components["building/floors/floor_0"]
        plank = components["building/floors/floor_0/plank_0"]
        self.assertNotEqual(floor["local_transform"]["translation"], [0.0, 0.0, 0.0])
        self.assertNotEqual(plank["local_transform"]["translation"], [0.0, 0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
