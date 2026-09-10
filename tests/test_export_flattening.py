import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import cadquery as cq


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.cli import build_parser  # noqa: E402
from app.services.config_loader import load_json_config  # noqa: E402
from app.services.export_service import ExportService, GlbFlattenOptions  # noqa: E402
from app.services.model_generator import ModelGenerator  # noqa: E402


class ExportFlatteningTest(unittest.TestCase):
    def test_flattening_preserves_framing_and_groups_non_framing(self):
        assembly = cq.Assembly()
        assembly.add(cq.Workplane("XY").box(1, 1, 1), name="sill_front_1", color=cq.Color(0.55, 0.45, 0.33))
        assembly.add(cq.Workplane("XY").box(1, 1, 1).translate((2, 0, 0)), name="joist_story1_1", color=cq.Color(0.55, 0.45, 0.33))
        assembly.add(cq.Workplane("XY").box(1, 1, 1).translate((0, 2, 0)), name="window_a_frame", color=cq.Color(0.8, 0.7, 0.6))
        assembly.add(cq.Workplane("XY").box(1, 1, 1).translate((0, 4, 0)), name="window_b_frame", color=cq.Color(0.8, 0.7, 0.6))
        assembly.add(cq.Workplane("XY").box(1, 1, 1).translate((0, 6, 0)), name="roof_panel_1", color=cq.Color(0.3, 0.3, 0.3))

        flattened = ExportService.flatten_assembly_for_gltf(assembly, GlbFlattenOptions(enabled=True))
        names = {name for name, obj_data in flattened.traverse() if getattr(obj_data, "obj", None) is not None}

        self.assertLess(len(list(flattened.traverse())), len(list(assembly.traverse())))
        self.assertIn("sill_front_1", names)
        self.assertIn("joist_story1_1", names)
        self.assertTrue(any(name.startswith("windows_flattened_") for name in names))
        self.assertTrue(any(name.startswith("roof_flattened_") for name in names))
        self.assertNotIn("window_a_frame", names)
        self.assertNotIn("window_b_frame", names)

    def test_flattening_only_groups_enabled_subsystems(self):
        assembly = cq.Assembly()
        assembly.add(cq.Workplane("XY").box(1, 1, 1), name="window_a_frame", color=cq.Color(0.8, 0.7, 0.6))
        assembly.add(cq.Workplane("XY").box(1, 1, 1).translate((0, 2, 0)), name="roof_panel_1", color=cq.Color(0.3, 0.3, 0.3))
        assembly.add(cq.Workplane("XY").box(1, 1, 1).translate((0, 4, 0)), name="roof_panel_2", color=cq.Color(0.3, 0.3, 0.3))

        flattened = ExportService.flatten_assembly_for_gltf(
            assembly,
            GlbFlattenOptions(enabled=True, flatten_layers=("roof",), preserve_layers=()),
        )
        names = {name for name, obj_data in flattened.traverse() if getattr(obj_data, "obj", None) is not None}

        self.assertIn("window_a_frame", names)
        self.assertTrue(any(name.startswith("roof_flattened_") for name in names))
        self.assertNotIn("roof_panel_1", names)
        self.assertNotIn("roof_panel_2", names)

    def test_cli_accepts_flatten_glb_flag(self):
        parser = build_parser()
        args = parser.parse_args(["generate", "example_request.json", "--flatten-glb"])

        self.assertTrue(args.flatten_glb)

    def test_cli_inherits_config_when_flatten_flag_is_omitted(self):
        parser = build_parser()
        args = parser.parse_args(["generate", "example_request.json"])

        self.assertIsNone(args.flatten_glb)

    def test_cli_can_disable_config_flattening(self):
        parser = build_parser()
        args = parser.parse_args(["generate", "example_request.json", "--no-flatten-glb"])

        self.assertFalse(args.flatten_glb)

    def test_model_generator_reads_flatten_default_from_building_config(self):
        previous_path = os.environ.get("BUILDING_CONFIG_PATH")
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "building.json"
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump({"defaults": {}, "export": {"flatten_glb": True}}, handle)

            os.environ["BUILDING_CONFIG_PATH"] = str(config_path)
            load_json_config.cache_clear()
            try:
                self.assertTrue(ModelGenerator.default_flatten_glb())
            finally:
                if previous_path is None:
                    os.environ.pop("BUILDING_CONFIG_PATH", None)
                else:
                    os.environ["BUILDING_CONFIG_PATH"] = previous_path
                load_json_config.cache_clear()

    def test_model_generator_reads_flatten_subsystem_defaults_from_building_config(self):
        previous_path = os.environ.get("BUILDING_CONFIG_PATH")
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "building.json"
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "defaults": {},
                        "export": {
                            "flatten_glb": True,
                            "flatten_subsystems": {
                                "windows": False,
                                "roof": True,
                            },
                        },
                    },
                    handle,
                )

            os.environ["BUILDING_CONFIG_PATH"] = str(config_path)
            load_json_config.cache_clear()
            try:
                options = ModelGenerator.default_flatten_options()
                self.assertTrue(options.enabled)
                self.assertNotIn("windows", options.flatten_layers)
                self.assertIn("roof", options.flatten_layers)
                self.assertNotIn("framing", options.flatten_layers)
            finally:
                if previous_path is None:
                    os.environ.pop("BUILDING_CONFIG_PATH", None)
                else:
                    os.environ["BUILDING_CONFIG_PATH"] = previous_path
                load_json_config.cache_clear()


if __name__ == "__main__":
    unittest.main()
