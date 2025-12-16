"""
Model generation endpoints.
"""
import json
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from app.models.structure import BuildingRequest
from app.models.responses import ModelResponse, ErrorResponse, BOMDataResponse, BOMSubmissionResponse
from app.services.model_generator import ModelGenerator
from app.services.bom_service import BOMService
from app.utils.file_manager import FileManager
from app.utils.bom_data_manager import BOMDataManager
from app.utils.hash_utils import validate_structure_hash

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_base_url_from_request(request: Request) -> str:
    """
    Extract base URL from request for generating file URLs.
    Uses the request's host and scheme to construct the base URL.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Base URL string (e.g., "http://192.168.1.214:8080")
    """
    scheme = request.url.scheme
    host = request.url.hostname
    port = request.url.port
    
    if port and port not in [80, 443]:
        return f"{scheme}://{host}:{port}"
    else:
        return f"{scheme}://{host}"


@router.post("/generate-model", response_model=ModelResponse)
async def generate_model(
    request: BuildingRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
):
    """
    Generate a 3D model or 2D drawing from building specifications.
    
    This endpoint receives building specifications from the frontend and generates
    either a 3D model (glTF format) or a 2D drawing (SVG format) based on the
    specified view_mode.
    
    **View Modes:**
    - `3d`: Returns a glTF 3D model for WebGL rendering
    - `plan`: Returns a floor plan (top view) as SVG
    - `section`: Returns a cross-section view as SVG
    - `elevation`: Returns a front elevation view as SVG
    
    **Example Request:**
    ```json
    {
      "customer": {
        "customer_name": "John Doe",
        "customer_email": "john@example.com"
      },
      "structure": {
        "floorplan": { ... },
        "foundation": { ... },
        "roof": { ... },
        "sheathing": { ... },
        "flooring": { ... },
        "windows": [],
        "doors": []
      },
      "view_mode": "3d"
    }
    ```
    
    **Response:**
    Returns URLs to access the generated model or drawing.
    
    **Error Responses:**
    - `400`: Invalid request data (validation errors)
    - `500`: Model generation failed
    """
    try:
        # Validate structure hash if provided (log warning but don't block request)
        if request.structure_hash:
            from app.utils.hash_utils import calculate_structure_hash
            calculated_hash = calculate_structure_hash(request.structure.dict())
            
            if not validate_structure_hash(request.structure_hash, request.structure.dict()):
                logger.warning(
                    f"Structure hash validation failed. "
                    f"Provided hash: {request.structure_hash}, "
                    f"Calculated hash: {calculated_hash}. "
                    f"Continuing with request anyway."
                )
            else:
                logger.debug(f"Structure hash validation passed: {request.structure_hash}")
            
            # Save structure data to file using the structure_hash as filename
            # Only save if the file doesn't already exist
            if not FileManager.structure_data_exists(request.structure_hash):
                structure_data = request.structure.dict()
                FileManager.save_structure_data(request.structure_hash, structure_data)
                logger.info(f"Saved structure data for hash: {request.structure_hash}")
            else:
                logger.info(f"Structure data already exists for hash: {request.structure_hash}")
        
        # Extract base URL from request to ensure URLs are accessible from the client
        base_url = _get_base_url_from_request(http_request)
        logger.debug(f"Using base URL from request: {base_url}")
        
        # Generate the model
        response = ModelGenerator.generate(
            structure=request.structure,
            view_mode=request.view_mode,
            structure_hash=request.structure_hash,
            base_url_override=base_url,
            component_visibility=request.component_visibility
        )
        
        # Schedule cleanup of old files in the background
        background_tasks.add_task(FileManager.cleanup_old_files)
        
        return response
        
    except ValueError as e:
        # Validation or input errors
        logger.error(f"ValueError in model generation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        )
    except RuntimeError as e:
        # Model generation errors
        logger.error(f"RuntimeError in model generation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Model generation failed: {str(e)}"
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error in model generation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/models/{model_id}")
async def get_model_info(model_id: str):
    """
    Get information about a previously generated model.
    
    Args:
        model_id: Unique identifier of the model
        
    Returns:
        Model information and availability status
    """
    # Check if model files exist
    gltf_path = FileManager.get_model_path(model_id, "gltf")
    
    if gltf_path.exists():
        return {
            "model_id": model_id,
            "available": True,
            "url": FileManager.get_model_url(model_id, "gltf"),
            "local_path": str(gltf_path),
            "file_size": gltf_path.stat().st_size
        }
    
    # Check for drawings
    for view_mode in ["plan", "section", "elevation"]:
        drawing_path = FileManager.get_drawing_path(model_id, view_mode, "svg")
        if drawing_path.exists():
            return {
                "model_id": model_id,
                "available": True,
                "view_mode": view_mode,
                "url": FileManager.get_drawing_url(model_id, view_mode, "svg")
            }
    
    raise HTTPException(
        status_code=404,
        detail=f"Model {model_id} not found or has been cleaned up"
    )

@router.get("/debug/model-file/{filename:path}")
async def debug_model_file(filename: str):
    """
    Debug endpoint to check model file accessibility.
    
    Args:
        filename: Name of the model file (e.g., 7dbffd4f1d9ce0a5859673995d2281b6f3a1b916ded682e03fc1feb740db677a.gltf)
        
    Returns:
        File information and access details
    """
    from pathlib import Path
    from app.config import settings
    
    # Check if file exists
    file_path = settings.models_dir / filename
    
    if not file_path.exists():
        # List available files for debugging
        available_files = [f.name for f in settings.models_dir.glob('*') if f.is_file()]
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"File not found: {filename}",
                "requested_path": str(file_path),
                "models_dir": str(settings.models_dir),
                "available_files": available_files[:20]  # Limit to first 20
            }
        )
    
    # Check for associated .bin files
    file_stem = file_path.stem
    bin_files = list(file_path.parent.glob(f"{file_stem}*.bin"))
    
    return {
        "filename": filename,
        "exists": True,
        "path": str(file_path),
        "size": file_path.stat().st_size,
        "url": f"{settings.base_url}/models/{filename}",
        "static_url": f"/models/{filename}",
        "associated_bin_files": [f.name for f in bin_files],
        "models_dir": str(settings.models_dir),
        "base_url": settings.base_url
    }


