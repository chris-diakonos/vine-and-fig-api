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
    def export_gltf(model, output_path: Path, upload_to_storage: bool = True, binary: bool = False) -> str:
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
            
            # Convert from inches to meters for glTF export
            # 1 inch = 0.0254 meters
            INCHES_TO_METERS = 0.0254
            
            # Debug: Log original assembly info
            original_components = list(assembly.traverse())
            logger.info(f"Exporting glTF: Original assembly has {len(original_components)} components")
            
            # Create a scaled assembly for export
            scaled_assembly = cq.Assembly()
            workplane_count = 0
            solid_count = 0
            empty_count = 0
            
            for name, obj_data in assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    obj = obj_data.obj
                    
                    # Debug: Check object type and geometry
                    if isinstance(obj, cq.Workplane):
                        workplane_count += 1
                        # Check if workplane has geometry
                        try:
                            val = obj.val()
                            if val is not None:
                                # Try to get bounding box
                                try:
                                    bb = val.BoundingBox()
                                    logger.debug(f"Component '{name}': Workplane with bounding box: "
                                               f"X=[{bb.xmin:.2f}, {bb.xmax:.2f}], "
                                               f"Y=[{bb.ymin:.2f}, {bb.ymax:.2f}], "
                                               f"Z=[{bb.zmin:.2f}, {bb.zmax:.2f}] (inches)")
                                except:
                                    logger.debug(f"Component '{name}': Workplane with geometry (no bounding box)")
                                
                                # Count solids
                                try:
                                    solids = val.Solids() if hasattr(val, 'Solids') else []
                                    if solids:
                                        solid_count += len(solids)
                                        logger.debug(f"Component '{name}': Contains {len(solids)} solid(s)")
                                except:
                                    pass
                            else:
                                empty_count += 1
                                logger.warning(f"Component '{name}': Empty workplane")
                        except Exception as e:
                            logger.warning(f"Component '{name}': Error checking workplane geometry: {e}")
                        
                        # Scale the workplane by scaling its underlying geometry
                        # Workplane doesn't have scale(), so we use transformGeometry on the underlying shape
                        try:
                            val = obj.val()
                            if val is not None:
                                # Use transformGeometry with a uniform scale
                                # Create a scale transformation (uniform scale in all directions)
                                try:
                                    # Import OCP (OpenCASCADE) for transformation
                                    from OCP.gp import gp_Trsf, gp_XYZ
                                    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
                                    
                                    # Create transformation
                                    trsf = gp_Trsf()
                                    trsf.SetScale(gp_XYZ(0, 0, 0), INCHES_TO_METERS)
                                    
                                    # Apply transformation
                                    transform = BRepBuilderAPI_Transform(val.wrapped, trsf)
                                    scaled_shape = transform.Shape()
                                    
                                    # Create new workplane with scaled geometry
                                    scaled_obj = cq.Workplane("XY")
                                    scaled_obj.objects = [scaled_shape]
                                except ImportError:
                                    # OCP not available, try alternative method
                                    logger.debug(f"Component '{name}': OCP not available, trying Matrix transform")
                                    try:
                                        from cadquery import Matrix
                                        scale_matrix = Matrix([
                                            [INCHES_TO_METERS, 0, 0, 0],
                                            [0, INCHES_TO_METERS, 0, 0],
                                            [0, 0, INCHES_TO_METERS, 0],
                                            [0, 0, 0, 1]
                                        ])
                                        scaled_val = val.transformGeometry(scale_matrix)
                                        scaled_obj = cq.Workplane("XY")
                                        scaled_obj.objects = [scaled_val]
                                    except Exception as matrix_error:
                                        logger.warning(f"Component '{name}': Matrix transform failed: {matrix_error}, using original")
                                        scaled_obj = obj
                                except Exception as transform_error:
                                    logger.warning(f"Component '{name}': Transform failed: {transform_error}, using original")
                                    scaled_obj = obj
                            else:
                                # Empty workplane, just copy it
                                scaled_obj = obj
                        except Exception as e:
                            logger.warning(f"Component '{name}': Failed to scale workplane, using original: {e}")
                            scaled_obj = obj
                    else:
                        logger.debug(f"Component '{name}': Non-Workplane object type: {type(obj)}")
                        scaled_obj = obj
                    
                    # Get color from original if available
                    color = obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.55, 0.45, 0.33)
                    scaled_assembly.add(scaled_obj, name=name, color=color)
                else:
                    logger.warning(f"Component '{name}': No object data found")
            
            # Debug: Log summary
            logger.info(f"glTF Export Summary: {workplane_count} workplanes, {solid_count} total solids, {empty_count} empty components")
            
            # Export to glTF. CadQuery writes binary GLB when the path uses .glb.
            gltf_path = output_path.with_suffix('.glb' if binary else '.gltf')
            
            # Log scaled assembly info
            scaled_components = list(scaled_assembly.traverse())
            logger.info(f"Scaled assembly has {len(scaled_components)} components (converted from inches to meters)")
            
            scaled_assembly.save(str(gltf_path), exportType='GLB' if binary else 'GLTF')
            logger.info(f"Exported glTF to local path: {gltf_path}")
            
            # Debug: Check file size
            if gltf_path.exists():
                file_size = gltf_path.stat().st_size
                logger.info(f"glTF file size: {file_size} bytes")
            else:
                logger.error(f"glTF file was not created at {gltf_path}")
            
            # Check for associated .bin files (glTF often creates binary buffer files)
            gltf_dir = gltf_path.parent
            gltf_stem = gltf_path.stem
            bin_files = list(gltf_dir.glob(f"{gltf_stem}*.bin"))
            if bin_files:
                logger.info(f"Found {len(bin_files)} associated .bin file(s) for glTF export")
                for bin_file in bin_files:
                    logger.debug(f"  - {bin_file.name} ({bin_file.stat().st_size} bytes)")
            
            if upload_to_storage:
                # Upload glTF file
                blob_name = f"models/{gltf_path.name}"
                content_type = "model/gltf-binary" if binary else "model/gltf+json"
                url = FileManager.save_file(gltf_path, blob_name, content_type=content_type)
                
                # Upload any associated .bin files
                for bin_file in bin_files:
                    bin_blob_name = f"models/{bin_file.name}"
                    FileManager.save_file(bin_file, bin_blob_name, content_type="application/octet-stream")
                    logger.info(f"Uploaded associated .bin file: {bin_file.name}")
                
                return url
            
            return str(gltf_path)
        except Exception as e:
            logger.error(f"Failed to export to glTF: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to export to glTF: {str(e)}")

    @staticmethod
    def export_glb(model, output_path: Path, upload_to_storage: bool = True) -> str:
        """
        Export model to binary GLB format.

        Args:
            model: CadQuery Workplane or Assembly object
            output_path: Path where the file should be saved
            upload_to_storage: Whether to upload using the existing storage path

        Returns:
            URL or local path to the exported file
        """
        return ExportService.export_gltf(model, output_path, upload_to_storage=upload_to_storage, binary=True)
    
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
            # If model is an Assembly, extract workplanes and union them for SVG export
            if isinstance(model, cq.Assembly):
                # Collect all workplanes from the assembly
                all_workplanes = []
                component_details = []
                
                for name, obj_data in model.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        obj = obj_data.obj
                        if isinstance(obj, cq.Workplane):
                            try:
                                val = obj.val()
                                if val is not None:
                                    all_workplanes.append(obj)
                                    # Debug: Get bounding box info
                                    try:
                                        bb = val.BoundingBox()
                                        component_details.append({
                                            'name': name,
                                            'bbox': {
                                                'x': [bb.xmin, bb.xmax],
                                                'y': [bb.ymin, bb.ymax],
                                                'z': [bb.zmin, bb.zmax]
                                            }
                                        })
                                        logger.debug(f"SVG Component '{name}': "
                                                   f"X=[{bb.xmin:.2f}, {bb.xmax:.2f}], "
                                                   f"Y=[{bb.ymin:.2f}, {bb.ymax:.2f}], "
                                                   f"Z=[{bb.zmin:.2f}, {bb.zmax:.2f}] (inches)")
                                    except Exception as e:
                                        logger.debug(f"SVG Component '{name}': Has geometry but no bounding box: {e}")
                                        component_details.append({'name': name, 'bbox': None})
                                else:
                                    logger.warning(f"SVG Component '{name}': Empty workplane")
                            except Exception as e:
                                logger.warning(f"SVG Component '{name}': Error checking workplane: {e}")
                        else:
                            logger.debug(f"SVG Component '{name}': Non-Workplane type: {type(obj)}")
                
                if all_workplanes:
                    logger.info(f"SVG Export: Found {len(all_workplanes)} workplanes in Assembly")
                    
                    # Calculate overall bounding box
                    if component_details:
                        all_x = []
                        all_y = []
                        all_z = []
                        for detail in component_details:
                            if detail['bbox']:
                                all_x.extend(detail['bbox']['x'])
                                all_y.extend(detail['bbox']['y'])
                                all_z.extend(detail['bbox']['z'])
                        
                        if all_x and all_y and all_z:
                            logger.info(f"SVG Export: Overall bounding box - "
                                      f"X=[{min(all_x):.2f}, {max(all_x):.2f}], "
                                      f"Y=[{min(all_y):.2f}, {max(all_y):.2f}], "
                                      f"Z=[{min(all_z):.2f}, {max(all_z):.2f}] (inches)")
                    
                    # Start with first workplane
                    model = all_workplanes[0]
                    # Union remaining workplanes
                    for i, wp in enumerate(all_workplanes[1:], 1):
                        try:
                            model = model.union(wp)
                            logger.debug(f"SVG Export: Unioned workplane {i+1}/{len(all_workplanes)}")
                        except Exception as e:
                            logger.warning(f"SVG Export: Failed to union workplane {i+1}: {e}")
                else:
                    # No workplanes found, create empty workplane
                    model = cq.Workplane("XY")
                    logger.warning("SVG Export: No workplanes found in Assembly - creating empty workplane")
            
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
            
            # Debug: Check final model before export
            try:
                val = model.val()
                if val is not None:
                    try:
                        bb = val.BoundingBox()
                        logger.info(f"SVG Export: Final model bounding box - "
                                  f"X=[{bb.xmin:.2f}, {bb.xmax:.2f}], "
                                  f"Y=[{bb.ymin:.2f}, {bb.ymax:.2f}], "
                                  f"Z=[{bb.zmin:.2f}, {bb.zmax:.2f}] (inches)")
                    except:
                        logger.debug("SVG Export: Final model has geometry but no bounding box")
                else:
                    logger.warning("SVG Export: Final model has no geometry!")
            except Exception as e:
                logger.warning(f"SVG Export: Error checking final model: {e}")
            
            exporters.export(model, str(output_path), opt=svg_opts)
            logger.info(f"Exported SVG to local path: {output_path}")
            
            # Debug: Check file size
            if output_path.exists():
                file_size = output_path.stat().st_size
                logger.info(f"SVG file size: {file_size} bytes")
                if file_size < 1000:
                    logger.warning(f"SVG file is very small ({file_size} bytes) - may be empty or invalid")
            else:
                logger.error(f"SVG file was not created at {output_path}")
            
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
        export_type: Literal["gltf", "glb", "step", "svg", "stl", "dxf"],
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
            "glb": ExportService.export_glb,
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
