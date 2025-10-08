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
        view_mode: Literal["3d", "plan", "section", "elevation"]
    ) -> ModelResponse:
        """
        Generate a building model or drawing based on the structure specification.
        
        Args:
            structure: Complete building structure specification
            view_mode: View mode for output (3d, plan, section, elevation)
            
        Returns:
            ModelResponse with URLs to the generated files
            
        Raises:
            RuntimeError: If generation or export fails
        """
        # Generate unique model ID
        model_id = FileManager.generate_model_id()
        
        # Build the 3D model using CadQuery
        try:
            building_model = BuildingBuilder.build(structure)
        except Exception as e:
            raise RuntimeError(f"Failed to build model: {str(e)}")
        
        # Export based on view mode
        if view_mode == "3d":
            return ModelGenerator._generate_3d(building_model, model_id)
        else:
            return ModelGenerator._generate_2d(building_model, model_id, view_mode)
    
    @staticmethod
    def _generate_3d(building_model, model_id: str) -> ModelResponse:
        """
        Generate 3D model output in glTF format.
        
        Args:
            building_model: CadQuery Workplane with building geometry
            model_id: Unique identifier for this model
            
        Returns:
            ModelResponse with 3D model URLs
        """
        # Get output path
        output_path = FileManager.get_model_path(model_id, "gltf")
        
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
            model_id=model_id
        )
    
    @staticmethod
    def _generate_2d(
        building_model,
        model_id: str,
        view_mode: Literal["plan", "section", "elevation"]
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
        output_path = FileManager.get_drawing_path(model_id, view_mode, "svg")
        
        # Export to SVG with projection and upload to storage
        try:
            drawing_url = ExportService.export_svg(
                building_model,
                output_path,
                projection_dir=projection.direction,
                upload_to_storage=True
            )
        except Exception as e:
            raise RuntimeError(f"Failed to export 2D drawing: {str(e)}")
        
        return ModelResponse(
            model_url=drawing_url,
            gltf_url=None,
            image_url=drawing_url,
            view_mode=view_mode,
            model_id=model_id
        )
