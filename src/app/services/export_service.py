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
    def export_gltf(model, output_path: Path, upload_to_storage: bool = True) -> str:
        """
        Export model to glTF format for 3D visualization.
        Note: CadQuery only supports glTF export for Assembly objects.
        
        Args:
            model: CadQuery Workplane or Assembly object
            output_path: Path where the file should be saved (local temp)
            upload_to_storage: Whether to upload to configured storage (Azure/local)
            
        Returns:
            URL to the exported file
            
        Raises:
            RuntimeError: If export fails
        """
        try:
            # CadQuery requires an Assembly for glTF export
            # If model is already an Assembly, use it directly
            # Otherwise, wrap the workplane model in an assembly
            if isinstance(model, cq.Assembly):
                assembly = model
            else:
                assembly = cq.Assembly()
                assembly.add(model, name="building", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
            
            # Export to glTF (use .gltf extension for text format, .glb for binary)
            gltf_path = output_path.with_suffix('.gltf')
            assembly.save(str(gltf_path), exportType='GLTF')
            logger.info(f"Exported glTF to local path: {gltf_path}")
            
            if upload_to_storage:
                # Determine blob name
                blob_name = f"models/{gltf_path.name}"
                # Upload to storage and get URL
                url = FileManager.save_file(gltf_path, blob_name, content_type="model/gltf+json")
                return url
            
            return str(gltf_path)
        except Exception as e:
            logger.error(f"Failed to export to glTF: {str(e)}", exc_info=True)
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
        model,
        output_path: Path,
        projection_dir: tuple = (0, 0, 1),
        upload_to_storage: bool = True
    ) -> str:
        """
        Export model to SVG format for 2D drawings.
        
        Args:
            model: CadQuery Workplane or Assembly object
            output_path: Path where the file should be saved (local temp)
            projection_dir: Camera direction for projection (x, y, z)
            upload_to_storage: Whether to upload to configured storage (Azure/local)
            
        Returns:
            URL to the exported file
        """
        try:
            # If model is an Assembly, convert to workplane for SVG export
            # SVG export typically works better with workplanes
            if isinstance(model, cq.Assembly):
                # Extract all solids from assembly and combine into workplane
                all_solids = []
                for name, obj_data in model.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        obj = obj_data.obj
                        if isinstance(obj, cq.Workplane) and obj.objects:
                            for wp_obj in obj.objects:
                                if hasattr(wp_obj, 'Solids'):
                                    all_solids.extend(wp_obj.Solids())
                                elif hasattr(wp_obj, 'isValid') and wp_obj.isValid():
                                    all_solids.append(wp_obj)
                        elif hasattr(obj, 'Solids'):
                            all_solids.extend(obj.Solids())
                        elif hasattr(obj, 'isValid') and obj.isValid():
                            all_solids.append(obj)
                
                if all_solids:
                    # Create a single workplane containing all solids (no need to union them)
                    # The SVG exporter can handle multiple objects in a workplane
                    model = cq.Workplane("XY")
                    # Add all solids to the workplane's objects list
                    model.objects = all_solids
                else:
                    model = cq.Workplane("XY")
            
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
