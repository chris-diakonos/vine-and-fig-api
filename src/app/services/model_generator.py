"""
Main model generation service that orchestrates the entire process.
"""
from pathlib import Path
from typing import Tuple, Literal

from app.models.structure import Structure
from app.models.responses import ModelResponse
from app.services.building_builder import BuildingBuilder
from app.services.export_service import ExportService
from app.utils.file_manager import FileManager
from app.utils.view_projections import get_projection_settings


class ModelGenerator:
    """Main service for generating building models and drawings."""
    
    @staticmethod
    def generate(
        structure: Structure,
        view_mode: Literal["3d", "plan", "section", "elevation"],
        structure_hash: str = None
    ) -> ModelResponse:
        """
        Generate a building model or drawing based on the structure specification.
        
        Args:
            structure: Complete building structure specification
            view_mode: View mode for output (3d, plan, section, elevation)
            structure_hash: Optional structure hash for filename generation
            
        Returns:
            ModelResponse with URLs to the generated files
            
        Raises:
            RuntimeError: If generation or export fails
        """
        # Check if we should use existing hashed files
        if structure_hash:
            if view_mode == "3d":
                if FileManager.hashed_model_exists(structure_hash) and not FileManager.should_regenerate_hashed_file(structure_hash):
                    # Return existing model
                    model_url = FileManager.get_model_url("", "gltf", structure_hash)
                    return ModelResponse(
                        model_url=model_url,
                        gltf_url=model_url,
                        image_url=None,
                        view_mode="3d",
                        model_id=structure_hash
                    )
            else:
                if FileManager.hashed_drawing_exists(structure_hash, view_mode) and not FileManager.should_regenerate_hashed_file(structure_hash):
                    # Return existing drawing
                    drawing_url = FileManager.get_drawing_url("", view_mode, "svg", structure_hash)
                    return ModelResponse(
                        model_url=drawing_url,
                        gltf_url=None,
                        image_url=drawing_url,
                        view_mode=view_mode,
                        model_id=structure_hash
                    )
        
        # Generate unique model ID
        model_id = FileManager.generate_model_id()
        
        # Build the 3D model using CadQuery
        try:
            building_model = BuildingBuilder.build(structure)
        except Exception as e:
            raise RuntimeError(f"Failed to build model: {str(e)}")
        
        # Export based on view mode
        if view_mode == "3d":
            return ModelGenerator._generate_3d(building_model, model_id, structure_hash)
        else:
            return ModelGenerator._generate_2d(building_model, model_id, view_mode, structure_hash)
    
    @staticmethod
    def _generate_3d(building_model, model_id: str, structure_hash: str = None) -> ModelResponse:
        """
        Generate 3D model output in glTF format.
        
        Args:
            building_model: CadQuery Workplane with building geometry
            model_id: Unique identifier for this model
            
        Returns:
            ModelResponse with 3D model URLs
        """
        # Get output path
        output_path = FileManager.get_model_path(model_id, "gltf", structure_hash)
        
        # Export to glTF and upload to storage
        try:
            model_url = ExportService.export_gltf(building_model, output_path, upload_to_storage=True)
        except Exception as e:
            raise RuntimeError(f"Failed to export 3D model: {str(e)}")
        
        return ModelResponse(
            model_url=model_url,
            gltf_url=model_url,
            image_url=None,
            view_mode="3d",
            model_id=structure_hash if structure_hash else model_id
        )
    
    @staticmethod
    def _generate_2d(
        building_model,
        model_id: str,
        view_mode: Literal["plan", "section", "elevation"],
        structure_hash: str = None
    ) -> ModelResponse:
        """
        Generate 2D drawing output in SVG format.
        
        Args:
            building_model: CadQuery Workplane with building geometry
            model_id: Unique identifier for this model
            view_mode: View mode (plan, section, elevation)
            
        Returns:
            ModelResponse with 2D drawing URLs
        """
        # Get projection settings
        projection = get_projection_settings(view_mode)
        
        # Get output path
        output_path = FileManager.get_drawing_path(model_id, view_mode, "svg", structure_hash)
        
        try:
            if view_mode == "plan" and structure:
                # Use dedicated plan view generator for architectural-style floor plans
                floorplan = structure.floorplan
                
                # Convert windows and doors to dict format for plan generator
                windows_dict = [w.dict() for w in structure.windows] if structure.windows else None
                doors_dict = [d.dict() for d in structure.doors] if structure.doors else None
                
                PlanViewGenerator.generate_plan_svg(
                    floorplan_type=floorplan.floorplan_type,
                    dimensions={
                        'front': floorplan.dimensions.front,
                        'rear': floorplan.dimensions.rear,
                        'left': floorplan.dimensions.left,
                        'right': floorplan.dimensions.right,
                    },
                    hall_width=floorplan.hall_width,
                    hall_offset=floorplan.hall_offset or 0,
                    stories=floorplan.stories,
                    bays=floorplan.bays.dict() if floorplan.bays else None,
                    windows=windows_dict,
                    doors=doors_dict,
                    output_path=output_path
                )
            elif view_mode == "section" and structure:
                # Use dedicated section view generator for architectural-style sections
                floorplan = structure.floorplan
                foundation = structure.foundation
                roof = structure.roof
                
                # Debug: Check if windows exist
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Section view: structure.windows = {structure.windows}")
                logger.info(f"Number of windows: {len(structure.windows) if structure.windows else 0}")
                
                # Convert windows to dict format for section generator
                windows_dict = [w.dict() for w in structure.windows] if structure.windows else None
                logger.info(f"Converted windows_dict: {windows_dict}")
                
                # Calculate building height from structure
                building_height = floorplan.building_height if hasattr(floorplan, 'building_height') else 240
                
                # Extract foundation block height from block_size if available
                foundation_block_height = 8  # Default
                if foundation and foundation.foundation_block_size:
                    foundation_block_height = foundation.foundation_block_size[2]  # height is 3rd element
                
                SectionViewGenerator.generate_section_svg(
                    dimensions={
                        'front': floorplan.dimensions.front,
                        'left': floorplan.dimensions.left,
                        'building_height': building_height,
                    },
                    stories=floorplan.stories,
                    ceiling_heights=floorplan.ceiling_heights,
                    joist_heights=floorplan.joist_heights,
                    foundation_courses=foundation.foundation_courses if foundation else 8,
                    foundation_block_height=foundation_block_height,
                    foundation_block_joint=foundation.foundation_block_joint if foundation else 0.5,
                    roof_pitch=roof.roof_pitch if roof else 12,
                    roof_type=roof.roof_type if roof else 'side-gable',
                    roof_shed_length=roof.roof_shed_length if roof else 0,
                    floorplan_type=floorplan.floorplan_type,
                    hall_width=floorplan.hall_width,
                    hall_offset=floorplan.hall_offset or 0,
                    windows=windows_dict,
                    output_path=output_path
                )
            elif view_mode.startswith("elevation") and structure:
                # Use dedicated elevation view generator for architectural-style elevations
                # Parse face from view_mode: "elevation" or "elevation-front", "elevation-rear", etc.
                if '-' in view_mode:
                    face = view_mode.split('-')[1]  # e.g., "elevation-front" -> "front"
                else:
                    face = 'front'  # Default to front elevation
                
                floorplan = structure.floorplan
                foundation = structure.foundation
                roof = structure.roof
                sheathing = structure.sheathing
                
                # Convert windows and doors to dict format
                windows_dict = [w.dict() for w in structure.windows] if structure.windows else None
                doors_dict = [d.dict() for d in structure.doors] if structure.doors else None
                
                # Calculate foundation details
                foundation_block_size = [40, 14, 14]  # Default
                if foundation and foundation.foundation_block_size:
                    foundation_block_size = foundation.foundation_block_size
                foundation_block_height = foundation_block_size[2]
                foundation_courses = foundation.foundation_courses if foundation else 8
                foundation_block_joint = foundation.foundation_block_joint if foundation else 0.5
                foundation_height = foundation_courses * (foundation_block_height + foundation_block_joint)
                
                # Calculate building height
                building_height = floorplan.building_height if hasattr(floorplan, 'building_height') else 240
                
                ElevationViewGenerator.generate_elevation_svg(
                    face=face,
                    dimensions={
                        'front': floorplan.dimensions.front,
                        'left': floorplan.dimensions.left,
                        'building_height': building_height,
                    },
                    stories=floorplan.stories,
                    ceiling_heights=floorplan.ceiling_heights,
                    joist_heights=floorplan.joist_heights,
                    foundation_height=foundation_height,
                    foundation_courses=foundation_courses,
                    foundation_block_size=foundation_block_size,
                    foundation_block_joint=foundation_block_joint,
                    roof_pitch=roof.roof_pitch if roof else 37,
                    roof_type=roof.roof_type if roof else 'side-gable',
                    roof_panel_exposure=roof.roof_panel_exposure if roof else 12,
                    roof_panel_color=roof.roof_panel_color if roof else 'charcoal-gray',
                    roof_overhang=roof.roof_overhang if roof else 12,
                    roof_shed_length=roof.roof_shed_length if roof else 0,
                    floorplan_type=floorplan.floorplan_type,
                    bays=floorplan.bays.dict() if floorplan.bays else None,
                    windows=windows_dict,
                    doors=doors_dict,
                    sheathing=sheathing.dict() if sheathing else None,
                    output_path=output_path
                )
            else:
                # Fallback: Use 3D projection for other views
                projection = get_projection_settings(view_mode)
                ExportService.export_svg(
                building_model,
                output_path,
                projection_dir=projection.direction,
                upload_to_storage=True
            )
        except Exception as e:
            raise RuntimeError(f"Failed to export 2D drawing: {str(e)}")
        
        # Generate the drawing URL
        drawing_url = FileManager.get_drawing_url(model_id, view_mode, "svg", structure_hash)
        
        return ModelResponse(
            model_url=drawing_url,
            gltf_url=None,
            image_url=drawing_url,
            view_mode=view_mode,
            model_id=structure_hash if structure_hash else model_id
        )
