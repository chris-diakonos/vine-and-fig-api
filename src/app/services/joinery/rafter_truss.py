"""Notebook-derived rafter truss geometry."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Tuple

import cadquery as cq

from app.services.scene_graph import bounds_for_workplane

Point2 = Tuple[float, float]


@dataclass(frozen=True)
class RafterTrussParams:
    rafter_thickness: float
    rafter_depth: float
    roof_angle_degrees: float
    bearing_span: float
    collar_height: float
    collar_drop_from_ridge: float
    seat_depth: float
    cut_margin: float
    y_overlap: float


@dataclass(frozen=True)
class RafterTrussGeometry:
    front_rafter: cq.Workplane
    rear_rafter: cq.Workplane
    collar: cq.Workplane
    metadata: Dict[str, float]


def rafter_truss_geometry(params: RafterTrussParams) -> RafterTrussGeometry:
    """Return front/rear rafters and collar in truss-local coordinates.

    The notebook uses XZ as the truss section and Y as member thickness. This
    helper rotates the completed solids so local Y spans rear-to-front in the
    building and local X is the station/thickness direction.
    """

    values = _rafter_values(params)
    front = _map_notebook_section_to_truss(_front_rafter(values, params))
    rear = _map_notebook_section_to_truss(_rear_rafter(values, params))
    collar = _map_notebook_section_to_truss(_collar(values, params))
    front_bounds = bounds_for_workplane(front)
    rear_bounds = bounds_for_workplane(rear)
    z_shift = 0.0
    if front_bounds is not None and rear_bounds is not None:
        z_shift = -min(front_bounds.min[2], rear_bounds.min[2])
        front = front.translate((0.0, 0.0, z_shift))
        rear = rear.translate((0.0, 0.0, z_shift))
        collar = collar.translate((0.0, 0.0, z_shift))
    return RafterTrussGeometry(
        front_rafter=front,
        rear_rafter=rear,
        collar=collar,
        metadata={
            "roof_angle_degrees": params.roof_angle_degrees,
            "ridge_angle_degrees": values["ridge_degrees"],
            "rafter_length": values["rafter_length"],
            "rafter_run": values["rafter_run"],
            "rafter_rise": values["rafter_rise"],
            "tail_z_shift": z_shift,
        },
    )


def _rafter_values(params: RafterTrussParams) -> Dict[str, float]:
    angle = math.radians(params.roof_angle_degrees)
    rafter_run = params.bearing_span / 2.0
    rafter_length = rafter_run / math.cos(angle)
    rafter_rise = rafter_run * math.tan(angle)
    ridge_degrees = 180.0 - 2.0 * params.roof_angle_degrees
    if ridge_degrees <= 0.0:
        raise ValueError(f"Invalid roof angle for rafter truss: {params.roof_angle_degrees}")
    return {
        "a": angle,
        "slope_sin": math.sin(angle),
        "slope_cos": math.cos(angle),
        "rafter_run": rafter_run,
        "rafter_length": rafter_length,
        "rafter_rise": rafter_rise,
        "ridge_z": rafter_rise,
        "ridge_degrees": ridge_degrees,
        "bearing_x": rafter_length,
        "z_bottom": -params.rafter_depth / 2.0,
        "z_top": params.rafter_depth / 2.0,
        "half_crossing": params.rafter_depth / (2.0 * math.sin(angle)),
        "collar_center_z": rafter_rise - params.collar_drop_from_ridge,
    }


def _front_rafter(values: Dict[str, float], params: RafterTrussParams) -> cq.Workplane:
    a = values["a"]
    z_bottom = values["z_bottom"]
    z_top = values["z_top"]
    bearing_x = values["bearing_x"]
    ridge = _ridge_lap_coords(+1, values, params)
    lower_x_bottom = bearing_x + z_bottom / math.tan(a)
    lower_x_top = bearing_x + z_top / math.tan(a)
    body = _xz_solid(
        [
            (ridge[0], z_bottom),
            (ridge[1], z_top),
            (lower_x_top, z_top),
            (lower_x_bottom, z_bottom),
        ],
        params.rafter_thickness,
    )
    lap = _xz_solid(
        [
            (ridge[0], z_bottom),
            (ridge[1], z_top),
            (ridge[3], z_top),
            (ridge[2], z_bottom),
        ],
        params.rafter_thickness / 2.0,
    ).translate((0.0, params.rafter_thickness / 4.0, 0.0))
    return _place_notebook_rafter(body.cut(lap), params.roof_angle_degrees, values["ridge_z"])


def _rear_rafter(values: Dict[str, float], params: RafterTrussParams) -> cq.Workplane:
    a = values["a"]
    z_bottom = values["z_bottom"]
    z_top = values["z_top"]
    bearing_x = values["bearing_x"]
    ridge = _ridge_lap_coords(-1, values, params)
    lower_x_bottom = bearing_x - z_bottom / math.tan(a)
    lower_x_top = bearing_x - z_top / math.tan(a)
    body = _xz_solid(
        [
            (ridge[0], z_bottom),
            (ridge[1], z_top),
            (lower_x_top, z_top),
            (lower_x_bottom, z_bottom),
        ],
        params.rafter_thickness,
    )
    lap = _xz_solid(
        [
            (ridge[0], z_bottom),
            (ridge[1], z_top),
            (ridge[3], z_top),
            (ridge[2], z_bottom),
        ],
        params.rafter_thickness / 2.0,
    ).translate((0.0, -params.rafter_thickness / 4.0, 0.0))
    return _place_notebook_rafter(body.cut(lap), 180.0 - params.roof_angle_degrees, values["ridge_z"])


def _collar(values: Dict[str, float], params: RafterTrussParams) -> cq.Workplane:
    points = _collar_points(values, params)
    collar = _xz_solid(points["profile"], params.rafter_thickness)
    y_overlap = params.y_overlap
    cut_margin = params.cut_margin
    cut_y0 = -y_overlap
    cut_y1 = params.rafter_thickness / 2.0 + y_overlap
    for side in ("left", "right"):
        cutter_points = points[f"{side}_cut"]
        cutter = (
            cq.Workplane("XZ")
            .polyline(cutter_points)
            .close()
            .extrude((cut_y1 - cut_y0) / 2.0, both=True)
            .translate((0.0, (cut_y0 + cut_y1) / 2.0, 0.0))
        )
        collar = collar.cut(cutter)
    return collar.clean()


def _collar_points(values: Dict[str, float], params: RafterTrussParams) -> Dict[str, List[Point2]]:
    a = values["a"]
    half_crossing = values["half_crossing"]
    ridge_z = values["ridge_z"]
    collar_z0 = values["collar_center_z"] - params.collar_height / 2.0
    collar_z1 = values["collar_center_z"] + params.collar_height / 2.0
    seat_z = collar_z1 - params.seat_depth
    cut_margin = params.cut_margin

    def right_center_x_at_z(z: float) -> float:
        return (ridge_z - z) / math.tan(a)

    def right_inner_x_at_z(z: float) -> float:
        return right_center_x_at_z(z) - half_crossing

    def right_outer_x_at_z(z: float) -> float:
        return right_center_x_at_z(z) + half_crossing

    def left_center_x_at_z(z: float) -> float:
        return -(ridge_z - z) / math.tan(a)

    def left_inner_x_at_z(z: float) -> float:
        return left_center_x_at_z(z) + half_crossing

    def left_outer_x_at_z(z: float) -> float:
        return left_center_x_at_z(z) - half_crossing

    right_inner_top = (right_inner_x_at_z(collar_z1), collar_z1)
    right_inner_bottom = (right_inner_x_at_z(collar_z0), collar_z0)
    right_inner_seat = (right_inner_x_at_z(seat_z), seat_z)
    right_outer_top = (right_outer_x_at_z(collar_z1), collar_z1)
    right_outer_bottom = (right_outer_x_at_z(collar_z0), collar_z0)

    left_inner_top = (left_inner_x_at_z(collar_z1), collar_z1)
    left_inner_bottom = (left_inner_x_at_z(collar_z0), collar_z0)
    left_inner_seat = (left_inner_x_at_z(seat_z), seat_z)
    left_outer_top = (left_outer_x_at_z(collar_z1), collar_z1)
    left_outer_bottom = (left_outer_x_at_z(collar_z0), collar_z0)
    return {
        "profile": [
            left_outer_bottom,
            left_outer_top,
            left_inner_seat,
            left_inner_top,
            right_inner_top,
            right_inner_seat,
            right_outer_top,
            right_outer_bottom,
            left_outer_bottom,
        ],
        "left_cut": [
            left_inner_bottom,
            left_inner_top,
            (left_outer_top[0] - cut_margin, collar_z1 + cut_margin),
            (left_outer_bottom[0] - cut_margin, collar_z0 - cut_margin),
        ],
        "right_cut": [
            right_inner_bottom,
            right_inner_top,
            (right_outer_top[0] + cut_margin, collar_z1 + cut_margin),
            (right_outer_bottom[0] + cut_margin, collar_z0 - cut_margin),
        ],
    }


def _ridge_lap_coords(hand: int, values: Dict[str, float], params: RafterTrussParams) -> Tuple[float, float, float, float]:
    alpha = math.radians(values["ridge_degrees"])
    s = math.sin(alpha)
    c = math.cos(alpha)
    if s <= 0.0:
        raise ValueError(f"Invalid ridge angle: {values['ridge_degrees']}")
    z_bottom = values["z_bottom"]
    z_top = values["z_top"]

    def base_x(z: float) -> float:
        return -hand * z * c

    end_bottom_x = (base_x(z_bottom) - params.rafter_depth / 2.0) / s
    end_top_x = (base_x(z_top) - params.rafter_depth / 2.0) / s
    shoulder_bottom_x = (base_x(z_bottom) + params.rafter_depth / 2.0) / s
    shoulder_top_x = (base_x(z_top) + params.rafter_depth / 2.0) / s
    return end_bottom_x, end_top_x, shoulder_bottom_x, shoulder_top_x


def _xz_solid(points: List[Point2], thickness: float) -> cq.Workplane:
    return cq.Workplane("XZ").polyline(points).close().extrude(thickness / 2.0, both=True)


def _place_notebook_rafter(shape: cq.Workplane, angle_degrees: float, ridge_z: float) -> cq.Workplane:
    return shape.rotate((0, 0, 0), (0, 1, 0), angle_degrees).translate((0, 0, ridge_z)).clean()


def _map_notebook_section_to_truss(shape: cq.Workplane) -> cq.Workplane:
    return shape.rotate((0, 0, 0), (0, 0, 1), 90.0).clean()
