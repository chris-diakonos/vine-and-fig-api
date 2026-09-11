import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.models.structure import BuildingRequest, ComponentVisibility  # noqa: E402
from app.services.building_builder import BuildingBuilder  # noqa: E402


class NonFramingDatumContextTest(unittest.TestCase):
    def _load_request(self, path: Path) -> BuildingRequest:
        with open(path, "r", encoding="utf-8") as handle:
            return BuildingRequest(**json.load(handle))

    def _visibility(self, **enabled) -> ComponentVisibility:
        return ComponentVisibility(
            foundation=False,
            framing=enabled.get("framing", True),
            floors=enabled.get("floors", False),
            sheathing=enabled.get("sheathing", False),
            roof=False,
            windows=enabled.get("windows", False),
            doors=enabled.get("doors", False),
        )

    def test_floor_surface_uses_joist_top_datums(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            "floor-datum-context-test",
            self._visibility(floors=True),
        )

        components = {component["semantic_path"]: component for component in model.scene_components}
        by_name = {component["component_name"]: component for component in model.scene_components}
        floor = components["building/floors/floor_0"]
        joist_top = by_name["joist_story1_1"]["world_bounds"]["max"][2]
        floor_thickness = floor["metadata"]["metrics"]["floor_thickness"]
        self.assertEqual(floor["metadata"]["placement_source"], "framing_datums")
        self.assertAlmostEqual(floor["local_transform"]["translation"][2], joist_top + floor_thickness / 2.0)

    def test_sheathing_marks_frame_datum_placement(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            "sheathing-datum-context-test",
            self._visibility(sheathing=True),
        )

        components = {component["semantic_path"]: component for component in model.scene_components}
        by_name = {component["component_name"]: component for component in model.scene_components}
        self.assertEqual(components["building/sheathing"]["metadata"]["placement_source"], "framing_datums")
        self.assertEqual(components["building/gable_sheathing"]["metadata"]["placement_source"], "framing_datums")
        planes = {
            "front": by_name["post_front_left"]["world_bounds"]["max"][1],
            "rear": by_name["post_rear_left"]["world_bounds"]["min"][1],
            "left": by_name["post_front_left"]["world_bounds"]["min"][0],
            "right": by_name["post_front_right"]["world_bounds"]["max"][0],
        }
        self.assertAlmostEqual(by_name["sheathing_front_board1"]["world_bounds"]["min"][1], planes["front"], places=5)
        self.assertAlmostEqual(by_name["sheathing_rear_board1"]["world_bounds"]["max"][1], planes["rear"], places=5)
        self.assertAlmostEqual(by_name["sheathing_left_board1"]["world_bounds"]["max"][0], planes["left"], places=5)
        self.assertAlmostEqual(by_name["sheathing_right_board1"]["world_bounds"]["min"][0], planes["right"], places=5)
        self.assertAlmostEqual(by_name["gable_sheathing_left_board1"]["world_bounds"]["max"][0], planes["left"], places=5)
        self.assertAlmostEqual(by_name["gable_sheathing_right_board1"]["world_bounds"]["min"][0], planes["right"], places=5)

    def test_windows_use_framing_wall_plane(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            "window-datum-context-test",
            self._visibility(windows=True),
        )

        components = {component["semantic_path"]: component for component in model.scene_components}
        by_name = {component["component_name"]: component for component in model.scene_components}
        window = components["building/windows/front_wall/story_1/window_120"]
        sill = components["building/windows/front_wall/story_1/window_120/frame/bottom_frame_sill"]
        front_plane = by_name["post_front_left"]["world_bounds"]["max"][1]
        self.assertEqual(window["metadata"]["placement"]["source"], "framing_datums")
        self.assertAlmostEqual(sill["world_bounds"]["min"][1], front_plane, places=5)

    def test_second_story_window_uses_cripple_sill_and_centered_sashes(self):
        request = self._load_request(ROOT / "example_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            "window-cripple-sill-test",
            self._visibility(windows=True),
        )

        components = {component["semantic_path"]: component for component in model.scene_components}
        by_name = {component["component_name"]: component for component in model.scene_components}
        path = "building/windows/front_wall/story_2/window_80"
        front_plane = by_name["post_front_left"]["world_bounds"]["max"][1]
        cripple_top = by_name["cripple_stud_front_story2_bay1"]["world_bounds"]["max"][2]
        sill = components[f"{path}/frame/bottom_frame_sill"]
        lower_left = components[f"{path}/lower_sash/left_stile"]
        lower_right = components[f"{path}/lower_sash/right_stile"]
        upper_left = components[f"{path}/upper_sash/left_stile"]

        lower_sash_center = (lower_left["world_bounds"]["min"][0] + lower_right["world_bounds"]["max"][0]) / 2.0
        sash_gap = upper_left["world_bounds"]["min"][2] - lower_left["world_bounds"]["max"][2]
        self.assertAlmostEqual(sill["world_bounds"]["min"][2], cripple_top, places=5)
        self.assertAlmostEqual(sill["world_bounds"]["min"][1], front_plane, places=5)
        self.assertAlmostEqual(lower_sash_center, 80.0, places=5)
        self.assertLessEqual(sash_gap, 0.25 + 1e-5)

    def test_doors_use_framing_wall_plane(self):
        request = self._load_request(ROOT / "example_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            "door-datum-context-test",
            self._visibility(doors=True),
        )

        components = {component["semantic_path"]: component for component in model.scene_components}
        by_name = {component["component_name"]: component for component in model.scene_components}
        door = components["building/doors/front_wall/story_1/door_240"]
        front_plane = by_name["post_front_left"]["world_bounds"]["max"][1]
        self.assertEqual(door["metadata"]["placement_source"], "framing_datums")
        self.assertAlmostEqual(door["local_transform"]["translation"][1], front_plane, places=5)

    def test_cornice_cavetto_is_flush_to_ceiling_joist_ends(self):
        request = self._load_request(ROOT / "tests" / "fixtures" / "minimal_window_request.json")

        model, _ = BuildingBuilder.build(
            request.structure,
            "cornice-datum-context-test",
            self._visibility(),
        )

        components = {component["semantic_path"]: component for component in model.scene_components}
        by_name = {component["component_name"]: component for component in model.scene_components}
        ceiling_joist_front_plane = max(
            component["world_bounds"]["max"][1]
            for component in by_name.values()
            if component["component_name"] and component["component_name"].startswith("joist_story2_")
        )
        cavetto = by_name["front_cavetto"]
        self.assertEqual(components["building/cornice"]["metadata"]["placement_source"], "framing_datums")
        self.assertAlmostEqual(cavetto["world_bounds"]["min"][1], ceiling_joist_front_plane)


if __name__ == "__main__":
    unittest.main()
