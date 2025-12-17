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
            panel_run,
            roof_pitch_degrees,
            total_wall_height,
            gable_direction,
            roof.roof_panel_exposure
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
        roof_run: float,
        roof_pitch_degrees: float,
        base_elevation: float,
        gable_direction: str,
        roof_panel_exposure: float
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
        
        assembly = cq.Assembly()
        

        if gable_direction == "side":
            faces = ["front", "rear"]
        elif gable_direction == "front":
            faces = ["left", "right"]
        else:
            raise ValueError(f"Invalid gable direction: {gable_direction}")

        for face in faces:

            quantity = math.ceil(roof_length / roof_panel_exposure)

            for q in range(quantity):

                panel_counter = q + 1

                if face == "front":
                    panel_x = (roof.roof_panel_exposure * (panel_counter - 1))
                    panel_y = +(panel_length/2.7)
                    panel_z = base_elevation + (panel_length/2.7)
                    roof_pitch = 180 - roof_pitch_degrees
                elif face == "rear":
                    panel_x = (roof.roof_panel_exposure * (panel_counter - 1))
                    panel_y = -(panel_length/2.7)
                    panel_z = base_elevation + (panel_length/2.7)
                    roof_pitch = roof_pitch_degrees
                elif face == "left":
                    panel_x = (roof.roof_panel_exposure * (panel_counter - 1))
                    panel_y = +(roof_run/2) - (panel_length/2.7)
                    panel_z = base_elevation + (panel_length/2.7)
                    roof_pitch = 90
                elif face == "right":
                    panel_x = (roof.roof_panel_exposure * (panel_counter - 1))
                    panel_y = +(roof_run/2) + (panel_length/2.7)
                    panel_z = base_elevation + (panel_length/2.7)
                    roof_pitch = -90
                else:
                    raise ValueError(f"Invalid face: {face}")

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

                panel = panel.translate((panel_x, panel_y, panel_z)).rotateAboutCenter((1, 0, 0),roof_pitch)
                
                assembly.add(panel, name=f"roof_panel_{panel_counter}_{face}", color=cq.Color(0.3, 0.3, 0.3))  # Dark roof

        return assembly
