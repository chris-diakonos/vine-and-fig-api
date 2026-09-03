"""
Roof builder service using CadQuery.
"""
import cadquery as cq
import math
from typing import List
from app.models.building import Roof
from app.models.floorplan import Dimensions


class RoofBuilder:
    """Builds roof geometry using CadQuery."""
    
    @staticmethod
    def build(
        roof: Roof,
        dimensions: Dimensions,
        stories: int,
        floor_heights: List[float]
    ) -> cq.Workplane:
        """
        Build roof structure based on roof type and pitch.
        
        Args:
            roof: Roof specification
            dimensions: Building dimensions
            stories: Number of stories
            floor_heights: Pre-calculated floor heights for each story
            
        Returns:
            CadQuery Workplane with roof geometry
        """
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
            panel_sin = math.sin(roof_pitch_radians)
            panel_length = math.ceil(panel_run / panel_cos) if panel_cos != 0 else math.ceil(panel_run)
            panel_y = ((panel_length/2) * panel_cos)
            panel_z = (panel_length/2) * panel_sin
            roof_length = front_dimension
            gable_direction = "side"
        elif roof.roof_type == "front-gable":
            panel_run = (front_dimension / 2) + roof_overhang
            panel_cos = math.cos(roof_pitch_radians)
            panel_sin = math.sin(roof_pitch_radians)
            panel_length = math.ceil(panel_run / panel_cos) if panel_cos != 0 else math.ceil(panel_run)
            panel_y = (panel_length/2) * panel_cos
            panel_z = (panel_length/2) * panel_sin
            roof_length = right_dimension
            gable_direction = "front"
        else:
            raise ValueError(f"Invalid roof type: {roof.roof_type}")

        # Build the roof panels
        roof_assembly = RoofBuilder._build_gable_roof(
            roof,
            panel_length,
            roof_length,
            panel_y,
            roof_pitch_degrees,
            panel_z,
            total_wall_height,
            gable_direction,
            roof.roof_panel_exposure,
            panel_run,
            right_dimension,
            front_dimension
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
        panel_y_offset: float,
        roof_pitch_degrees: float,
        panel_z_offset: float,
        base_elevation: float,
        gable_direction: str,
        roof_panel_exposure: float,
        panel_run: float,
        right_dimension: float = None,
        front_dimension: float = None
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
            roof_panel_exposure: Exposure of the roof panel in inches
            panel_run: Run of the roof panel in inches
        """
        
        assembly = cq.Assembly()
        

        if gable_direction == "side":
            faces = ["front", "rear"]
        elif gable_direction == "front":
            faces = ["left", "right"]
        else:
            raise ValueError(f"Invalid gable direction: {gable_direction}")

        for face in faces:
            
            # For side-gable roofs, account for gable overhang on both ends
            if gable_direction == "side":
                # Add gable overhang to both ends
                effective_roof_length = roof_length + (2 * roof.roof_overhang)
                gable_overhang_offset = -roof.roof_overhang
            else:
                effective_roof_length = roof_length
                gable_overhang_offset = 0

            quantity = math.ceil(effective_roof_length / roof_panel_exposure)

            for q in range(quantity):

                panel_counter = q + 1

                if face == "front":
                    panel_x = (roof.roof_panel_exposure * (panel_counter - 1)) + gable_overhang_offset
                    # Position panel so eave edge is at stud_depth + roof_overhang from building origin
                    stud_depth = 6
                    panel_y = stud_depth + roof.roof_overhang + panel_y_offset
                    panel_z = base_elevation + panel_z_offset
                    roof_pitch = 180 - roof_pitch_degrees
                elif face == "rear":
                    panel_x = (roof.roof_panel_exposure * (panel_counter - 1)) + gable_overhang_offset
                    # Position panel so eave edge is at -dimension - stud_depth - roof_overhang
                    stud_depth = 6
                    # For side-gable, rear wall is at -right_dimension; for front-gable, at -front_dimension
                    dimension = right_dimension if gable_direction == "side" else front_dimension
                    panel_y = -dimension - stud_depth - roof.roof_overhang - panel_y_offset
                    panel_z = base_elevation + panel_z_offset
                    roof_pitch = roof_pitch_degrees
                elif face == "left":
                    panel_x = (roof.roof_panel_exposure * (panel_counter - 1)) + gable_overhang_offset
                    panel_y = panel_y_offset
                    panel_z = base_elevation + panel_z_offset
                    roof_pitch = 90
                elif face == "right":
                    panel_x = (roof.roof_panel_exposure * (panel_counter - 1)) + gable_overhang_offset
                    panel_y = -panel_y_offset
                    panel_z = base_elevation + panel_z_offset
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

                # Rotate the panel first
                panel = panel.rotateAboutCenter((1, 0, 0), roof_pitch)
                
                # Get the bounding box after rotation to find actual center Y position
                # panel_y represents where the center should be after accounting for pitch
                # After rotateAboutCenter, the center stays fixed, so we need to find where it is
                bbox = panel.val().BoundingBox()
                current_center_y = (bbox.ymin + bbox.ymax) / 2
                
                # Calculate offset needed to move center from current position to panel_y
                y_offset = panel_y - current_center_y
                
                # Translate to final position
                panel = panel.translate((panel_x, y_offset, panel_z))
                
                assembly.add(panel, name=f"roof_panel_{panel_counter}_{face}", color=cq.Color(0.3, 0.3, 0.3))  # Dark roof

        return assembly
