# ADR-0003: Integrate a Joinery Compilation Layer into the Procedural Generator

- **Status:** Proposed
- **Date:** 2026-09-09
- **Scope:** Procedural CAD generator, scene graph, timber-member geometry
- **Language:** Python
- **Geometry engine:** CadQuery

## Context

The current procedural generator creates structural members and positions them relative to
one another, but most members terminate as simple rectangular solids.

Connections are therefore represented visually as:

- members butted against each other;
- members intersecting each other;
- members passing through each other without actual joinery.

This was sufficient for developing the building-level layout and scene graph, but it now
creates several problems:

1. Historical timber-frame assemblies do not visually read correctly without joinery.
2. Raw intersections make it difficult to distinguish placement errors from unfinished geometry.
3. Important parts of the building geometry are created by the joints themselves.
4. Visual review becomes unreliable when the intended structural relationship is not represented.
5. Adding connection-specific Boolean operations directly into building generators would
   recreate the coupling that the scene-graph refactor was intended to eliminate.

A joinery library has now been prototyped manually in CadQuery notebooks.

The notebook work was intentionally interactive. Correct geometry often required repeated
comparison against historical drawings and rendered geometry. This work established a
set of visually validated joinery patterns that can now be treated as deterministic
geometry primitives.

The current joinery vocabulary includes:

- mortise and tenon;
- stub tenon;
- half lap;
- reciprocal mortise-and-tenon plate splice;
- peg bores;
- angled brace tenons and mortises;
- notched bearing;
- rafter ridge half lap;
- false-plate rafter bearing;
- collar half-dovetail lap;
- historical plate-to-girder dovetail;
- housed dovetail joist connection.

The generator is not yet ready for the full architectural IR graph.

The immediate goal is to improve the geometric and visual behavior of the existing
procedural generator while preserving the scene-graph architecture already in place.

---

## Decision

Introduce a **joinery compilation layer** into the existing Python/CadQuery procedural
generator.

Joinery will be represented as explicit relationships between scene members.

A joint:

- references the members participating in the connection;
- contains the parameters needed to construct the joint;
- may generate positive geometry, subtractive geometry, or both;
- modifies member geometry;
- does **not** determine building-level member placement.

The scene graph remains authoritative for placement.

The joinery layer is therefore:

> A deterministic CadQuery geometry compiler operating on relationships between scene
> members.

It is not:

- a replacement for the scene graph;
- the future architectural IR;
- a constraint solver;
- an automatic assembly solver.

The procedural pipeline becomes:

```text
building parameters
        |
        v
procedural layout
        |
        v
scene graph
+----------------------+
| member nodes         |
| local geometry       |
| transforms           |
| hierarchy            |
+----------------------+
        |
        v
joint declarations
        |
        v
JOINERY COMPILER
        |
        v
joined local geometry
        |
        v
scene transforms
        |
        v
GLB / viewer / artifacts
```

---

## Scene Graph Remains Authoritative for Placement

Joinery must not reposition members in order to make a connection work.

For example:

```text
corner_post.transform
top_plate.transform
brace.transform
```

are determined by the procedural layout and scene graph.

The joinery compiler may inspect the relationship between these transforms in order to
construct the correct geometry, but it must not silently modify them.

The separation is:

```text
scene graph = where members are

joinery     = how members physically connect
```

If a joint cannot be generated correctly because two members are incorrectly positioned,
that should eventually be reported as a geometry or validation error.

The joint should not move one member until the geometry happens to fit.

This preserves the local-space scene-graph architecture already established.

---

## Member Representation

A structural member should preserve its original blank geometry separately from its final
joined geometry.

Conceptually:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class MemberNode:
    id: str
    parent_id: str | None

    transform: Any

    blank: Any
    joined: Any | None = None

    metadata: dict[str, Any] = field(default_factory=dict)
```

`blank` represents the deterministic member before joinery.

For example:

```text
6x8 post
4x6 brace
8x8 sill
3x8 ceiling joist
```

`joined` represents the same member after all applicable joinery operations have been
compiled.

The scene transform remains separate from both.

The intended rule is:

> Construct the member in local space, apply joinery in local space, then place the
> completed member through the scene graph.

This prevents world-space transforms from becoming baked into part geometry.

---

## Joint Declarations

The procedural generator should declare connections after the participating members have
been created.

A lightweight representation is sufficient.

For example:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class JointSpec:
    id: str
    joint_type: str

    member_a: str
    member_b: str

    anchor: Any
    params: dict[str, Any] = field(default_factory=dict)
```

