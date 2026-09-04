# ADR: CAD Inspection and Repair Primitives Inspired by text-to-cad

**Status:** Accepted
**Date:** 2026-09-04

## Implementation Scope

This ADR is accepted as the inspection and repair direction for the generator.
The first implementation slice applies these primitives to windows: canonical
coordinates, semantic scene nodes, lightweight datums, deterministic validation,
and metadata artifacts. Broader viewer and non-window migrations remain follow-on
work.

## Context

The existing procedural CadQuery generator is being repaired before development begins on the more general Wicketgate CAD architecture.

Recent agentic development experiments demonstrated that a coding agent paired with a visual-review agent can successfully identify and repair CAD defects. However, the loop also produced regressions and wasted iterations, particularly around member positioning.

The underlying cause is partly architectural. Components have historically been positioned too independently in building/world coordinates rather than assembled hierarchically in local coordinate systems.

A separate ADR establishes a scene graph and parent-relative transform model to address this problem.

The `earthtojake/text-to-cad` project demonstrates several additional patterns useful for making generated CAD inspectable and repairable by both humans and agents. In particular, it treats CAD generation as more than a render-and-review problem: semantic identity, coordinate conventions, datums, geometric inspection, and deterministic validation provide structured evidence before visual judgment is required.

The procedural generator does not need to adopt the complete `text-to-cad` architecture. The objective of this ADR is to select a small number of high-value concepts that:

* facilitate the scene-graph refactor;
* make positioning defects easier to diagnose;
* reduce regressions;
* improve the agent inspection and repair loop;
* provide useful experience for the future Wicketgate CAD architecture.

## Decision

The procedural generator will adopt five high-priority CAD inspection and repair primitives inspired by `text-to-cad`:

1. **Canonical local coordinate systems and functional origins**
2. **Semantic scene nodes and stable occurrence paths**
3. **Named datums and reference geometry**
4. **Deterministic geometric inspection and validation**
5. **Hierarchical GLB inspection and targeted visual review**

These capabilities will be introduced incrementally while repairing the existing generator.

They are intentionally narrower than a generalized CAD IR, constraint solver, or full `text-to-cad`-style CAD environment.

---

# 1. Canonical Local Coordinate Systems and Functional Origins

Every reusable part and major assembly type will define a documented canonical local coordinate system.

For example:

```text
Window
  origin = lower-left exterior corner
  +X = left → right
  +Y = exterior → interior
  +Z = bottom → top
```

The same principle applies recursively to:

```text
building
wall
window
frame
sash
rail
stile
muntin
```

Origins will be selected deliberately according to useful construction or mating references rather than being accidental consequences of modeling operations.

Geometry should be created in its canonical local coordinate system before placement.

### Rationale

The existing generator contains rotations and translations whose meaning can be difficult to determine because coordinate conventions are implicit.

Explicit coordinate conventions make transforms predictable and allow geometry to be inspected independently of its eventual building placement.

This directly supports the scene-graph invariant:

> **Build locally, assemble hierarchically, place once.**

### Agent benefit

The coding agent can reason about a component in a known coordinate system instead of reverse-engineering arbitrary world-space transforms.

A positioning defect can be classified as either:

* incorrect local geometry;
* incorrect child-to-parent placement; or
* incorrect ancestor placement.

This substantially narrows the repair surface.

---

# 2. Semantic Scene Nodes and Stable Occurrence Paths

Generated geometry will retain semantic identity through the assembly and rendering pipeline.

The system will distinguish the conceptual geometry of an object from an **occurrence** of that object within an assembly.

For example:

```text
building
/west_wall
/window_03
/lower_sash
/meeting_rail
```

Each significant scene node should have, at minimum:

```text
id
name
type
role
parent
semantic path
local transform
```

Where practical, GLB export should preserve this information using glTF node names and metadata.

Repeated components may share geometry while retaining distinct semantic occurrences.

### Rationale

Anonymous solids and meshes make both debugging and automated review unnecessarily difficult.

A semantic path provides a common identifier across:

* source code;
* scene graph;
* GLB;
* viewer;
* validation output;
* screenshots;
* agent findings;
* repair reports.

Instead of reporting:

> The horizontal piece in the second window appears misplaced.

the system should eventually support:

```text
target:
building/west_wall/window_03/lower_sash/meeting_rail
```

