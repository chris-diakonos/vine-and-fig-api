#!/usr/bin/env python3
"""
Verify window frame fix: check AABBs for left/right wall windows.
Must show y_overlap > 0 and reasonable x_mis (≈frame depth).
"""
import json
import sys
from app.services.model_generator import ModelGenerator
from app.models.structure import Structure
from app.models.customer import Customer

def get_aabb(shape):
    """Get axis-aligned bounding box from a CadQuery shape."""
    try:
        if hasattr(shape, 'val'):
            bbox = shape.val().BoundingBox()
        elif hasattr(shape, 'BoundingBox'):
            bbox = shape.BoundingBox()
        else:
            return None
        return {
            'xmin': bbox.xmin,
            'xmax': bbox.xmax,
            'ymin': bbox.ymin,
            'ymax': bbox.ymax,
            'zmin': bbox.zmin,
            'zmax': bbox.zmax,
            'x_span': bbox.xmax - bbox.xmin,
            'y_span': bbox.ymax - bbox.ymin,
            'z_span': bbox.zmax - bbox.zmin
        }
    except Exception as e:
        print(f"Error getting AABB: {e}")
        return None

def calculate_overlap(aabb1, aabb2, axis='y'):
    """Calculate overlap between two AABBs along given axis."""
    if not aabb1 or not aabb2:
        return 0.0
    
    min_key = f'{axis}min'
    max_key = f'{axis}max'
    
    # Overlap is the intersection of the two ranges
    overlap_min = max(aabb1[min_key], aabb2[min_key])
    overlap_max = min(aabb1[max_key], aabb2[max_key])
    
    overlap = overlap_max - overlap_min
    return max(0.0, overlap)