An example mortise-and-tenon declaration might conceptually be:

```python
JointSpec(
    id="corner_post_to_plate",
    joint_type="mortise_tenon",
    member_a="corner_post",
    member_b="top_plate",
    params={
        "tenon_width": 3.0,
        "tenon_thickness": 2.0,
        "tenon_length": 2.5,
    },
)
```

A girder dovetail might be:

```python
JointSpec(
    id="girder_to_plate",
    joint_type="dovetail_girder_notch",
    member_a="girder",
    member_b="top_plate",
    params={
        "depth": 3.0,
        "neck_width": 3.0,
        "bottom_width": 4.0,
    },
)
```

These declarations are deliberately lightweight.

They are not the future IR.

They simply provide enough semantic information for the procedural generator to invoke
known deterministic geometry.

---

## Joint-Local Coordinates

Joint implementations should be authored in a canonical joint-local coordinate system.

The joint compiler is responsible for mapping joint geometry into each participating
member's local coordinate system.

Conceptually:

```text
member world transform = Tm
joint world transform  = Tj

joint -> member local transform:

Tlocal = inverse(Tm) * Tj
```

This allows the same joint implementation to be reused across:

- horizontal members;
- vertical members;
- diagonal braces;
- left- and right-handed rafters;
- mirrored assemblies;
- different locations in the building.

The joinery implementation should not contain building-specific world translations.

For example, an angled brace tenon should understand:

```text
brace-local axis
brace section
tenon dimensions
joint shoulder
```

but not:

```text
this brace happens to be at X=144, Y=48, Z=96
```

That placement belongs to the scene graph.

---

## Geometry Operations

A joint does not necessarily correspond to one Boolean operation.

Each joint may generate one or more operations against one or more members.

A minimal representation could be:

```python
@dataclass
class GeometryOperation:
    member_id: str
    operation: str
    shape: Any
```

Where:

```text
operation = "cut"
operation = "fuse"
```

A simple application function could initially be:

```python
def apply_operations(blank, operations):
    shape = blank

    for op in operations:
        if op.operation == "cut":
            shape = shape.cut(op.shape)

        elif op.operation == "fuse":
            shape = shape.fuse(op.shape)

        else:
            raise ValueError(
                f"Unknown geometry operation: {op.operation}"
            )

    return shape.clean()
```

The exact implementation may evolve, but the important architectural point is that the
joint emits geometry operations rather than owning the entire member.

---

## Joint Examples

### Mortise and Tenon

A post-to-plate connection may emit:

```text
post:
    fuse tenon

plate:
    cut mortise
```

### Half Lap

A half-lap connection may emit:

```text
member A:
    cut upper half

member B:
    cut lower half
```

### Notched Bearing

For the Brush-Everard ceiling-joist/top-plate relationship:

```text
ceiling joist:
    cut notch

top plate:
    no modification
```

The top plate acts as the support datum.

### Reciprocal Plate Splice

The plate splice may emit:

```text
plate A:
    cut half lap
    fuse tenon
    cut open mortise
    cut peg bores

plate B:
    cut complementary half lap
    fuse reciprocal tenon
    cut reciprocal open mortise
    cut peg bores
```

This is an important example because a single semantic joint produces several geometric
operations on both members.

### Dovetail Girder Notch

The historical plate-to-girder dovetail may emit:

```text
girder:
    form dovetail tail

plate:
    cut corresponding dovetail notch
```

The production implementation should derive the female geometry from the same canonical
parameters as the male geometry rather than maintaining two unrelated definitions.

---

## Multiple Joints on One Member

A single structural member may participate in many joints.

A top plate may contain:

```text
post mortises
brace mortises
ceiling-joist bearings
plate splice
girder dovetail
```

Therefore the top-plate generator should not own the final Boolean sequence.

Instead:

```text
raw top plate
       |
       +-- post mortise
       |
       +-- brace mortise
       |
       +-- girder dovetail
       |
       +-- plate splice
       |
       v
compiled top plate
```

