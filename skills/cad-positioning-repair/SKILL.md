---
name: cad-positioning-repair
description: Diagnose and repair Wicketgate CAD scene-graph positioning defects. Use when working on window, wall, assembly, transform, semantic path, deterministic validation, GLB inspection, or 3D placement regressions.
disable-model-invocation: true
---

# CAD Positioning Repair

Use this workflow when repairing 3D positioning or scene-graph defects.

## Core Rule

Build locally, assemble hierarchically, place once.

Do not fix a misplaced child by adding a world-space offset that bypasses its
owning assembly.

## Diagnosis

Classify the defect before editing:

1. Local geometry: the part has the wrong dimensions or shape in its own local coordinates.
2. Child-to-parent assembly: the part is placed incorrectly inside its owning assembly.
3. Ancestor placement: a complete assembly is placed incorrectly on its parent.

Repair the smallest level that owns the failed relationship.

## Coordinate Contract

Use the cornerstone coordinate system for new placement logic:

- `cornerstone`: front-left exterior foundation corner at grade.
- `(0, 0, 0)`: the cornerstone.
- `+X`: left to right across the front elevation.
- `+Y`: front to rear along building depth.
- `+Z`: up from grade.

For windows:

- Origin: lower-left exterior corner of the opening.
- `+X`: left to right across the opening.
- `+Y`: exterior to interior through wall depth.
- `+Z`: bottom to top.

Use compatibility helpers when projecting new placement semantics into legacy
CadQuery coordinates.

## Repair Workflow

1. Inspect the failing semantic path, validation result, or visual target.
2. Identify whether the defect is local geometry, child placement, or ancestor placement.
3. Inspect the owning assembly code and related transform helper.
4. Make the smallest coherent change at the owning level.
5. Run deterministic validation before visual review.
6. Check `components.json` and `validation.json` for semantic paths, bounds, and transforms.
7. Use GLB visual inspection only after deterministic checks pass.

## Validation Expectations

For window positioning, preserve or add checks for:

- local window bounds;
- sash containment within the frame;
- rails, stiles, muntins, and glass within their assembly envelope;
- common glazing plane alignment;
- wall placement through one parent transform;
- stable semantic paths from source to artifacts.
