# ADR-0001: Hierarchical Scene Graph for CAD Assembly and Placement

**Status:** Accepted
**Date:** 2026-09-04

## Implementation Scope

This ADR is accepted as the direction for the generator. The first implementation
slice is intentionally narrow: windows move to the hierarchical local-coordinate
model first, while the remaining builders continue to use their existing
coordinate conventions through compatibility helpers.

## Context

The current CadQuery building generator is primarily procedural. Individual building members and components are generated and then positioned into the final building using translation and rotation operations.

This approach worked adequately while the generator was small, but it has become increasingly difficult to modify safely. In particular, related members frequently contain independent positioning logic expressed directly or indirectly in building coordinates.

For example, the members of a window sash may each independently determine their final placement:

```text
Building
├── place left stile
├── place right stile
├── place top rail
├── place bottom rail
└── place muntins
```

Although these members conceptually form a single sash assembly, their spatial relationships are not represented explicitly by the architecture. Instead, those relationships emerge from multiple pieces of procedural positioning code agreeing on the same assumptions.

This creates strong implicit coupling.

A change to the dimensions, rotation, translation, origin, or positioning logic of one member can cause it to become misaligned with related members. Fixing the resulting visual problem locally can then introduce a regression elsewhere.

This problem has occurred both during manual development and during experimentation with an agentic coding and visual-review loop. The agent loop makes the problem particularly visible: a visual reviewer can correctly identify a misplaced member, and a coding agent can locally correct that member's translation or rotation, while unintentionally breaking its relationship with other members.

Repeated visual iteration therefore does not necessarily converge. The agent is attempting to optimize geometry whose spatial relationships are insufficiently represented in the underlying architecture.

The problem is architectural rather than primarily an agent-prompting or CadQuery problem.

## Decision

The CAD generator will adopt a **hierarchical scene graph and local-coordinate assembly model**.

Objects will be constructed and positioned relative to their immediate parent rather than independently positioned in building/world coordinates.

The conceptual hierarchy will resemble:

```text
Building
├── Wall
│   ├── Window
│   │   ├── Frame
│   │   ├── Upper Sash
│   │   │   ├── Left Stile
│   │   │   ├── Right Stile
│   │   │   ├── Rails
│   │   │   └── Muntins
│   │   └── Lower Sash
│   └── Door
├── Roof
└── Other assemblies
```

Each node owns:

1. Geometry expressed in a canonical local coordinate system, where applicable.
2. A transform describing its placement relative to its immediate parent.
3. Child nodes, where the object is an assembly.

Final building-space geometry is derived by composing transforms through the hierarchy.

Conceptually:

```text
member local space
      ↓
sash local space
      ↓
window local space
      ↓
wall local space
      ↓
building space
```

A member's final world transform is therefore derived from its ancestry rather than independently calculated.

## Coordinate-Space Ownership

A node may know:

- its own local coordinate system;
- its geometry;
- its dimensions and semantic role;
- its transform relative to its immediate parent.

A node should not depend on the coordinate systems of arbitrary ancestors.

For example:

- A rail may know where it belongs within a sash.
- A sash may know where it belongs within a window.
- A window may know where it belongs within a wall.
- A wall may know where it belongs within the building.

A rail must not calculate its position from the orientation or location of the building wall.

This establishes the architectural invariant:

> **A component is positioned by the assembly that owns its spatial relationship. Building-space placement must not leak into child-component geometry.**



## Geometry, Assembly, and Placement

The generator will distinguish three responsibilities.

### Geometry

Geometry answers:

> What shape is this object?

A member generator should create geometry in a predictable canonical coordinate system.

For example:

```text
make_stile(...)
make_rail(...)
make_muntin(...)
make_molding_profile(...)
```

These functions should not need to know where the resulting object will ultimately appear in the building.

### Assembly

Assembly answers:

> How are these objects arranged relative to each other?

For example:

```text
assemble_upper_sash(...)
assemble_lower_sash(...)
assemble_window(...)
```

The sash assembly owns the relationships between rails, stiles, muntins, and glazing.

The window assembly owns the relationships between the frame and its sashes.

### Placement

Placement answers:

> Where does this completed assembly belong in its parent?

For example:

```text
wall.add(window, opening_transform)
```

Changing the location or orientation of the window on the building should change the window-to-wall transform without changing any rail, stile, sash, or frame positioning logic.

## Transform Composition

Transforms will be composed hierarchically.

If:

```text
A = rail → sash
B = sash → window
C = window → wall
D = wall → building
```

then the final rail placement is conceptually:

```text
D × C × B × A
```

Application code should rely on CadQuery or an appropriate abstraction for transform mathematics rather than manually implementing matrix operations where possible.

Translation and rotation are the primary placement operations.

Scaling should generally not be used to dimension manufacturing geometry. A differently sized component should be regenerated from its dimensions so that profiles, joinery, thicknesses, and other physical features remain semantically correct.

## Canonical Coordinate Conventions

Each major assembly type will define a predictable local coordinate system.

For example, a window may use:

```text
+X = left to right
+Y = exterior to interior
+Z = bottom to top
```

The window generator uses this convention regardless of whether the completed window eventually appears on the north, south, east, or west elevation.

Placement on a particular wall is handled by the window-to-wall and wall-to-building transforms.

Origins and pivots must be chosen deliberately and documented for reusable component and assembly types.

## Hierarchy Preservation

The scene graph is the canonical representation of spatial organization.

