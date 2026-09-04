import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.models.structure import BuildingRequest, ComponentVisibility  # noqa: E402
from app.services.building_builder import BuildingBuilder  # noqa: E402


class DoorSceneGraphTest(unittest.TestCase):
    def _load_request(self, path: Path) -> BuildingRequest:
        with open(path, "r", encoding="utf-8") as handle:
            return BuildingRequest(**json.load(handle))

    def _door_only_visibility(self) -> ComponentVisibility:
        return ComponentVisibility(
            foundation=False,
            framing=False,
            floors=False,
            sheathing=False,
            roof=False,
            windows=False,
            doors=True,
        )

    def test_doors_emit_scene_metadata_and_validation(self):
        request = self._load_request(ROOT / "example_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            request.structure_hash,
            self._door_only_visibility(),
        )

        self.assertEqual(model.validation_results["status"], "passed")
        paths = {component["semantic_path"] for component in model.scene_components}
        self.assertIn("building/doors/front_wall/story_1/door_240/slab", paths)

        components = {component["semantic_path"]: component for component in model.scene_components}
        door = components["building/doors/front_wall/story_1/door_240"]
        slab = components["building/doors/front_wall/story_1/door_240/slab"]
        self.assertEqual(door["metadata"]["local_bounds_datum"]["min"][2], 0.0)
        self.assertEqual(slab["component_name"], "door_0")


if __name__ == "__main__":
    unittest.main()
