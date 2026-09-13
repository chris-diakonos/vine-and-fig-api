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
            cornice=False,
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

    def test_beaded_corner_treatment_adds_corner_boards_and_clips_sheathing(self):
        request = self._load_request(ROOT / "example_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            request.structure_hash,
            self._sheathing_only_visibility(),
        )

        by_name = {component["component_name"]: component for component in model.scene_components}
        corner_boards = [component for component in model.scene_components if component["role"] == "corner_board"]
        corner_beads = [component for component in model.scene_components if component["role"] == "corner_bead"]

        self.assertEqual(len(corner_boards), 8)
        self.assertEqual(len(corner_beads), 4)
        self.assertIn("building/sheathing/corner_trim/corner_board_front_left_cross", {
            component["semantic_path"] for component in corner_boards
        })
        self.assertAlmostEqual(by_name["corner_board_front_left_cross"]["world_bounds"]["size"][0], 4.0, places=5)
        self.assertAlmostEqual(by_name["corner_board_front_left_cross"]["world_bounds"]["size"][1], 1.0, places=5)
        self.assertAlmostEqual(by_name["corner_board_front_left_side"]["world_bounds"]["size"][0], 1.0, places=5)
        self.assertAlmostEqual(by_name["corner_board_front_left_side"]["world_bounds"]["size"][1], 4.0, places=5)
        self.assertAlmostEqual(
            by_name["sheathing_front_board1"]["world_bounds"]["min"][0],
            by_name["corner_board_front_left_cross"]["world_bounds"]["max"][0],
            places=5,
        )
        self.assertAlmostEqual(
            by_name["sheathing_left_board1"]["world_bounds"]["max"][1],
            by_name["corner_board_front_left_side"]["world_bounds"]["min"][1],
            places=5,
        )
        self.assertLess(by_name["corner_board_front_left_cross"]["world_bounds"]["min"][0], 0.0)


if __name__ == "__main__":
    unittest.main()
