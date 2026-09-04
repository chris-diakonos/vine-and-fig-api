import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.models.structure import BuildingRequest, ComponentVisibility  # noqa: E402
from app.services.building_builder import BuildingBuilder  # noqa: E402


class SheathingSceneGraphTest(unittest.TestCase):
    def _load_request(self, path: Path) -> BuildingRequest:
        with open(path, "r", encoding="utf-8") as handle:
            return BuildingRequest(**json.load(handle))

    def _sheathing_only_visibility(self) -> ComponentVisibility:
        return ComponentVisibility(
            foundation=False,
            framing=False,
            floors=False,
            sheathing=True,
            roof=False,
            windows=False,
            doors=False,
        )

    def test_sheathing_emits_scene_metadata_and_validation(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            request.structure_hash,
            self._sheathing_only_visibility(),
        )

        self.assertEqual(model.validation_results["status"], "passed")
        paths = {component["semantic_path"] for component in model.scene_components}
        self.assertTrue(any(path.startswith("building/sheathing/front_wall/") for path in paths))
        self.assertTrue(any(path.startswith("building/gable_sheathing/left_gable/") for path in paths))


if __name__ == "__main__":
    unittest.main()
