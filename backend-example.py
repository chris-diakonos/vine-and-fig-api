"""
Example Backend API for Vine & Fig Building Designer

This example shows how to integrate the React frontend with a Python/FastAPI backend
that generates 3D models using CadQuery and exports them as glTF files.

Requirements:
- fastapi
- uvicorn
- cadquery
- pydantic
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import cadquery as cq
from cadquery import exporters
import uuid
from datetime import datetime
import os
import tempfile

app = FastAPI(title="Vine & Fig Building Designer API")

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models matching the JSON schema
class Customer(BaseModel):
    customer_name: str
    customer_email: EmailStr

class Dimensions(BaseModel):
    front: float
    rear: float
    left: float
    right: float
    building_height: float

class Spacing(BaseModel):
    stud_spacing: float
    joist_spacing: float
    rafter_spacing: float
    bay_width: float
    pile_width: float

class Floorplan(BaseModel):
    floorplan_type: str
    depth: str
    stories: int
    hall_width: float
    dimensions: Dimensions
    spacing: Spacing
    bays: Optional[Dict[str, List[float]]] = None

class Foundation(BaseModel):
    foundation_type: str
    foundation_block_size: Optional[List[int]] = None
    foundation_courses: int
    foundation_block_joint: float

class Roof(BaseModel):
    roof_pitch: float
    roof_type: str
    roof_panel_type: str
    roof_panel_color: str
    roof_panel_exposure: int

class Sheathing(BaseModel):
    sheathing_species: str
    sheathing_exposure: int
    sheathing_height: float
    sheathing_type: str

class Flooring(BaseModel):
    flooring_type: str
    flooring_species: str
    flooring_thickness: float
    flooring_width: float
    flooring_exposure: float

class Structure(BaseModel):
    floorplan: Floorplan
    foundation: Foundation
    roof: Roof
    sheathing: Sheathing
    flooring: Flooring
    windows: List[Dict[str, Any]] = []
    doors: List[Dict[str, Any]] = []

class BuildingRequest(BaseModel):
    customer: Customer
    structure: Structure
    view_mode: str = '3d'  # Options: '3d', 'plan', 'section', 'elevation'

class ModelResponse(BaseModel):
    modelUrl: str  # URL to the model/image
    gltfUrl: Optional[str] = None  # For 3D models
    imageUrl: Optional[str] = None  # For 2D views
    viewMode: str  # Echo back the view mode
    modelId: str
    timestamp: str

def generate_building_model(structure: Structure) -> cq.Workplane:
    """
    Generate a 3D building model using CadQuery based on form data.
    
    This is a simplified example. In production, you would:
    - Use the molding_shapes library for detailed moldings
    - Add windows and doors
    - Add roof geometry
    - Add foundation details
    - Apply materials and textures
    """
    floorplan = structure.floorplan
    dims = floorplan.dimensions
    
    # Create the main building box
    building = cq.Workplane("XY").box(
        dims.front,
        dims.left,
        dims.building_height
    )
    
    # Add foundation
    foundation_height = structure.foundation.foundation_courses * 12  # Assume 12" per course
    foundation = cq.Workplane("XY").box(
        dims.front + 24,  # Wider than building
        dims.left + 24,
        foundation_height
    ).translate((0, 0, -foundation_height/2 - dims.building_height/2))
    
    # Combine building and foundation
    complete_structure = building.union(foundation)
    
    # Add roof (simple gable for now)
    roof_height = (dims.front / 2) * (structure.roof.roof_pitch / 12)
    roof_peak = cq.Workplane("XY").box(
        dims.front,
        dims.left,
        roof_height
    ).translate((0, 0, dims.building_height/2 + roof_height/2))
    
    # Final model
    final_model = complete_structure.union(roof_peak)
    
    return final_model

@app.post("/api/generate-model", response_model=ModelResponse)
async def generate_model(request: BuildingRequest):
    """
    Generate a 3D model or 2D drawing from the building specifications.
    
    This endpoint:
    1. Receives building specifications and view_mode from the frontend
    2. Generates a 3D model or 2D drawing using CadQuery
    3. Exports to glTF (3D) or SVG/PNG (2D) format
    4. Returns the file URL
    
    View modes:
    - '3d': Returns a glTF 3D model
    - 'plan': Returns a floor plan (top view) as PNG/SVG
    - 'section': Returns a section view as PNG/SVG
    - 'elevation': Returns an elevation view (front) as PNG/SVG
    """
    try:
        # Generate the 3D model
        model = generate_building_model(request.structure)
        
        # Create unique model ID
        model_id = str(uuid.uuid4())
        temp_dir = tempfile.gettempdir()
        
        view_mode = request.view_mode
        
        if view_mode == '3d':
            # Export to glTF for 3D view
            gltf_path = os.path.join(temp_dir, f"{model_id}.gltf")
            exporters.export(model, gltf_path, exportType=exporters.ExportTypes.GLTF)
            
            model_url = f"http://localhost:8000/models/{model_id}.gltf"
            
            return ModelResponse(
                modelUrl=model_url,
                gltfUrl=model_url,
                imageUrl=None,
                viewMode='3d',
                modelId=model_id,
                timestamp=datetime.utcnow().isoformat()
            )
        
        elif view_mode in ['plan', 'section', 'elevation']:
            # Export to SVG for 2D views
            svg_path = os.path.join(temp_dir, f"{model_id}_{view_mode}.svg")
            
            # Set the view direction based on view_mode
            if view_mode == 'plan':
                # Top view (looking down Z axis)
                svg_opts = {"projectionDir": (0, 0, 1)}
            elif view_mode == 'section':
                # Side view (looking along Y axis)
                svg_opts = {"projectionDir": (0, 1, 0)}
            else:  # elevation
                # Front view (looking along X axis)
                svg_opts = {"projectionDir": (1, 0, 0)}
            
            # Export to SVG
            exporters.export(model, svg_path, opt=svg_opts)
            
            image_url = f"http://localhost:8000/drawings/{model_id}_{view_mode}.svg"
            
            return ModelResponse(
                modelUrl=image_url,
                gltfUrl=None,
                imageUrl=image_url,
                viewMode=view_mode,
                modelId=model_id,
                timestamp=datetime.utcnow().isoformat()
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Invalid view_mode: {view_mode}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model generation failed: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Vine & Fig Building Designer API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
To run this backend:

1. Install dependencies:
   pip install fastapi uvicorn cadquery pydantic[email]

2. Run the server:
   python backend-example.py

3. Or with uvicorn directly:
   uvicorn backend-example:app --reload --port 8000

The API will be available at http://localhost:8000
API docs will be at http://localhost:8000/docs
"""

