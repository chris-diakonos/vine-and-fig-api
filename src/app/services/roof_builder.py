"""
Roof builder service using CadQuery.
"""
import cadquery as cq
import math
from typing import List, Optional
from app.models.building import Roof
from app.models.floorplan import Dimensions


class RoofBuilder:
    """Builds roof geometry using CadQuery."""
    
    @staticmethod
    def build(
        roof: Roof,
        dimensions: Dimensions,
        stories: int,
        ceiling_heights: Optional[List[float]] = None
    ) -> cq.Workplane:
        """
        Build roof structure based on roof type and pitch.
        
        Args:
            roof: Roof specification
            dimensions: Building dimensions
            stories: Number of stories
            ceiling_heights: Ceiling heights for each story
            
        Returns:
            CadQuery Workplane with roof geometry
        """
        # Use default ceiling heights if not specified
        if ceiling_heights is None:
            ceiling_heights = [120] * stories  # 10 feet default
        
        # Calculate roof base elevation
        total_wall_height = sum(ceiling_heights)
        
        # Calculate roof height based on pitch (rise over 12 inches run)
        if roof.roof_type == "side-gable":
            # Pitch applies to the depth dimension
            run = dimensions.left / 2
            roof_height = (run / 12) * roof.roof_pitch
            
            # Create gable roof with panels
            roof_obj = RoofBuilder._build_gable_roof(
                roof,
                dimensions.front,
                dimensions.left,
                roof_height,
                total_wall_height,
                "side"
            )
        
        elif roof.roof_type == "front-gable":
            # Pitch applies to the front dimension
            run = dimensions.front / 2
            roof_height = (run / 12) * roof.roof_pitch
            
            roof_obj = RoofBuilder._build_gable_roof(
                roof,
                dimensions.front,
                dimensions.left,
                roof_height,
                total_wall_height,
                "front"
            )
        
        elif roof.roof_type == "hipped-gable":
            # More complex - simplified for now
            run = min(dimensions.front, dimensions.left) / 2
            roof_height = (run / 12) * roof.roof_pitch
            
            roof_obj = RoofBuilder._build_hipped_roof(
                dimensions.front,
                dimensions.left,
                roof_height,
                total_wall_height
            )
        
        else:
            # Default to simple gable
            run = dimensions.left / 2
            roof_height = (run / 12) * roof.roof_pitch
            roof_obj = RoofBuilder._build_gable_roof(
                roof,
                dimensions.front,
                dimensions.left,
                roof_height,
                total_wall_height,
                "side"
            )
        
        return roof_obj
    
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
        width: float,
        depth: float,
        height: float,
        base_elevation: float,
        gable_direction: str
    ) -> cq.Workplane:
        """
        Build a gable roof using individual metal roofing panels.
        
        Args:
            roof: Roof specification (for panel type and exposure)
            width: Building width
            depth: Building depth
            height: Roof height
            base_elevation: Base elevation for roof
            gable_direction: Direction of gable ("side" or "front")
        """
        # Calculate roof pitch angle in radians
        pitch_radians = math.radians(roof.roof_pitch)
        
        # Calculate actual roof surface length (accounting for pitch)
        # For a gable roof, the surface length is the hypotenuse
        if gable_direction == "side":
            # Ridge runs along front-back (X-axis), pitch applies to depth (Y-axis)
            run = depth / 2
            surface_length = math.sqrt(run**2 + height**2)
            panel_length = width  # Panels run along the ridge (X-axis)
            num_panels = math.ceil(run / roof.roof_panel_exposure) * 2  # Both sides
        else:
            # Ridge runs along left-right (Y-axis), pitch applies to width (X-axis)
            run = width / 2
            surface_length = math.sqrt(run**2 + height**2)
            panel_length = depth  # Panels run along the ridge (Y-axis)
            num_panels = math.ceil(run / roof.roof_panel_exposure) * 2  # Both sides
        
        all_panels = None
        
        # Create panels based on panel type
        if roof.roof_panel_type in ["ag-panel", "cf-panel", "pbr-panel"]:
            # Create panels for each side of the gable
            for side in range(2):
                side_offset = 1 if side == 0 else -1
                
                for panel_index in range(int(num_panels / 2)):
                    # Calculate panel position along the roof slope (horizontal distance from ridge)
                    panel_position = panel_index * roof.roof_panel_exposure
                    
                    # Calculate Z height based on roof pitch
                    # For pitch in degrees: rise = run * tan(pitch)
                    panel_z_height = (panel_position / 12) * roof.roof_pitch
                    
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
                    
                    # Position and rotate panel based on gable direction
                    if gable_direction == "side":
                        # Panels run along X-axis (parallel to ridge), positioned along Y-axis
                        # Ridge is at Y=0, panels extend outward
                        # ag_panel creates profile in XZ plane, extrudes along Y
                        # Need to rotate 90° around Z to make it extrude along X
                        panel = panel.rotate((0, 0, 0), (0, 0, 1), 90)
                        
                        panel_y = side_offset * (panel_position + roof.roof_panel_exposure / 2)
                        panel_z = base_elevation + panel_z_height
                        panel_x = 0  # Centered along X
                        
                        # Rotate panel around X-axis to match roof pitch
                        rotation_angle = math.degrees(pitch_radians) * side_offset
                        panel = panel.rotate((0, 0, 0), (1, 0, 0), rotation_angle)
                        panel = panel.translate((panel_x, panel_y, panel_z))
                    else:
                        # Panels run along Y-axis (parallel to ridge), positioned along X-axis
                        # Ridge is at X=0, panels extend outward
                        # ag_panel profile is in XZ plane, extrudes along Y (correct for front-gable)
                        panel_x = side_offset * (panel_position + roof.roof_panel_exposure / 2)
                        panel_z = base_elevation + panel_z_height
                        panel_y = 0  # Centered along Y
                        
                        # Rotate panel around Y-axis to match roof pitch
                        rotation_angle = -math.degrees(pitch_radians) * side_offset
                        panel = panel.rotate((0, 0, 0), (0, 1, 0), rotation_angle)
                        panel = panel.translate((panel_x, panel_y, panel_z))
                    
                    # Add panel to collection
                    if all_panels is None:
                        all_panels = panel
                    else:
                        all_panels = all_panels.union(panel)
        else:
            # Fallback for unknown panel types - use simple geometric roof
            # This should not normally be reached as all panel types are defined
            if gable_direction == "side":
                roof_plane = (
                    cq.Workplane("XY")
                    .sketch()
                    .polygon([
                        (-width/2, -depth/2),
                        (width/2, -depth/2),
                        (width/2, 0),
                        (-width/2, 0)
                    ])
                    .finalize()
                    .extrude(height)
                    .translate((0, depth/4, base_elevation + height/2))
                )
                
                other_side = (
                    cq.Workplane("XY")
                    .sketch()
                    .polygon([
                        (-width/2, 0),
                        (width/2, 0),
                        (width/2, depth/2),
                        (-width/2, depth/2)
                    ])
                    .finalize()
                    .extrude(height)
                    .translate((0, -depth/4, base_elevation + height/2))
                )
                
                all_panels = roof_plane.union(other_side)
            else:
                roof_plane = (
                    cq.Workplane("XY")
                    .sketch()
                    .polygon([
                        (-width/2, -depth/2),
                        (0, -depth/2),
                        (0, depth/2),
                        (-width/2, depth/2)
                    ])
                    .finalize()
                    .extrude(height)
                    .translate((-width/4, 0, base_elevation + height/2))
                )
                
                other_side = (
                    cq.Workplane("XY")
                    .sketch()
                    .polygon([
                        (0, -depth/2),
                        (width/2, -depth/2),
                        (width/2, depth/2),
                        (0, depth/2)
                    ])
                    .finalize()
                    .extrude(height)
                    .translate((width/4, 0, base_elevation + height/2))
                )
                
                all_panels = roof_plane.union(other_side)
        
        if all_panels is None:
            return cq.Workplane("XY")
        
        return all_panels
    
    @staticmethod
    def _build_hipped_roof(
        width: float,
        depth: float,
        height: float,
        base_elevation: float
    ) -> cq.Workplane:
        """Build a hipped roof (simplified pyramid)."""
        # Create a pyramid shape for simplified hipped roof
        roof = (
            cq.Workplane("XY")
            .rect(width, depth)
            .workplane(offset=height)
            .rect(width * 0.3, depth * 0.3)
            .loft()
            .translate((0, 0, base_elevation))
        )
        
        return roof
