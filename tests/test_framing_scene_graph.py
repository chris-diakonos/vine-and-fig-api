import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.models.structure import BuildingRequest, ComponentVisibility  # noqa: E402
from app.services.building_builder import BuildingBuilder  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