@router.get("/structures/{structure_hash}")
async def get_structure_data(structure_hash: str):
    """
    Get structure data by hash.
    
    Args:
        structure_hash: SHA-256 hash of the structure data
        
    Returns:
        Structure data as JSON
    """
    # Check if structure data file exists
    if not FileManager.structure_data_exists(structure_hash):
        raise HTTPException(
            status_code=404,
            detail=f"Structure data with hash {structure_hash} not found"
        )
    
    try:
        # Read the structure data file
        file_path = FileManager.get_structure_data_path(structure_hash)
        with open(file_path, 'r', encoding='utf-8') as f:
            structure_data = json.load(f)
        
        return {
            "structure_hash": structure_hash,
            "structure_data": structure_data,
            "file_path": str(file_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to read structure data file {file_path}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read structure data: {str(e)}"
        )


@router.get("/bom/{structure_hash}", response_model=BOMDataResponse)
async def get_bom_data(structure_hash: str):
    """
    Get BOM data by structure hash.
    
    Args:
        structure_hash: SHA-256 hash of the structure data
        
    Returns:
        BOM data including materials, components, quantities, and levels
    """
    # Check if BOM data exists
    if not BOMDataManager.bom_data_exists(structure_hash):
        raise HTTPException(
            status_code=404,
            detail=f"BOM data with hash {structure_hash} not found. Generate a model first to create BOM data."
        )
    
    try:
        # Retrieve BOM data
        bom_data = BOMDataManager.get_bom_data(structure_hash)
        if not bom_data:
            raise HTTPException(
                status_code=404,
                detail=f"BOM data with hash {structure_hash} not found"
            )
        
        # Convert defaultdicts to regular dicts for JSON serialization
        serialized_bom = BOMDataManager.serialize_bom_data(bom_data)
        
        return BOMDataResponse(
            structure_hash=structure_hash,
            materials=serialized_bom.get('materials', []),
            bom_components=serialized_bom.get('bom_components', {}),
            bom_quantities=serialized_bom.get('bom_quantities', {}),
            bom_levels=serialized_bom.get('bom_levels', {}),
            created_at=serialized_bom.get('created_at'),
            updated_at=serialized_bom.get('updated_at')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve BOM data for {structure_hash}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve BOM data: {str(e)}"
        )


@router.post("/bom/{structure_hash}/submit", response_model=BOMSubmissionResponse)
async def submit_bom_to_mrp(structure_hash: str):
    """
    Submit BOM data to MRP system.
    
    This endpoint:
    1. Retrieves BOM data for the given structure_hash
    2. Creates materials in MRP system
    3. Creates production BOMs in MRP system
    4. Creates sales BOM in MRP system
    
    Args:
        structure_hash: SHA-256 hash of the structure data
        
    Returns:
        Submission results including success status and any errors
    """
    # Check if BOM data exists
    if not BOMDataManager.bom_data_exists(structure_hash):
        raise HTTPException(
            status_code=404,
            detail=f"BOM data with hash {structure_hash} not found. Generate a model first to create BOM data."
        )
    
    try:
        # Submit BOM to MRP
        result = BOMService.submit_bom_to_mrp(structure_hash)
        
        return BOMSubmissionResponse(
            structure_hash=structure_hash,
            success=result.get('success', False),
            materials=result.get('materials', {}),
            production_boms=result.get('production_boms', {}),
            sales_bom=result.get('sales_bom', {}),
            errors=result.get('errors', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit BOM to MRP for {structure_hash}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit BOM to MRP: {str(e)}"
        )