The joinery compiler should collect the operations that affect a member and produce its
final joined solid.

Conceptually:

```python
operations_by_member = {
    "top_plate_01": [
        post_mortise,
        brace_mortise,
        girder_dovetail,
    ],
}
```

Compilation can initially remain straightforward:

```python
for member_id, member in scene.members.items():
    operations = operations_by_member.get(
        member_id,
        [],
    )

    member.joined = apply_operations(
        member.blank,
        operations,
    )
```

If Boolean ordering later proves significant, operation ordering can become explicit.

It does not need to be solved preemptively.

---

## Component Generators Declare Intent

Procedural component generators should know:

> Which members connect.

They should not contain the detailed CadQuery implementation of:

> How the joint is cut.

For example, a wall generator might currently perform:

```text
create sill
create post
place post at sill endpoint
```

It should evolve toward:

```text
create sill
create post

place post through scene graph

declare:
    mortise_tenon(
        male=post,
        female=sill
    )
```

Similarly, a roof generator might declare:

```text
ridge_half_lap(
    left_rafter,
    right_rafter
)

false_plate_bearing(
    rafter,
    false_plate
)

collar_half_dovetail(
    collar,
    rafter
)
```

The division of responsibility becomes:

```text
component generator
    knows which things connect

joinery library
    knows how that connection is constructed
```

---

## Python Joinery Package

The production geometry should live in a dedicated Python package rather than remain
embedded inside building-specific generators.

An initial structure might be:

```text
cad/
    scene/
        member.py
        transform.py
        scene.py

    joinery/
        base.py
        mortise_tenon.py
        half_lap.py
        plate_splice.py
        notched_bearing.py
        brace_tenon.py
        ridge_half_lap.py
        collar_half_dovetail.py
        dovetail_girder_notch.py
        housed_dovetail.py
        peg_bore.py

    generators/
        frame.py
        wall.py
        floor.py
        roof.py
```

The exact module structure is not important at first.

The important boundary is:

> Joinery geometry must not remain duplicated inside procedural building generators.

---

## Joinery Interface

The first production implementation should remain lightweight.

A base protocol could eventually look like:

```python
class Joint:
    def operations(
        self,
        scene,
    ) -> list[GeometryOperation]:
        raise NotImplementedError
```

For example:

```python
class MortiseTenon(Joint):
    def __init__(
        self,
        male_id,
        female_id,
        width,
        thickness,
        length,
    ):
        self.male_id = male_id
        self.female_id = female_id
        self.width = width
        self.thickness = thickness
        self.length = length

    def operations(self, scene):
        # Resolve member relationship.
        # Generate joint-local geometry.
        # Transform geometry into member-local coordinates.

        return [
            GeometryOperation(
                member_id=self.male_id,
                operation="fuse",
                shape=tenon,
            ),
            GeometryOperation(
                member_id=self.female_id,
                operation="cut",
                shape=mortise,
            ),
        ]
```

However, a class hierarchy is not required immediately.

A simpler functional API is also acceptable:

```python
operations = mortise_tenon(
    male=post,
    female=plate,
    tenon_width=3.0,
    tenon_thickness=2.0,
    tenon_length=2.5,
)
```

The notebook implementations should guide the API rather than forcing every joint into a
premature abstraction.

---

## Compilation Strategy

Joinery should be compiled after procedural placement has been resolved but before final
scene rendering/export.

The sequence is:

```text
1. Generate raw members.

2. Add members to the scene graph.

3. Resolve member transforms and hierarchy.

4. Declare joint relationships.

5. Resolve the joint frame from the participating members.

6. Generate the joint geometry.

7. Transform each joint operation into the affected member's
   local coordinate system.

8. Apply the accumulated cut/fuse operations to the member blank.

9. Store the resulting solid as the member's joined geometry.

10. Render the joined geometry using the existing scene transform.
```

This allows the joint compiler to understand the spatial relationship between members
without abandoning local-space modeling.

---

## No Automatic Assembly Solving

This ADR does not make joints responsible for locating members.

For example:

```text
post tenon
    does NOT pull the post toward the mortise

rafter bearing
    does NOT move the rafter onto the false plate

brace tenon
    does NOT rotate the brace until it fits
```

