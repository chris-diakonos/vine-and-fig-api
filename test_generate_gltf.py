"""
Test script to generate a glTF file from a structure file.

Usage:
    # Run inside Docker container:
    docker-compose exec api python /app/test_generate_gltf.py
    
    # Or copy to container and run:
    docker-compose cp test_generate_gltf.py vine-and-fig-api:/app/
    docker-compose exec api python /app/test_generate_gltf.py
"""
import json
import sys
import os
from pathlib import Path

# Check if we're in the right environment
try:
    import pydantic
except ImportError:
    print("Error: Missing dependencies. This script must be run inside the Docker container.")
    print("\nTo run this script:")
    print("  1. Make sure the Docker container is running: docker-compose up -d")
    print("  2. Run the script in the container:")
    print("     docker-compose exec api python /app/test_generate_gltf.py")
    print("\nOr copy the file to the container first:")
    print("  docker-compose cp test_generate_gltf.py vine-and-fig-api:/app/")
    sys.exit(1)

# Add src to path so we can import app modules
# In Docker, the working directory is /app, so paths are relative to that
if os.path.exists("/app"):
    # Running in Docker
    sys.path.insert(0, "/app/src")
    base_path = Path("/app")
else:
    # Running locally (if dependencies are installed)
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    base_path = Path(__file__).parent

from app.models.structure import Structure
from app.services.model_generator import ModelGenerator


def main():
    # Structure hash from filename
    structure_hash = "7dbffd4f1d9ce0a5859673995d2281b6f3a1b916ded682e03fc1feb740db677a"
    
    # Path to structure file
    # In Docker, use /app/temp, otherwise use relative path
    if os.path.exists("/app"):
        structure_file = base_path / "temp" / "structures" / f"{structure_hash}.json"
    else:
        structure_file = base_path / "temp" / "structures" / f"{structure_hash}.json"
    
    if not structure_file.exists():
        print(f"Error: Structure file not found: {structure_file}")
        return 1
    
    print(f"Loading structure from: {structure_file}")
    
    # Load structure data
    with open(structure_file, 'r') as f:
        structure_data = json.load(f)
    
    # Parse into Structure model
    try:
        structure = Structure(**structure_data)
        print("Structure loaded successfully")
    except Exception as e:
        print(f"Error parsing structure: {e}")
        return 1
    
    # Generate 3D model (glTF)
    print(f"\nGenerating 3D model (glTF) with structure hash: {structure_hash}")
    try:
        response = ModelGenerator.generate(
            structure=structure,
            view_mode="3d",
            structure_hash=structure_hash
        )
        
        print(f"\n✓ Model generated successfully!")
        print(f"  Model URL: {response.model_url}")
        if response.gltf_url:
            print(f"  glTF URL: {response.gltf_url}")
        print(f"  Model ID: {response.model_id}")
        print(f"  View Mode: {response.view_mode}")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error generating model: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