### Agent benefit

Agent findings become addressable.

A visual-review agent can identify a scene node, and a coding agent can inspect the same node and its ancestry before modifying source code.

This creates a stable bridge between visual evidence and implementation.

---

# 3. Named Datums and Reference Geometry

Important construction references will be represented explicitly rather than repeatedly reconstructed through coordinate arithmetic.

Examples may include:

```text
window.opening_origin

frame.sill_datum

lower_sash.glazing_plane

left_stile.inside_edge

right_stile.inside_edge

meeting_rail.centerline
```

Initially, a datum may simply resolve to a point, axis, plane, edge location, or coordinate.

The procedural generator does not need a generalized constraint solver to benefit from this abstraction.

For example, instead of repeatedly calculating:

```text
meeting rail Z =
window origin
+ frame offset
+ sash offset
+ ...
```

the sash assembly should be able to work from an authoritative sash-local reference.

### Rationale

Repeated coordinate arithmetic creates hidden coupling.

Named datums make the geometric intention explicit and establish authoritative references that multiple members can share.

They also provide a migration path toward future constraint-based or semantic assembly mechanisms without requiring them now.

### Agent benefit

The agent can repair relationships rather than magic numbers.

A repair should increasingly resemble:

```text
align meeting rail with lower sash meeting datum
```

rather than:

```text
change translate Z from 42.125 to 42.375
```

This should reduce locally successful fixes that create downstream regressions.

---

# 4. Deterministic Geometric Inspection and Validation

Generated geometry will expose machine-readable inspection information before visual review.

At minimum, important scene nodes should support inspection of:

```text
semantic path
parent
local transform
world transform
bounding box
dimensions
```

Important assemblies should also have deterministic spatial invariants.

Examples include:

```text
expected window width and height

expected sash dimensions

rails span between appropriate stiles

expected glazing-plane alignment

members remain within assembly envelope

expected member intersections exist

unexpected intersections do not exist

child transforms remain within plausible ranges
```

Validation should run as part of generation or CI where practical.

### Rationale

The current agent loop relies too heavily on rendered appearance to detect errors that can be identified deterministically.

A member translated several feet outside its sash is fundamentally a geometric validation failure, not a visual-design judgment.

The repair workflow should therefore become:

```text
generate
   ↓
structural validation
   ↓
transform inspection
   ↓
bounding/datum validation
   ↓
render
   ↓
visual review
```

rather than:

```text
generate
   ↓
render
   ↓
LLM discovers geometric problem
   ↓
modify code
   ↺
```

### Agent benefit

Deterministic evidence gives the coding agent a much stronger diagnostic context.

A visual finding can be accompanied by facts such as:

```text
target:
  .../lower_sash/meeting_rail

local transform:
  ...

parent bounds:
  ...

member bounds:
  ...

failed invariant:
  meeting_rail outside expected sash envelope
```

The agent can then repair the responsible relationship instead of inferring the entire problem from pixels.

---

# 5. Hierarchical GLB Inspection and Targeted Visual Review

The existing GLB viewer will evolve from a general renderer into a lightweight CAD inspection surface.

The first viewer enhancements should support:

```text
scene hierarchy
click/tree selection
semantic path display
parent display
local transform
world transform
bounding box
isolate selection
ghost non-selected geometry
fit selection
local origin/axis visualization
standard orthographic views
```

The viewer remains an inspection tool rather than becoming a CAD editor.

The scene graph and generator remain authoritative for geometry and placement.

### Hierarchical Review

Visual review should be possible at multiple levels:

```text
member
   ↓
sash
   ↓
window
   ↓
wall
   ↓
building
```

Major assemblies should be independently renderable and inspectable at their local origin.

This allows the review system to determine whether a defect belongs to:

```text
geometry
assembly
placement
building integration
overall composition
```

### Agent benefit

The visual agent no longer needs to inspect every problem through a whole-building screenshot.

It can receive a deterministic view such as:

```text
target:
building/west_wall/window_03/lower_sash

view:
front

mode:
isolated

show:
bounding box
```

Visual findings can then reference semantic scene paths and be passed directly into the coding-agent repair context.

---

# Agent Repair Loop

Together, these five capabilities change the agent workflow from a primarily visual trial-and-error loop into an evidence-driven repair loop.

## Current Pattern

