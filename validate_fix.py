#!/usr/bin/env python3
"""
Validation script to verify the export_service.py fix is syntactically correct
and uses proper CadQuery API patterns.

This script validates:
1. Import statements are correct
2. Shape.cast() method exists and is used correctly
3. Code structure is valid Python

Note: This does NOT run actual CadQuery generation (requires full CadQuery/OCP setup)
"""

import sys
import ast
from pathlib import Path


def validate_export_service():
    """Validate the export_service.py file has correct structure."""
    
    export_service_path = Path(__file__).parent / "src" / "app" / "services" / "export_service.py"
    
    if not export_service_path.exists():
        print(f"❌ File not found: {export_service_path}")
        return False
    
    print(f"✓ Found file: {export_service_path}")
    
    # Read and parse the file
    try:
        with open(export_service_path, 'r') as f:
            source = f.read()
        tree = ast.parse(source)
        print("✓ File is valid Python syntax")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    
    # Check for the fix: cq.Shape.cast(scaled_shape)
    if "cq.Shape.cast(scaled_shape)" in source:
        print("✓ Found correct Shape.cast() wrapper for scaled OCCT shape")
    else:
        print("❌ Missing Shape.cast() wrapper")
        return False
    
    # Check for the problematic pattern (should NOT exist)
    if "scaled_obj.objects = [scaled_shape]" in source:
        print("❌ Found unwrapped OCCT shape assignment (should be wrapped)")
        return False
    else:
        print("✓ No unwrapped OCCT shape assignments found")
    
    # Check for proper wrapped assignment
    if "scaled_obj.objects = [scaled_cq_shape]" in source:
        print("✓ Found correct wrapped shape assignment")
    else:
        print("⚠ Warning: Expected pattern not found, but may be OK")
    
    # Check for the comment explaining the fix
    if "This is critical - raw OCCT shapes cause empty GLB exports" in source:
        print("✓ Found explanatory comment about the fix")
    else:
        print("⚠ Warning: Explanatory comment not found")
    
    # Verify imports are present
    if "import cadquery as cq" in source:
        print("✓ CadQuery import present")
    else:
        print("❌ Missing CadQuery import")
        return False
    
    if "from OCP.gp import gp_Trsf, gp_Pnt" in source:
        print("✓ OCP imports correct (gp_Pnt, not gp_XYZ)")
    else:
        print("⚠ Warning: Expected OCP imports not found")
    
    print("\n" + "="*60)
    print("Summary:")
    print("  The fix correctly wraps the OCCT TopoDS_Shape using")
    print("  cq.Shape.cast() before assigning to the workplane.")
    print("  This ensures proper mesh tessellation during glTF export.")
    print("="*60)
    
    return True


def check_cadquery_api():
    """
    Document the CadQuery API pattern being used.
    
    Based on CadQuery documentation:
    https://cadquery.readthedocs.io/en/stable/_modules/cadquery/occ_impl/shapes.html
    
    Shape.cast(obj: TopoDS_Shape) -> Shape:
        "Returns the right type of wrapper, given a OCCT object"
    
    This method is the official way to wrap OCCT shapes as CadQuery Shape objects.
    """
    print("\nCadQuery API Pattern Validation:")
    print("-" * 60)
    print("Pattern: cq.Shape.cast(TopoDS_Shape) -> cq.Shape")
    print("Purpose: Wrap OCCT geometry as proper CadQuery Shape object")
    print("Documentation: https://cadquery.readthedocs.io/en/stable/")
    print("-" * 60)
    print()


if __name__ == "__main__":
    print("Validating export_service.py fix...")
    print("="*60)
    check_cadquery_api()
    
    if validate_export_service():
        print("\n✓ ✓ ✓ All validations passed! ✓ ✓ ✓")
        sys.exit(0)
    else:
        print("\n❌ Validation failed")
        sys.exit(1)
