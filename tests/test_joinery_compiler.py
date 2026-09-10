import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.services.joinery.base import JointSpec, box_at  # noqa: E402
from app.services.joinery.compiler import compile_joinery  # noqa: E402
from app.services.joinery.framing_handlers import FRAMING_JOINERY_HANDLERS  # noqa: E402
from app.services.scene_graph import SceneNode, Transform  # noqa: E402


class JoineryCompilerTest(unittest.TestCase):
    def test_compiler_preserves_blank_and_records_joined_geometry(self):
        root = SceneNode("building", "building", "building")
        framing = root.add_child(SceneNode("framing", "framing", "framing"))
        plates = framing.add_child(SceneNode("plates", "assembly", "plates"))
        left = plates.add_child(
            SceneNode(
                "plate_left",
                "part",
                "plate",
                local_transform=Transform.identity(),
                geometry=box_at((82.0, 4.0, 6.0), (-72.0, -2.0, 0.0)),
                metadata={"component_name": "plate_left"},
            )
        )
        right = plates.add_child(
            SceneNode(
                "plate_right",
                "part",
                "plate",
                local_transform=Transform.identity(),
                geometry=box_at((82.0, 4.0, 6.0), (-10.0, -2.0, 0.0)),
                metadata={"component_name": "plate_right"},
            )
        )

        operations = compile_joinery(
            root,
            [JointSpec("splice_1", "plate_splice", "plate_left", "plate_right")],
            FRAMING_JOINERY_HANDLERS,
        )

        self.assertEqual(len(operations), 10)
        self.assertIsNotNone(left.blank_geometry)
        self.assertIsNotNone(left.joined_geometry)
        self.assertIs(left.geometry, left.joined_geometry)
        self.assertEqual(left.metadata["joinery"]["operation_count"], 5)
        self.assertIsNotNone(right.blank_geometry)
        self.assertEqual(right.metadata["joinery"]["joint_ids"], ["splice_1"] * 5)


if __name__ == "__main__":
    unittest.main()