```text
Generate building
       ↓
Render GLB
       ↓
Visual agent finds defect
       ↓
Coding agent changes positioning
       ↓
Render again
       ↓
Visual agent finds regression
       ↺
```

This allows local positioning changes to oscillate because the agent has limited information about assembly structure.

## Target Pattern

```text
Generate
   ↓
Scene graph
   ↓
Deterministic validation
   ↓
Inspection evidence
   ↓
Targeted render
   ↓
Visual review
   ↓
Structured finding
   ↓
Coding-agent diagnosis
   ↓
Smallest responsible repair
   ↓
Repeat validation
```

A structured finding should eventually resemble:

```text
target:
  building/west_wall/window_03/lower_sash/meeting_rail

review_level:
  sash

finding:
  meeting rail appears vertically misplaced

deterministic_evidence:
  parent: lower_sash
  bounds: ...
  local_transform: ...
  failed_invariants: [...]

recommended_repair_scope:
  lower_sash assembly
```

The coding agent should repair the smallest architectural level responsible for the relationship.

It should not introduce world-space corrections to child geometry to compensate for an incorrect parent or assembly transform.

---

# Priority and Implementation Order

The five decisions are ordered deliberately.

```text
1. Coordinate conventions
          ↓
2. Semantic scene nodes
          ↓
3. Named datums
          ↓
4. Deterministic inspection
          ↓
5. Viewer + agent inspection
```

The viewer should consume information produced by the CAD model rather than becoming a parallel source of spatial semantics.

Likewise, agent tooling should consume the inspection model rather than infer information that can be calculated deterministically.

---

# Explicitly Deferred

This ADR does **not** require adoption of:

* a generalized constraint solver;
* a complete CAD intermediate representation;
* generalized joint solving;
* persistent topology references;
* generalized face/edge selector languages;
* a complete CAD command-line environment;
* natural-language CAD generation;
* STEP-first architecture;
* manufacturing workflow abstractions;
* the complete `text-to-cad` architecture.

These remain candidates for the future Wicketgate CAD project.

The procedural generator is being used to prove the smaller primitives before those abstractions are designed.

---

# Consequences

## Positive

The procedural generator becomes easier to diagnose and repair.

Positioning responsibility becomes visible rather than implicit.

Visual agents spend fewer cycles discovering deterministic geometry failures.

Coding agents receive structured geometric evidence rather than only screenshots.

Regression testing becomes substantially stronger.

The GLB viewer becomes useful as an interactive scene-graph debugger.

Semantic identifiers provide continuity from generator source through rendered artifacts and agent reports.

The work directly informs the eventual Wicketgate CAD architecture without requiring the existing generator to become that system.

## Negative

GLB export must preserve more hierarchy and metadata.

Existing procedural geometry will require semantic labeling.

Some implicit coordinate assumptions will need to be discovered and documented.

Datums and validation introduce additional abstractions into code that currently relies primarily on direct coordinate arithmetic.

Viewer work is required in addition to the CadQuery refactor.

The initial refactor may expose previously hidden inconsistencies in origins, dimensions, and positioning conventions.

---

# Success Criteria

The repair architecture will be considered successful when:

1. A major assembly such as a window can be generated and inspected independently at its local origin.
2. Every significant component has a stable semantic path.
3. Important positioning relationships use shared references or named datums rather than duplicated world-space arithmetic.
4. Common positioning failures are detected deterministically before visual review.
5. The GLB viewer can navigate from a visual defect to the responsible semantic scene node and expose enough transform information to diagnose its placement.
6. Agent findings identify specific scene nodes and review levels.
7. Coding-agent repairs increasingly modify the assembly level responsible for a defect rather than introducing compensating world-space offsets.
8. A repair to one member or assembly does not routinely cause unrelated members to drift out of alignment.

## Summary

The procedural generator will borrow a deliberately small set of concepts from `text-to-cad` to make CAD generation more observable and repairable:

> **Known coordinates, named objects, meaningful references, deterministic evidence, and targeted visual inspection.**

These capabilities complement the scene-graph refactor and provide the missing instrumentation between procedural CadQuery generation and the agentic visual-repair loop.

The objective is not to reproduce `text-to-cad`. It is to use the existing generator as a proving ground for the primitives that appear necessary for a reliable, agent-friendly Wicketgate CAD architecture.
