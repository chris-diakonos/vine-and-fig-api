import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.services.joinery.base import apply_operations, box_at, workplane_bounds, workplane_volume  # noqa: E402
from app.services.joinery.half_lap import default_bearing_notch_params, joist_bearing_notch  # noqa: E402
from app.services.joinery.joist_to_sill import joist_to_sill_operations  # noqa: E402
from app.services.joinery.mortise_tenon import default_stub_tenon_params, stud_to_sill_fixture  # noqa: E402
from app.services.joinery.plate_splice import plate_splice_fixture  # noqa: E402
from app.services.joinery.post_to_sill_corner import post_to_sill_corner_fixture  # noqa: E402


class JoineryPrimitiveTest(unittest.TestCase):
    def assertBoundsAlmostEqual(self, actual, expected, places=5):
        for actual_point, expected_point in zip(actual, expected):
            for actual_value, expected_value in zip(actual_point, expected_point):
                self.assertAlmostEqual(actual_value, expected_value, places=places)

    def test_stud_stub_tenons_match_reference_extent(self):
        stud, sill, girder = stud_to_sill_fixture(default_stub_tenon_params())

        self.assertBoundsAlmostEqual(workplane_bounds(stud), ((-1.5, -2.0, -2.0), (1.5, 2.0, 114.0)))
        self.assertLess(workplane_volume(sill), 48.0 * 8.0 * 10.0)
        self.assertLess(workplane_volume(girder), 48.0 * 4.0 * 6.0)

    def test_plate_splice_preserves_reference_extents_and_bores(self):
        left, right = plate_splice_fixture()

        self.assertBoundsAlmostEqual(workplane_bounds(left), ((-72.0, -2.0, 0.0), (10.0, 2.0, 6.0)))
        self.assertBoundsAlmostEqual(workplane_bounds(right), ((-10.0, -2.0, 0.0), (72.0, 2.0, 6.0)))
        self.assertLess(workplane_volume(left), 82.0 * 4.0 * 6.0)
        self.assertLess(workplane_volume(right), 82.0 * 4.0 * 6.0)

    def test_post_to_sill_corner_preserves_reference_extents(self):
        sill_x, sill_y, post = post_to_sill_corner_fixture()

        self.assertBoundsAlmostEqual(workplane_bounds(sill_x), ((0.0, -4.0, 0.0), (72.0, 4.0, 10.0)))
        self.assertBoundsAlmostEqual(workplane_bounds(sill_y), ((-4.0, 0.0, 0.0), (4.0, 72.0, 10.0)))
        self.assertBoundsAlmostEqual(workplane_bounds(post), ((-3.0, -2.0, 5.0), (3.0, 2.0, 106.0)))
        self.assertLess(workplane_volume(sill_y), 8.0 * 72.0 * 10.0)

    def test_joist_bearing_notch_cuts_reference_plate_overlap(self):
        joist = box_at((144.0, 3.0, 8.0), (-12.0, -1.5, 4.0))
        op = joist_bearing_notch(
            "joist",
            plate_x0=0.0,
            joist_y0=-1.5,
            joist_thickness=3.0,
            joist_bottom_z=4.0,
            params=default_bearing_notch_params(),
        )
        joined = apply_operations(joist, [op])

        self.assertBoundsAlmostEqual(workplane_bounds(joined), workplane_bounds(joist))
        self.assertLess(workplane_volume(joined), workplane_volume(joist))

    def test_joist_to_sill_adds_tail_and_cuts_socket(self):
        joist = box_at((3.0, 72.0, 8.0), (0.0, 0.0, 0.0))
        sill = box_at((48.0, 8.0, 10.0), (0.0, 0.0, 0.0))
        operations = joist_to_sill_operations(
            "joist",
            "sill",
            joist_end_y=72.0,
            joist_top_z=8.0,
            sill_socket_center=(24.0, 4.0),
            sill_top_z=10.0,
            direction=1,
        )

        joined_joist = apply_operations(joist, [op for op in operations if op.member_id == "joist"])
        joined_sill = apply_operations(sill, [op for op in operations if op.member_id == "sill"])

        self.assertGreater(workplane_volume(joined_joist), workplane_volume(joist))
        self.assertLess(workplane_volume(joined_sill), workplane_volume(sill))
        self.assertGreater(workplane_bounds(joined_joist)[1][1], workplane_bounds(joist)[1][1])


if __name__ == "__main__":
    unittest.main()
