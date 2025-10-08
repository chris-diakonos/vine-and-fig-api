"""
Model generation endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.structure import BuildingRequest
from app.models.responses import ModelResponse, ErrorResponse
from app.services.model_generator import ModelGenerator
from app.utils.file_manager import FileManager

router = APIRouter()


@router.post("/generate-model", response_model=ModelResponse)
async def generate_model(
    request: BuildingRequest,
    background_tasks: BackgroundTasks
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
        # Generate the model
        response = ModelGenerator.generate(
            structure=request.structure,
            view_mode=request.view_mode
        )
        
        # Schedule cleanup of old files in the background
        background_tasks.add_task(FileManager.cleanup_old_files)
        
        return response
        
    except ValueError as e:
        # Validation or input errors
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        )
    except RuntimeError as e:
        # Model generation errors
        raise HTTPException(
            status_code=500,
            detail=f"Model generation failed: {str(e)}"
        )
    except Exception as e:
        # Unexpected errors
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
            "url": FileManager.get_model_url(model_id, "gltf")
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