Those placements remain the responsibility of the current procedural generator and scene
graph.

This is intentional.

Introducing automatic positioning now would effectively introduce:

- constraint solving;
- assembly solving;
- dependency propagation;
- potentially cyclic geometric relationships.

That belongs to a later architecture.

For the current generator:

```text
procedural layout
        |
        v
member placement

joinery compiler
        |
        v
connection geometry
```

This keeps the current work bounded.

---

## Relationship to the Future IR

The joinery library should be implemented so that the eventual architectural IR can
produce the same joint declarations.

Today, procedural Python code may effectively say:

```python
MortiseTenon(
    male="post_01",
    female="plate_01",
    width=3.0,
    thickness=2.0,
    length=2.5,
)
```

A future IR may contain something like:

```json
{
  "kind": "joint",
  "type": "mortise_tenon",
  "members": [
    "post_01",
    "plate_01"
  ],
  "parameters": {
    "width": 3.0,
    "thickness": 2.0,
    "length": 2.5
  }
}
```

Both should ultimately call the same CadQuery joinery implementation.

Therefore:

> The procedural generator is currently the producer of joinery semantics.

Later:

> The architectural IR may become the producer of joinery semantics.

The geometry implementation should not need to change when that migration occurs.

---

## Reference Notebooks

The completed joinery notebook should be retained.

It serves as:

1. a geometric specification;
2. a visual reference;
3. a regression fixture;
4. a record of the manually validated construction logic.

The notebook implementations should not necessarily be copied directly into production.

They are deliberately explicit and exploratory.

Their value is that they establish:

```text
known input parameters
        |
        v
known geometry
        |
        v
visually validated joint
```

Production refactors should preserve that behavior.

---

## Validation

Joint implementations should be tested at more than one level.

### Deterministic Geometry Tests

Useful tests may include:

- expected bounding box;
- expected joint dimensions;
- expected volume;
- expected mating-plane location;
- correct bore position;
- correct clearance;
- expected number of solids;
- absence of invalid geometry.

### Assembly Tests

Known joint pairs should be rendered assembled.

Examples:

```text
post + sill
post + top plate
brace + post
brace + sill
rafter pair
rafter + false plate
collar + rafter
plate splice
girder + plate
```

### Visual Regression Fixtures

The validated notebook examples should be reproduced as small fixture scenes.

These can later be rendered automatically for review.

This is especially important because several of the joinery prototypes demonstrated that
a Boolean operation can be technically valid while producing geometrically incorrect
historical joinery.

---

## Effect on Visual Review

The joinery layer should significantly improve the usefulness of the existing visual
agent loop.

Before joinery integration, a visual reviewer may encounter:

```text
two intersecting members
```

and be unable to distinguish between:

```text
correct placement + missing joint

incorrect placement

incorrect member length

incorrect orientation

incorrect connection type
```

With real joinery present, the model becomes much more legible.

Visual review can then focus on higher-level questions such as:

```text
Is the brace positioned correctly?

Does the rafter actually bear on the false plate?

Is the collar at the correct elevation?

Are the rafters mirrored correctly?

Are projections and overhangs correct?

Does the assembly match the historical reference?
```

The agent should no longer need to rediscover the geometry of a collar half-dovetail,
brace tenon, plate splice, or girder dovetail during normal building generation.

Those become deterministic tools.

---

## Migration Plan

### Phase 1 — Preserve the Notebook Library

Freeze the current working joinery notebook as the reference implementation.

Do not immediately clean it up or replace it.

The notebook represents validated geometry.

### Phase 2 — Create the Joinery Package

Move one joint at a time into the production Python/CadQuery package.

Recommended migration order:

```text
mortise and tenon
half lap
notched bearing
brace tenon
ridge half lap
collar half dovetail
plate splice
girder dovetail
housed dovetail
peg bore
```

Each production implementation should be checked against the notebook fixture before the
next one is migrated.

### Phase 3 — Preserve Blank and Joined Geometry

Extend scene members to support:

```text
blank geometry
joined geometry
```

The renderer should use:

```python
member.joined
```

when available and fall back to:

```python
member.blank
```

otherwise.

This allows incremental adoption.

### Phase 4 — Introduce Joint Declarations

Allow procedural assemblies to declare joints between existing members.

