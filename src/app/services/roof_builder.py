"""
Roof builder service using CadQuery.
"""
import cadquery as cq
import math
from typing import List, Optional
from app.models.building import Roof
from app.models.floorplan import Dimensions
from app.services.framing_builder import FramingBuilder


class RoofBuilder:
    """Builds roof geometry using CadQuery."""
    
    @staticmethod
    def build(
        roof: Roof,
        dimensions: Dimensions,
        stories: int,
        ceiling_heights: Optional[List[float]] = None,
        joist_heights: Optional[List[float]] = None
    ) -> cq.Workplane:
        """
        Build roof structure based on roof type and pitch.
        
        Args:
            roof: Roof specification
            dimensions: Building dimensions
            stories: Number of stories
            ceiling_heights: Ceiling heights for each story
            joist_heights: Joist heights for each floor
            
        Returns:
            CadQuery Workplane with roof geometry
        """
        if ceiling_heights is None:
            ceiling_heights = [120, 108]
        if joist_heights is None:
            joist_heights = [10, 9, 8]
        
        floor_heights = FramingBuilder.calculate_floor_heights(
            stories,
            joist_heights,
            ceiling_heights
        )
        total_wall_height = floor_heights[stories]
        roof_overhang = roof.roof_overhang
        roof_pitch_degrees = roof.roof_pitch
        right_dimension = dimensions.right
        front_dimension = dimensions.front
        
        # Calculate roof height based on pitch (rise over 12 inches run)
        roof_pitch_radians = roof_pitch_degrees * (math.pi / 180)
        
        if roof.roof_type == "side-gable":
            # Pitch applies to the depth dimension
            panel_run = (right_dimension / 2) + roof_overhang
            panel_cos = math.cos(roof_pitch_radians)
            panel_length = math.ceil(panel_run / panel_cos) if panel_cos != 0 else math.ceil(panel_run)
            roof_length = front_dimension
            gable_direction = "side"
        elif roof.roof_type == "front-gable":
            panel_run = (front_dimension / 2) + roof_overhang
            panel_cos = math.cos(roof_pitch_radians)
            panel_length = math.ceil(panel_run / panel_cos) if panel_cos != 0 else math.ceil(panel_run)
            roof_length = right_dimension
            gable_direction = "front"
        else:
            raise ValueError(f"Invalid roof type: {roof.roof_type}")

        # Build the roof panels
        roof_assembly = RoofBuilder._build_gable_roof(
            roof,
            panel_length,
            roof_length,
            roof_pitch_radians,
            total_wall_height,
            gable_direction
        )
        
        return roof_assembly

    
    @staticmethod
    def _ag_panel(length: float) -> cq.Workplane:
        """
        Generate a 3D drawing of an AG metal roofing panel of the desired length.
        
        Args:
            length: Length of the panel in inches
            
        Returns:
            CadQuery Workplane with the panel geometry
        """
        profile_points = []
        thickness = 0.0149
        large_rib_height = 0.75
        large_rib_top = 0.375
        large_rib_bottom = 0.50
        medium_rib_height = 0.625
        medium_rib_top = 0.75
        medium_rib_bottom = 1.75
        medium_rib_delta = (medium_rib_bottom - medium_rib_top)/2
        large_rib_delta = (medium_rib_top - large_rib_bottom)/2
        medium_rib_center = medium_rib_bottom/2
        large_rib_center = large_rib_top/2
        large_rib_top_delta = (large_rib_bottom - large_rib_top)/2

        small_rib_height = 0.125
        small_rib_top = 0.75
        small_rib_bottom = 1.25
        small_rib_delta = (small_rib_bottom - small_rib_top)/2
        
        large_rib_spacing = 9.00
        small_rib_middle_space = 1.5
        small_rib_outside_space = 1.625

        # Profile starting rib
        current_x = 0
        profile_points.append((current_x, 0))
        current_x += large_rib_delta
        profile_points.append((current_x, 0))
        current_x += medium_rib_delta
        profile_points.append((current_x, medium_rib_height))
        current_x += large_rib_delta
        profile_points.append((current_x, medium_rib_height))
        current_x += large_rib_top_delta
        profile_points.append((current_x, large_rib_height))

        # Repeatable profile
        for i in range(4):
            current_x += large_rib_top
            profile_points.append((current_x, large_rib_height))
            current_x += large_rib_top_delta
            profile_points.append((current_x, medium_rib_height))
            current_x += large_rib_delta
            profile_points.append((current_x, medium_rib_height))
            current_x += medium_rib_delta
            profile_points.append((current_x, 0))
            current_x += small_rib_outside_space
            profile_points.append((current_x, 0))
            current_x += small_rib_delta
            profile_points.append((current_x, small_rib_height))
            current_x += small_rib_top
            profile_points.append((current_x, small_rib_height))
            current_x += small_rib_delta
            profile_points.append((current_x, 0))
            current_x += small_rib_middle_space
            profile_points.append((current_x, 0))
            current_x += small_rib_delta
            profile_points.append((current_x, small_rib_height))
            current_x += small_rib_top
            profile_points.append((current_x, small_rib_height))
            current_x += small_rib_delta
            profile_points.append((current_x, 0))
            current_x += small_rib_outside_space
            profile_points.append((current_x, 0))
            current_x += medium_rib_delta
            profile_points.append((current_x, medium_rib_height))
            current_x += large_rib_delta
            profile_points.append((current_x, medium_rib_height))
            current_x += large_rib_top_delta
            profile_points.append((current_x, large_rib_height))

        # Profile ending rib
        current_x += large_rib_top
        profile_points.append((current_x, large_rib_height))
        current_x += large_rib_top_delta
        profile_points.append((current_x, medium_rib_height))
        current_x += large_rib_delta
        profile_points.append((current_x, medium_rib_height))
        current_x += medium_rib_delta * (3/4)
        profile_points.append((current_x, medium_rib_height / 4))
        
        profile_points.append((current_x, (medium_rib_height / 4) + thickness))
        current_x -= medium_rib_delta * (3/4)
        profile_points.append((current_x, medium_rib_height + thickness))
        current_x -= large_rib_delta
        profile_points.append((current_x, medium_rib_height + thickness))
        current_x -= large_rib_top_delta
        profile_points.append((current_x, large_rib_height + thickness))
        current_x -= large_rib_top
        profile_points.append((current_x, large_rib_height + thickness))

        # Repeatable profile (reverse)
        for j in range(4):
            current_x -= large_rib_top_delta
            profile_points.append((current_x, medium_rib_height + thickness))
            current_x -= large_rib_delta
            profile_points.append((current_x, medium_rib_height + thickness))
            current_x -= medium_rib_delta
            profile_points.append((current_x, thickness))
            current_x -= small_rib_outside_space
            profile_points.append((current_x, thickness))
            current_x -= small_rib_delta
            profile_points.append((current_x, small_rib_height + thickness))
            current_x -= small_rib_top
            profile_points.append((current_x, small_rib_height + thickness))
            current_x -= small_rib_delta
            profile_points.append((current_x, thickness))
            current_x -= small_rib_middle_space
            profile_points.append((current_x, thickness))
            current_x -= small_rib_delta
            profile_points.append((current_x, small_rib_height + thickness))
            current_x -= small_rib_top
            profile_points.append((current_x, small_rib_height + thickness))
            current_x -= small_rib_delta
            profile_points.append((current_x, thickness))
            current_x -= small_rib_outside_space
            profile_points.append((current_x, thickness))
            current_x -= medium_rib_delta
            profile_points.append((current_x, medium_rib_height + thickness))
            current_x -= large_rib_delta
            profile_points.append((current_x, medium_rib_height + thickness))
            current_x -= large_rib_top_delta
            profile_points.append((current_x, large_rib_height + thickness))
            current_x -= large_rib_top
            profile_points.append((current_x, large_rib_height + thickness))

        # Profile starting rib (reverse)
        current_x -= large_rib_top_delta
        profile_points.append((current_x, medium_rib_height + thickness))
        current_x -= large_rib_delta
        profile_points.append((current_x, medium_rib_height + thickness))
        current_x -= medium_rib_delta
        profile_points.append((current_x, thickness))
        current_x -= large_rib_delta
        profile_points.append((current_x, thickness))
        
        # Create the 2D profile and extrude along length
        profile = cq.Workplane("XZ").polyline(profile_points).close().extrude(length)

        return profile
    
    @staticmethod
    def _cf_panel(length: float) -> cq.Workplane:
        """
        Generate a 3D drawing of a CF metal roofing panel of the desired length.
        
        TODO: Replace with actual CF panel profile implementation.
        For now, uses AG panel as placeholder.
        
        Args:
            length: Length of the panel in inches
            
        Returns:
            CadQuery Workplane with the panel geometry
        """
        # Placeholder: use AG panel until CF panel implementation is ready
        return RoofBuilder._ag_panel(length)
    
    @staticmethod
    def _pbr_panel(length: float) -> cq.Workplane:
        """
        Generate a 3D drawing of a PBR metal roofing panel of the desired length.
        
        TODO: Replace with actual PBR panel profile implementation.
        For now, uses AG panel as placeholder.
        
        Args:
            length: Length of the panel in inches
            
        Returns:
            CadQuery Workplane with the panel geometry
        """
        # Placeholder: use AG panel until PBR panel implementation is ready
        return RoofBuilder._ag_panel(length)
    
    @staticmethod
    def _build_gable_roof(
        roof: Roof,
        panel_length: float,
        roof_length: float,
        roof_pitch_radians: float,
        base_elevation: float,
        gable_direction: str
    ) -> cq.Workplane:
        """
        Build a gable roof using individual metal roofing panels.
        
        Args:
            roof: Roof specification (for panel type and exposure)
            panel_length: Length of the panel in inches
            roof_length: Length of the roof in inches
            roof_pitch_radians: Roof pitch in radians
            base_elevation: Base elevation for roof
            gable_direction: Direction of gable ("side" or "front")
        """
        
        all_panels = None
        quantity = math.ceil(roof_length / roof.roof_panel_exposure)

        for q in range(quantity):

            if gable_direction == "side":
                panel_x = q * roof.roof_panel_exposure
                panel_y = 0
                faces = ["front", "rear"]
            elif gable_direction == "front":
                panel_x = 0
                panel_y = q * roof.roof_panel_exposure
                faces = ["left", "right"]
            else:
                panel_x = 0
                panel_y = q * roof.roof_panel_exposure
                faces = ["left", "right"]

            # Calculate panel position based on roof pitch
            panel_z = base_elevation + (q * panel_length * math.tan(roof_pitch_radians))

            for face in faces:

                # Create panel based on panel type
                if roof.roof_panel_type == "ag-panel":
                    panel = RoofBuilder._ag_panel(panel_length)
                elif roof.roof_panel_type == "cf-panel":
                    panel = RoofBuilder._cf_panel(panel_length)
                elif roof.roof_panel_type == "pbr-panel":
                    panel = RoofBuilder._pbr_panel(panel_length)
                else:
                    # Fallback to AG panel
                    panel = RoofBuilder._ag_panel(panel_length)

                if face == "front":
                    panel = panel.rotate((0, 0, 0), (0, 0, 1), 90).translate((panel_x, panel_y, panel_z))
                elif face == "rear":
                    panel = panel.rotate((0, 0, 0), (0, 0, 1), -90).translate((panel_x, panel_y, panel_z))
                elif face == "left":
                    panel = panel.rotate((0, 0, 0), (0, 0, 1), 180).translate((panel_x, panel_y, panel_z))
                elif face == "right":
                    panel = panel.rotate((0, 0, 0), (0, 0, 1), -180).translate((panel_x, panel_y, panel_z))

                if all_panels is None:
                    all_panels = panel
                else:
                    all_panels = all_panels.union(panel)

        # Return the combined panels (or an empty workplane if no panels)
        if all_panels is None:
            return cq.Workplane("XY")
        return all_panels
