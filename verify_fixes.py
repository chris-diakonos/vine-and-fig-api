#!/usr/bin/env python3
"""Quick AABB verification from GLB."""
import json
import struct
from pathlib import Path

glb_path = Path('output/model.glb')
with open(glb_path, 'rb') as f:
    magic = f.read(4)
    version, length = struct.unpack('<II', f.read(8))
    json_len = struct.unpack('<I', f.read(4))[0]
    json_type = f.read(4)
    gltf = json.loads(f.read(json_len).decode('utf-8'))

nodes = gltf.get('nodes', [])
meshes = gltf.get('meshes', [])
accessors = gltf.get('accessors', [])

# Extract bounds
results = []
for node in nodes:
    mesh_idx = node.get('mesh')
    if mesh_idx is not None and mesh_idx < len(meshes):
        mesh = meshes[mesh_idx]
        name = mesh.get('name', node.get('name', '?'))
        prims = mesh.get('primitives', [])
        if prims:
            pos_idx = prims[0].get('attributes', {}).get('POSITION')
            if pos_idx is not None and pos_idx < len(accessors):
                acc = accessors[pos_idx]
                mn, mx = acc.get('min', [0,0,0]), acc.get('max', [0,0,0])
                results.append({'name': name, 'min': mn, 'max': mx, 'size': [mx[i]-mn[i] for i in range(3)]})

print(f"Total components: {len(results)}")

# Issue #1: Window sash Y extent
front_sash = [r for r in results if 'window_front' in r['name'] and 'sash' in r['name']]
if front_sash:
    avg_y = sum(r['size'][1] for r in front_sash) / len(front_sash)
    print(f"\n[Issue #1] Front sash Y extent: {avg_y:.2f}\" (expect ~1.4\", bug was ~34.5\")")
    print(f"  {'✅ PASS' if avg_y < 5 else '❌ FAIL'}")

# Issue #2: Rafter tails
front_rafter = [r for r in results if 'rafter_front' in r['name']]
if front_rafter:
    avg_ymax = sum(r['max'][1] for r in front_rafter) / len(front_rafter)
    overhang = avg_ymax - 2.674
    print(f"\n[Issue #2] Front rafter overhang: {overhang:.2f}\" (target 12\")")
    print(f"  {'✅ PASS' if 11 <= overhang <= 13 else '❌ FAIL'}")

rear_rafter = [r for r in results if 'rafter_rear' in r['name']]
if rear_rafter:
    avg_ymin = sum(r['min'][1] for r in rear_rafter) / len(rear_rafter)
    overhang = -250.528 - avg_ymin
    print(f"  Rear rafter overhang: {overhang:.2f}\" (target 12\")")
    print(f"  {'✅ PASS' if 11 <= overhang <= 13 else '❌ FAIL'}")

# Issue #3: Gable overhang
roof = [r for r in results if 'roof_' in r['name']]
if roof:
    xmin = min(r['min'][0] for r in roof)
    xmax = max(r['max'][0] for r in roof)
    left_oh = -2.674 - xmin
    right_oh = xmax - 482.674
    print(f"\n[Issue #3] Gable overhang L/R: {left_oh:.2f}\" / {right_oh:.2f}\" (target 12\")")
    print(f"  {'✅ PASS' if 11 <= left_oh <= 15 and 11 <= right_oh <= 15 else '❌ FAIL'}")

# Issue #4: Side window Y overlap
left_win = [r for r in results if 'window_left' in r['name']]
if left_win:
    jambs = [r for r in left_win if 'frame' in r['name'] and 'sash' not in r['name']]
    headers = [r for r in left_win if 'top_frame' in r['name']]
    if jambs and headers:
        jy_min, jy_max = min(r['min'][1] for r in jambs), max(r['max'][1] for r in jambs)
        hy_min, hy_max = min(r['min'][1] for r in headers), max(r['max'][1] for r in headers)
        overlap = min(jy_max, hy_max) - max(jy_min, hy_min)
        print(f"\n[Issue #4] Left window Y overlap: {overlap:.2f}\" (expect >30\")")
        print(f"  {'✅ PASS' if overlap > 30 else '❌ FAIL'}")