def main():
    print("=" * 80)
    print("WINDOW FRAME VERIFICATION (PR #19 Fix)")
    print("=" * 80)
    
    # Load example request
    with open('example_request.json', 'r') as f:
        request_data = json.load(f)
    
    # Parse into Structure object
    print("\nParsing structure from example_request.json...")
    structure = Structure(**request_data['structure'])
    
    print("Building model directly (bypassing export)...")
    from app.services.building_builder import BuildingBuilder
    from app.utils.hash_utils import calculate_structure_hash
    
    structure_hash = calculate_structure_hash(structure.model_dump())
    try:
        assembly, bom_data = BuildingBuilder.build(structure, structure_hash)
    except Exception as e:
        print(f"ERROR: Failed to build model: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    if not assembly:
        print("ERROR: Failed to generate model assembly!")
        return 1
    
    print("\nSearching for side wall (left/right) window components...")
    
    # Find left and right wall window frame components
    left_windows = {}
    right_windows = {}
    
    for name, obj_data in assembly.traverse():
        if not hasattr(obj_data, 'obj') or obj_data.obj is None:
            continue
        
        # Look for left wall windows
        if '_left_' in name and 'window_' in name:
            # Extract component type (left_frame, right_frame, top_frame, bottom_frame_sill)
            if 'left_frame' in name or 'right_frame' in name or 'top_frame' in name or 'bottom_frame_sill' in name:
                component_type = name.split('_')[-2] + '_' + name.split('_')[-1] if 'bottom_frame' in name else name.split('_')[-1]
                if 'story' in name:
                    story = name.split('story')[1].split('_')[0]
                    key = f"left_story{story}"
                    if key not in left_windows:
                        left_windows[key] = {}
                    left_windows[key][component_type] = obj_data.obj
        
        # Look for right wall windows
        if '_right_' in name and 'window_' in name:
            if 'left_frame' in name or 'right_frame' in name or 'top_frame' in name or 'bottom_frame_sill' in name:
                component_type = name.split('_')[-2] + '_' + name.split('_')[-1] if 'bottom_frame' in name else name.split('_')[-1]
                if 'story' in name:
                    story = name.split('story')[1].split('_')[0]
                    key = f"right_story{story}"
                    if key not in right_windows:
                        right_windows[key] = {}
                    right_windows[key][component_type] = obj_data.obj
    
    print(f"\nFound {len(left_windows)} left wall window(s)")
    print(f"Found {len(right_windows)} right wall window(s)")
    
    if not left_windows and not right_windows:
        print("\nWARNING: No side wall windows found!")
        return 1
    
    all_passed = True
    
    # Check left wall windows
    for window_key, components in left_windows.items():
        print(f"\n{'='*80}")
        print(f"LEFT WALL WINDOW: {window_key}")
        print(f"{'='*80}")
        
        # Get AABBs
        aabbs = {}
        for comp_name, obj in components.items():
            aabb = get_aabb(obj)
            if aabb:
                aabbs[comp_name] = aabb
                print(f"\n{comp_name.upper()}:")
                print(f"  X: [{aabb['xmin']:.3f}, {aabb['xmax']:.3f}] span={aabb['x_span']:.3f}\"")
                print(f"  Y: [{aabb['ymin']:.3f}, {aabb['ymax']:.3f}] span={aabb['y_span']:.3f}\"")
                print(f"  Z: [{aabb['zmin']:.3f}, {aabb['zmax']:.3f}] span={aabb['z_span']:.3f}\"")
        
        # Calculate overlaps (for left/right walls, frame extends in Y, so check Y overlap)
        if 'frame' in aabbs and 'sill' in aabbs:
            y_overlap = calculate_overlap(aabbs['frame'], aabbs['sill'], 'y')
            print(f"\nJAMB-TO-SILL Y-OVERLAP: {y_overlap:.3f}\"")
            if y_overlap > 0:
                print("  ✓ PASS: Y-overlap > 0")
            else:
                print("  ✗ FAIL: Y-overlap should be > 0")
                all_passed = False
        
        # Check X misalignment (should be ~frame depth ≈4-5")
        if 'frame' in aabbs and 'sill' in aabbs:
            x_mis = abs(aabbs['frame']['xmin'] - aabbs['sill']['xmin'])
            print(f"X-MISALIGNMENT (frame vs sill): {x_mis:.3f}\"")
            if 3 < x_mis < 6:
                print("  ✓ PASS: X-misalignment ≈ frame depth")
            else:
                print(f"  ✗ FAIL: X-misalignment should be ≈4-5\" (frame depth), got {x_mis:.3f}\"")
                all_passed = False
    
    # Check right wall windows
    for window_key, components in right_windows.items():
        print(f"\n{'='*80}")
        print(f"RIGHT WALL WINDOW: {window_key}")
        print(f"{'='*80}")
        
        # Get AABBs
        aabbs = {}
        for comp_name, obj in components.items():
            aabb = get_aabb(obj)
            if aabb:
                aabbs[comp_name] = aabb
                print(f"\n{comp_name.upper()}:")
                print(f"  X: [{aabb['xmin']:.3f}, {aabb['xmax']:.3f}] span={aabb['x_span']:.3f}\"")
                print(f"  Y: [{aabb['ymin']:.3f}, {aabb['ymax']:.3f}] span={aabb['y_span']:.3f}\"")
                print(f"  Z: [{aabb['zmin']:.3f}, {aabb['zmax']:.3f}] span={aabb['z_span']:.3f}\"")
        
        # Calculate overlaps
        if 'frame' in aabbs and 'sill' in aabbs:
            y_overlap = calculate_overlap(aabbs['frame'], aabbs['sill'], 'y')
            print(f"\nJAMB-TO-SILL Y-OVERLAP: {y_overlap:.3f}\"")
            if y_overlap > 0:
                print("  ✓ PASS: Y-overlap > 0")
            else:
                print("  ✗ FAIL: Y-overlap should be > 0")
                all_passed = False
        
        # Check X misalignment
        if 'frame' in aabbs and 'sill' in aabbs:
            x_mis = abs(aabbs['frame']['xmin'] - aabbs['sill']['xmin'])
            print(f"X-MISALIGNMENT (frame vs sill): {x_mis:.3f}\"")
            if 3 < x_mis < 6:
                print("  ✓ PASS: X-misalignment ≈ frame depth")
            else:
                print(f"  ✗ FAIL: X-misalignment should be ≈4-5\" (frame depth), got {x_mis:.3f}\"")
                all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Windows are properly aligned!")
        print("="*80)
        return 0
    else:
        print("✗ SOME CHECKS FAILED - See details above")
        print("="*80)
        return 1

if __name__ == '__main__':
    sys.exit(main())
