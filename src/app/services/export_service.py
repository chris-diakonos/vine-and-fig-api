"""
Export service for converting CadQuery models to various formats.
"""
import cadquery as cq
from pathlib import Path
from typing import Literal, Optional
import logging

# Import CadQuery exporters - note: some exporters may not be available depending on CadQuery version
try:
    from cadquery import exporters
except ImportError:
    exporters = None

from app.utils.file_manager import FileManager

logger = logging.getLogger(__name__)


class ExportService:
    """Handles exporting CadQuery models to different file formats."""
    
    @staticmethod
    def export_gltf(model: cq.Workplane, output_path: Path, upload_to_storage: bool = True) -> str:
        """
        Export model to glTF format for 3D visualization.
        
        Args:
            model: CadQuery Workplane object
            output_path: Path where the file should be saved (local temp)
            upload_to_storage: Whether to upload to configured storage (Azure/local)
            
        Returns:
            URL to the exported file
            
        Raises:
            RuntimeError: If export fails
        """
        try:
            # Export to glTF locally first
            exporters.export(model, str(output_path), exportType=exporters.ExportTypes.GLTF)
            logger.info(f"Exported glTF to local path: {output_path}")
            
            if upload_to_storage:
                # Determine blob name
                blob_name = f"models/{output_path.name}"
                # Upload to storage and get URL
                url = FileManager.save_file(output_path, blob_name, content_type="model/gltf+json")
                return url
            
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to export to glTF: {str(e)}")
            raise RuntimeError(f"Failed to export to glTF: {str(e)}")
    
    @staticmethod
    def export_step(model: cq.Workplane, output_path: Path) -> Path:
        """
        Export model to STEP format (CAD interchange format).
        
        Args:
            model: CadQuery Workplane object
            output_path: Path where the file should be saved
            
        Returns:
            Path to the exported file
        """
        try:
            exporters.export(model, str(output_path), exportType=exporters.ExportTypes.STEP)
            return output_path
        except Exception as e:
            raise RuntimeError(f"Failed to export to STEP: {str(e)}")
    
    @staticmethod
    def export_svg(
        model: cq.Workplane,
        output_path: Path,
        projection_dir: tuple = (0, 0, 1),
        upload_to_storage: bool = True
    ) -> str:
        """
        Export model to SVG format for 2D drawings.
        
        Args:
            model: CadQuery Workplane object
            output_path: Path where the file should be saved (local temp)
            projection_dir: Camera direction for projection (x, y, z)
            upload_to_storage: Whether to upload to configured storage (Azure/local)
            
        Returns:
            URL to the exported file
        """
        try:
            # Configure SVG export options
            svg_opts = {
                "width": 800,
                "height": 600,
                "marginLeft": 50,
                "marginTop": 50,
                "showAxes": False,
                "projectionDir": projection_dir,
                "strokeWidth": 0.5,
                "strokeColor": (0, 0, 0),
                "hiddenColor": (160, 160, 160),
                "showHidden": True,
            }
            
            exporters.export(model, str(output_path), opt=svg_opts)
            logger.info(f"Exported SVG to local path: {output_path}")
            
            if upload_to_storage:
                # Determine blob name
                blob_name = f"drawings/{output_path.name}"
                # Upload to storage and get URL
                url = FileManager.save_file(output_path, blob_name, content_type="image/svg+xml")
                return url
            
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to export to SVG: {str(e)}")
            raise RuntimeError(f"Failed to export to SVG: {str(e)}")
    
    @staticmethod
    def export_stl(model: cq.Workplane, output_path: Path) -> Path:
        """
        Export model to STL format for 3D printing.
        
        Args:
            model: CadQuery Workplane object
            output_path: Path where the file should be saved
            
        Returns:
            Path to the exported file
        """
        try:
            exporters.export(model, str(output_path), exportType=exporters.ExportTypes.STL)
            return output_path
        except Exception as e:
            raise RuntimeError(f"Failed to export to STL: {str(e)}")
    
    @staticmethod
    def export_dxf(model: cq.Workplane, output_path: Path) -> Path:
        """
        Export model to DXF format for 2D CAD.
        
        Args:
            model: CadQuery Workplane object
            output_path: Path where the file should be saved
            
        Returns:
            Path to the exported file
        """
        try:
            exporters.export(model, str(output_path), exportType=exporters.ExportTypes.DXF)
            return output_path
        except Exception as e:
            raise RuntimeError(f"Failed to export to DXF: {str(e)}")
    
    @staticmethod
    def export_by_type(
        model: cq.Workplane,
        output_path: Path,
        export_type: Literal["gltf", "step", "svg", "stl", "dxf"],
        **kwargs
    ) -> Path:
        """
        Export model to specified format.
        
        Args:
            model: CadQuery Workplane object
            output_path: Path where the file should be saved
            export_type: Type of export
            **kwargs: Additional arguments for specific export types
            
        Returns:
            Path to the exported file
        """
        export_methods = {
            "gltf": ExportService.export_gltf,
            "step": ExportService.export_step,
            "svg": ExportService.export_svg,
            "stl": ExportService.export_stl,
            "dxf": ExportService.export_dxf,
        }
        
        if export_type not in export_methods:
            raise ValueError(f"Unsupported export type: {export_type}")
        
        export_method = export_methods[export_type]
        
        # Handle SVG with projection
        if export_type == "svg" and "projection_dir" in kwargs:
            return export_method(model, output_path, kwargs["projection_dir"])
        else:
            return export_method(model, output_path)
