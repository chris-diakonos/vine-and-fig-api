"""
Main model generation service that orchestrates the entire process.
"""
from pathlib import Path
from typing import Tuple, Literal
import logging

from app.models.structure import Structure
from app.models.responses import ModelResponse
from app.services.building_builder import BuildingBuilder
from app.services.export_service import ExportService
from app.utils.file_manager import FileManager
from app.utils.view_projections import get_projection_settings

logger = logging.getLogger(__name__)


class ModelGenerator:
    """Main service for generating building models and drawings."""
    
    @staticmethod
    def generate(
        structure: Structure,
        view_mode: Literal[
            "3d", 
            "plan", 
            "section", 
            "elevation",
            "elevation-front",
            "elevation-rear",
            "elevation-left",
            "elevation-right"
        ],
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
            building_model, bom_data = BuildingBuilder.build(structure, structure_hash)
        except Exception as e:
            raise RuntimeError(f"Failed to build model: {str(e)}")
        
        # Save BOM data if available and structure_hash is provided
        if bom_data and structure_hash:
            try:
                from app.utils.bom_data_manager import BOMDataManager
                BOMDataManager.save_bom_data(structure_hash, bom_data)
                logger.info(f"Saved BOM data for structure_hash: {structure_hash}")
            except Exception as e:
                logger.warning(f"Failed to save BOM data: {str(e)}")
                # Don't fail model generation if BOM save fails
        
        # Export based on view mode
        if view_mode == "3d":
            return ModelGenerator._generate_3d(building_model, model_id, structure_hash)
        else:
            return ModelGenerator._generate_2d(building_model, model_id, view_mode, structure_hash, structure)
    
    @staticmethod
    def _generate_3d(building_model, model_id: str, structure_hash: str = None) -> ModelResponse:
        """
        Generate 3D model output in glTF format.
        
        Args:
            building_model: CadQuery Assembly or Workplane with building geometry
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
        view_mode: Literal[
            "plan", 
            "section", 
            "elevation",
            "elevation-front",
            "elevation-rear",
            "elevation-left",
            "elevation-right"
        ],
        structure_hash: str = None,
        structure: Structure = None
    ) -> ModelResponse:
        """
        Generate 2D drawing output in SVG format using 3D model projections.
        
        Args:
            building_model: CadQuery Assembly or Workplane with building geometry
            model_id: Unique identifier for this model
            view_mode: View mode (plan, section, elevation, etc.)
            structure_hash: Optional structure hash
            structure: Structure specification (not used for projections, kept for compatibility)
            
        Returns:
            ModelResponse with 2D drawing URLs
        """
        # Get projection settings for the view mode
        projection = get_projection_settings(view_mode)
        
        # Get output path
        output_path = FileManager.get_drawing_path(model_id, view_mode, "svg", structure_hash)
        
        try:
            # Use 3D projection for all 2D views
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
