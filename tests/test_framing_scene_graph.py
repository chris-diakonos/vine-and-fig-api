import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.models.structure import BuildingRequest, ComponentVisibility  # noqa: E402
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
        self.assertEqual(model.scene_root.metadata["joinery_operation_count"], 0)
        names = {component["component_name"] for component in model.scene_components}
        self.assertIn("sill_front_1", names)


if __name__ == "__main__":
    unittest.main()