A simple structure is sufficient:

```text
scene.members
scene.joints
```

Do not introduce the full architectural graph.

### Phase 5 — Compile Joinery

Add a joinery compilation pass before scene export.

Conceptually:

```python
scene.build_members()
scene.resolve_transforms()
scene.compile_joinery()
scene.export()
```

The existing scene graph continues to perform placement.

### Phase 6 — Migrate One Complete Structural Assembly

Use one known building assembly as the vertical slice.

A strong candidate is:

```text
sill
  |
  +-- corner post
  |
  +-- angle brace
  |
  +-- top plate
          |
          +-- ceiling joist
                  |
                  +-- false plate
                          |
                          +-- common rafter
                                  |
                                  +-- collar
```

Replace the existing butt/intersection behavior with the validated joinery.

The member transforms should remain unchanged unless an existing placement bug is
discovered independently.

### Phase 7 — Remove Legacy Connection Geometry

As each connection migrates:

- remove duplicate cuts from the building generator;
- remove hacks that extend members solely to hide intersections;
- remove compensating transforms that existed because no real joint was present;
- preserve legitimate placement logic.

At the end of the migration, procedural generators should primarily define:

```text
members
dimensions
placement
relationships
```

while the joinery package defines connection geometry.

---

## Invariants

The implementation should preserve the following invariants:

1. **The scene graph owns placement.**
2. **Joinery does not silently reposition members.**
3. **Members are constructed in local space.**
4. **Joint geometry is applied in member-local space.**
5. **World transforms remain separate from part geometry.**
6. **The raw member blank remains recoverable.**
7. **A member may participate in multiple joints.**
8. **Building generators declare connections rather than implement connection solids.**
9. **The same joinery implementation should be usable by the current procedural generator
   and the future IR.**
10. **The full architectural IR is not required to complete this refactor.**
11. **The validated notebook examples remain the reference behavior during migration.**

---

## Consequences

### Positive

The procedural generator will produce structural assemblies that visually read as actual
timber framing rather than intersecting boxes.

The scene graph becomes easier to debug because joints make intended member relationships
visible.

Historical construction semantics become reusable deterministic code.

The generator gains a stable joinery vocabulary.

Visual agents can focus on assembly-level problems instead of repeatedly rediscovering
joint geometry.

The eventual architectural IR will be able to reuse the same joinery library.

The work completed in the notebooks becomes durable infrastructure rather than remaining
prototype code.

### Negative

The generator gains another compilation stage.

Boolean operations will increase geometry-generation time.

A member with many joints may require several sequential CadQuery operations.

Handed joints and angled members require careful coordinate transforms.

Some existing geometry hacks may need to be removed during migration.

The procedural system will temporarily contain lightweight semantic joint declarations
before the full IR exists.

---

## Accepted Tradeoff

This intermediate architecture is preferable to either alternative:

```text
continue using butt/intersection geometry
```

or:

```text
implement the entire architectural IR and constraint system now
```

The joinery library is durable domain infrastructure.

The procedural generator is simply the first system that will consume it.

---

## Non-Goals

This ADR does not introduce:

- the complete architectural IR;
- a general-purpose graph compiler;
- a constraint solver;
- automatic assembly positioning;
- structural engineering analysis;
- CNC toolpath generation;
- machining strategy;
- historical construction sequencing;
- automatic historical joint selection;
- generative discovery of new joint geometry.

Those systems may consume the joinery layer later.

They are not required to correct the current procedural generator.

---

## Decision Summary

The existing Python procedural generator will continue to determine:

```text
what members exist
```

The scene graph will continue to determine:

```text
where those members are
```

The new Python/CadQuery joinery library will determine:

```text
how those members physically connect
```

The resulting architecture is:

```text
procedural generator
        |
        | creates members and relationships
        v
scene graph
        |
        | owns local/world transforms
        v
joinery compiler
        |
        | applies deterministic CadQuery cuts and fuses
        v
joined member geometry
        |
        v
renderer / GLB / visual review
```

This corrects the current procedural generator without prematurely implementing the full
architectural IR.

The procedural generator remains useful as the current source of building intent, the
scene graph remains the authority for placement, and the joinery library becomes reusable
domain infrastructure that can later be driven by the full IR.