The generator should not flatten the hierarchy into world-space solids earlier than necessary.

A flattened world-space representation may be produced for:

- rendering;
- GLB generation;
- STEP or other CAD export;
- visualization;
- downstream manufacturing artifacts where required.

These are projections of the hierarchical model rather than the source of truth for assembly relationships.

## Independent Assembly Rendering

Every major assembly should be capable of being generated and rendered independently in its own local coordinate system.

For example:

```text
render member
render upper_sash
render lower_sash
render window
render wall
render building
```

A window must not require knowledge of its eventual building location in order to produce a coherent window.

This provides both a design constraint and a useful testing surface.

## Deterministic Spatial Validation

The scene graph should allow important spatial relationships to be tested before visual review.

Examples include:

- expected assembly bounding dimensions;
- rails spanning between the correct stiles;
- expected member intersections;
- aligned glazing planes;
- valid joinery intersections;
- components contained within expected assembly envelopes;
- expected child transforms;
- absence of unintended intersections;
- consistent origins and coordinate conventions.

Visual review remains valuable, but it should primarily evaluate proportions, appearance, historical fidelity, and design intent rather than repeatedly discovering basic assembly errors.

## Agentic CAD Implications

The agentic coding and visual-review loop will operate within the same hierarchy.

A visual reviewer may identify that a component is incorrectly positioned, but the coding agent should correct the relationship at the level that owns it.

For example:

```text
Incorrect rail-to-stile relationship
        ↓
fix sash assembly

Incorrect sash-to-frame relationship
        ↓
fix window assembly

Incorrect window location
        ↓
fix wall/window placement

Incorrect wall orientation
        ↓
fix building assembly
```

Agents should not correct a child member by introducing an ancestor-space transform that bypasses the hierarchy.

Agent instructions should explicitly preserve this invariant.

Visual review can also become hierarchical:

```text
part correctness
      ↓
assembly correctness
      ↓
window/component review
      ↓
building integration
      ↓
whole-building review
```

This should reduce wasted visual-review cycles and make agent modifications more localized and predictable.

## Relationship to Future CAD IR

This decision does not require immediately replacing the existing procedural generator with a generalized CAD intermediate representation or constraint solver.

The immediate goal is to refactor the existing procedural generator so that spatial responsibility follows the scene hierarchy.

The existing domain vocabulary and procedural geometry may remain.

A future CAD IR may represent scene nodes, assemblies, transforms, joinery, constraints, and semantic relationships explicitly. The scene graph established by this ADR provides a natural foundation for that work without requiring it as part of the initial refactor.

## Consequences



### Positive

Spatial relationships become explicit and localized.

Changing the placement of an assembly automatically moves its descendants as a unit.

Component geometry becomes reusable across different assemblies and building orientations.

Positioning regressions should become easier to diagnose because each relationship has an identifiable owner.

Major assemblies can be independently rendered and tested.

Deterministic spatial tests can catch failures before expensive visual-agent review.

Agent modifications become more constrained: a positioning problem should normally be corrected at one level of the hierarchy.

The architecture aligns with established scene-graph practices from graphics, game engines, robotics, and other hierarchical 3D systems.

The hierarchy also provides a foundation for future CAD IR, reusable component libraries, semantic constraints, and agent-driven assembly.

### Negative

The existing procedural generator will require significant refactoring.

Existing world-space positioning calculations must be identified and moved to their appropriate assembly level.

Coordinate-system and origin conventions must be defined explicitly.

Transform composition introduces concepts that are currently implicit in procedural code and will require discipline in implementation and testing.

Some existing geometry may initially appear incorrect when extracted from building-space assumptions and rendered independently.

## Refactoring Strategy

The refactor should be incremental rather than a complete rewrite.

Start with one representative assembly, preferably a window, because it contains nested assemblies and repeated positioning relationships.

The first target hierarchy should be:

```text
Window
├── Frame
├── Upper Sash
│   ├── Stiles
│   ├── Rails
│   └── Muntins
└── Lower Sash
    ├── Stiles
    ├── Rails
    └── Muntins
```

For this vertical refactor:

1. Define canonical axes and origins.
2. Generate individual members in local coordinates.
3. Assemble each sash entirely in sash-local coordinates.
4. Place each sash into window-local coordinates.
5. Assemble the complete window at the origin.
6. Verify the window independently.
7. Place the completed window into a wall using one parent transform.
8. Place the wall into the building using its parent transform.
9. Add deterministic tests for assembly dimensions and critical spatial relationships.
10. Compare the resulting building against the existing generator and visual references.

Once this pattern is stable, migrate doors, trim, stairs, roof assemblies, and other building components incrementally.

## Acceptance Criteria

This decision is successfully implemented for an assembly when:

- the assembly can render correctly at the origin without building context;
- its child members contain no building-space positioning assumptions;
- moving or rotating the assembly requires changing only its parent transform;
- changing a child dimension preserves unrelated parent and sibling placement;
- world-space placement is derived through transform composition;
- important internal spatial relationships have deterministic tests;
- visual review does not require correcting individual members using building-space offsets.



## Summary

The CAD generator will treat a building as a hierarchy of locally assembled objects rather than a collection of independently positioned world-space solids.

The core rule is:

> **Build locally, assemble hierarchically, place once.**

This addresses a recurring source of positioning regressions in both manual and agentic development and establishes a more stable foundation for procedural CadQuery generation, reusable architectural components, deterministic validation, and future agent-driven CAD workflows.