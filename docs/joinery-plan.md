# Joinery Library Implementation Slice

## Summary
Implement ADR-0003 as an opt-in joinery compiler for framing essentials, using the notebooks in `docs/joinery` as geometry specs. Keep scene graph placement authoritative: the compiler may cut/fuse member geometry, but it must not move, rotate, or solve member positions.

## Key Changes
- Add `src/app/services/joinery/` with:
  - `base.py`: `JointSpec`, `GeometryOperation`, `JoineryError`, operation application helpers.
  - `compiler.py`: collect operations by member, apply them to blanks, store joined geometry.
  - focused modules for the first slice: `mortise_tenon.py`, `half_lap.py`, `plate_splice.py`, `notched_bearing.py`, `peg_bore.py`.
- Extend `SceneNode` conservatively:
  - preserve original geometry as `blank_geometry`;
  - store compiled output as `joined_geometry`;
  - keep `geometry` as the exported/rendered geometry, set to `joined_geometry` only after successful compile.
- Add transform helpers needed by joinery:
  - matrix inverse for current translate/principal-axis rotate transforms;
  - helper to map a joint-local cutter/fuse shape into member-local coordinates;
  - fail clearly for unsupported transforms rather than silently approximating.
- Add an opt-in flag on `FramingBuilder.build(...)`, default `False`, named `compile_joinery`.
  - Existing output remains unchanged unless enabled.
  - When enabled, framing creates or annotates member scene nodes, declares first-slice joints, compiles them, then projects the scene to the assembly.

## First-Slice Joint Coverage
- Port these notebook patterns first:
  - `post_to_sill_corner.ipynb`: sill half-lap plus post bottom tenon and sill mortise.
  - `stud_to_post_sill.ipynb`: stud stub tenons and receiving sill/girder mortises.
  - `plate_to_joist_false_plate.ipynb`: joist notch around top plate plus post-to-plate tenon/mortise.
  - `plate_to_plate.ipynb`: reciprocal half-lap plate splice, open mortises, tenons, and peg bores.
- Defer more complex profiled/angled work to later slices:
  - `brace_to_post_sill.ipynb`
  - `girt_to_post.ipynb`
  - `joist_to_sill.ipynb`
  - `plate_to_girder.ipynb`
  - `rafter.ipynb`

## Framing Integration
- Do not rewrite the whole framing builder yet.
- Introduce a small framing member registry while members are created:
  - stable `member_id` equals the existing CadQuery assembly component name;
  - record role, dimensions, face/story metadata, blank geometry, and scene node reference.
- Declare joints only where both participating members are known and named deterministically.
- If a joint cannot resolve members or transforms, return a validation error when `compile_joinery=True`; do not reposition geometry.
- Preserve BOM behavior unchanged: joinery changes shapes only, not material counts in this slice.

## Tests
- Add unit tests for each first-slice joint module:
  - expected bounding boxes;
  - expected volume change after cut/fuse;
  - mortise clearance and tenon dimensions;
  - peg bore position for plate splice;
  - valid CadQuery shape after `.clean()`.
- Add compiler tests:
  - multiple operations accumulate on one member;
  - operation order is deterministic by declaration order;
  - blank geometry remains available after compile;
  - failed joints do not mutate member placement.
- Add opt-in framing integration test:
  - existing `test_framing_scene_graph.py` still passes with default behavior;
  - new joinery-enabled fixture passes validation and contains joined geometry metadata;
  - semantic paths and component names remain stable.

## Assumptions
- The first implementation lives under `src/app/services/joinery/`, matching the current repo layout rather than creating a new top-level `cad/` package.
- `compile_joinery=False` remains the default until visual regression fixtures are in place.
- The notebooks remain source references in `docs/joinery`; production code should port their parameters and geometry behavior, not copy exploratory world-coordinate placement directly.
