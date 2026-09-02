# Agent Loop Plan for Refactoring the Existing CAD Generator

## Purpose

The immediate goal is **not** to complete the final DSL/IR architecture.

The goal is to take the existing procedural CAD generator that already produces mostly-correct geometry, make it operable by an agent, and automate the iterative loop that previously required continuous human visual inspection.

The first target should be the existing timber-frame generator, especially the incomplete joinery behavior.

The guiding idea is:

> Preserve the working procedural generator, wrap it in a deterministic execution and inspection interface, and let an agent iterate inside the unfinished parts of the implementation.

This creates a usable agentic CAD environment before the IR refactor is complete.

---

## Problem Being Solved

The existing generator already does much of the difficult work:

```text
JSON input
   ↓
procedural generator
   ↓
frame members
   ↓
member placement
   ↓
partial joinery
   ↓
rendered model
```

The implementation stalled in the refinement loop:

```text
edit code
   ↓
generate
   ↓
inspect geometry
   ↓
identify incorrect joinery
   ↓
reason about fix
   ↓
edit again
   ↓
repeat
```

The expensive step was not computation. It was repeated human visual inspection and reasoning.

The agent should replace the human in that inner loop while preserving human review at meaningful checkpoints.

---

# Target Loop

```text
                     source / test case
                            │
                            ▼
                   procedural generator
                            │
                            ▼
                     generated model
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
      deterministic validation      controlled renders
              │                           │
              └─────────────┬─────────────┘
                            ▼
                        agent review
                            │
                      problem found?
                       ↙          ↘
                     yes           no
                      │             │
                modify code       finish
                      │             │
                      └──── repeat ─┘
```

The agent should be able to perform multiple iterations without human intervention.

The human reviews the final result or cases where the agent believes the current abstraction itself is inadequate.

---

# Scope of the First Refactor

The first refactor should introduce four capabilities:

```text
1. deterministic CLI execution
2. stable artifact production
3. standardized visual inspection
4. agent-editable development loop
```

Do not require the new IR for this slice.

The generator implementation behind the CLI can remain procedural.

---

# 1. CLI Wrapper

Expose the existing generator through a simple deterministic command-line interface.

For example:

```bash
wicketgate-frame generate examples/frame-01.json
```

Output:

```text
build/frame-01/
  model.step
  model.glb
  bom.json
  validation.json
  manifest.json
  renders/
```

The exact executable name is not important. The contract is.

The same input should produce the same artifact structure every time.

Useful initial commands might be:

```text
generate
validate
render
inspect
```

For example:

```bash
wicketgate-frame generate frame.json

wicketgate-frame validate build/frame

wicketgate-frame render build/frame

wicketgate-frame inspect build/frame --member post-04
```

Keep the CLI thin. It should invoke existing code rather than becoming another implementation layer.

---

# 2. Stable Artifact Contract

Every run should produce a predictable artifact directory.

Recommended initial structure:

```text
artifacts/
  run.json

  model/
    frame.step
    frame.glb

  data/
    bom.json
    validation.json
    components.json

  renders/
    perspective.png
    front.png
    rear.png
    left.png
    right.png
```

For joinery debugging, support scoped artifacts:

```text
artifacts/
  joints/
    joint-017/
      context.json
      perspective.png
      exploded.png
      section-x.png
      section-y.png
```

The artifact layout should become one of the durable parts of the system even after the IR migration.

---

# 3. Controlled Rendering

The agent should not decide how to inspect the model from scratch on every iteration.

Define standard views.

For a whole timber frame:

```text
perspective
front elevation
rear elevation
left elevation
right elevation
top
```

For a connection:

```text
close perspective
exploded view
section along member A
section along member B
```

The rendering tool should automatically:

* frame the target;
* use consistent camera orientation;
* use neutral materials;
* preserve visible edges;
* optionally hide unrelated components;
* generate images at a known resolution.

The rendering pipeline can initially be simple.

CadQuery remains authoritative. A mesh export may be passed to Blender or another viewer/rendering layer if that produces better visual evidence.

---

# 4. Deterministic Validation

Visual inspection should be paired with machine checks.

The first validators do not need to be sophisticated.

Useful checks include:

```text
solid validity
missing solids
unexpected intersections
member count
zero-volume parts
joint participant count
mortise/tenon overlap
tenon extending beyond mortise
shoulder alignment
duplicate members
```

Output should be machine-readable:

```json
{
  "status": "failed",
  "errors": [
    {
      "code": "TENON_OVERRUN",
      "joint": "joint-017",
      "member": "girt-03",
      "amount": 0.375
    }
  ]
}
```

This lets the agent reason from both geometry and explicit diagnostics.

---

# Agent Task Boundary

The agent should receive a very explicit contract.

For the timber framing task:

```text
Authoritative:
- input frame definition
- existing member layout logic
- existing public generator API

Editable:
- joinery generation
- connection resolution
- related tests
- local helper functions

Do not:
- rewrite the complete framing model
- move structural members merely to hide bad joinery
- replace working abstractions without explaining why
```

The central instruction should be something like:

> Preserve member layout unless evidence shows it is structurally incompatible. Repair joinery and connection geometry so the existing frame produces coherent physical joints.

This prevents the agent from solving local geometry failures by changing unrelated geometry.

---

# Agent Iteration

Each iteration should follow a fixed process.

```text
1. inspect current failure
2. inspect relevant source code
3. make the smallest plausible change
4. execute generator
5. run deterministic validation
6. inspect controlled renders
7. compare result with intended construction
8. repeat if needed
```

The agent should record a concise iteration note:

```yaml
iteration: 4
problem:
  joint: joint-017
  issue: tenon shoulder offset from post face

change:
  file: joinery/tenon.py
  summary: derive shoulder plane from receiving-member face

validation:
  before: failed
  after: passed

visual_review:
  result: acceptable
```

This is not chain-of-thought. It is an engineering audit trail.

---

# Unit of Work

Do not initially ask the agent to repair an entire frame.

Start at the connection level.

Recommended progression:

```text
joint
 ↓
small connection assembly
 ↓
single bent / bay
 ↓
whole frame
```

For example:

### Test 1

```text
post + beam
mortise-and-tenon
```

### Test 2

```text
post + girt + brace
multiple interacting joints
```

### Test 3

```text
single framed bent
```

### Test 4

```text
complete building frame
```

This reduces visual complexity and makes failures easier to attribute.

---

# Explicit Escape Hatch

The agent should distinguish between:

```text
implementation problem
```

and:

```text
abstraction problem
```

If it believes the current API cannot represent the required geometry cleanly, it should stop and surface a proposal rather than silently redesigning the library.

For example:

```text
needs_design_review

Current abstraction:
BraceJoint(member_a, member_b)

Problem:
Required housing belongs to a third receiving surface and cannot be
represented without special casing.

Proposed change:
Introduce explicit receiving_face or ConnectionContext.
```

That is a human architecture decision.

---

# Viewer

The viewer can begin much smaller than the eventual Wicketgate CAD UI.

Initial requirements:

```text
orbit / pan / zoom
whole-model view
component visibility
component selection
fixed camera views
```

Useful next capabilities:

```text
isolate component
isolate joint
explode participants
display dimensions
display validation errors
```

The viewer should consume generated artifacts.

It should not own CAD generation.

---

# Relationship to the Future IR

The procedural generator and IR refactor should proceed independently.

Current:

```text
JSON
 ↓
procedural generator
 ↓
CLI artifacts
```

Future:

```text
DSL
 ↓
semantic IR
 ↓
geometry projection
 ↓
same CLI artifacts
```

The CLI, renderer, validation framework, viewer, and agent loop should survive that transition.

That is an important design constraint.

The implementation behind `generate` can change without changing the outer development loop.

---

# Parallel IR Work

While the agent completes the procedural library, a separate workstream can develop:

```text
schema/config
   ↓
Frame IR
   ├── members
   ├── assemblies
   ├── joints
   └── participant relationships
```

The working procedural implementation then becomes useful reference behavior.

Eventually:

```text
same input
   │
   ├── procedural path
   │       ↓
   │   reference result
   │
   └── IR-backed path
           ↓
       candidate result
```

Parity can be evaluated using:

* component counts;
* component dimensions;
* positions;
* joint types;
* BOM;
* validation results;
* rendered views.

The procedural implementation can then be retired when the IR-backed path has sufficient parity.

---

# First Vertical Slice

I would make the first slice deliberately small.

**Goal:** prove that an agent can complete one unfinished joinery case using the existing generator without requiring a human in every visual iteration.

Build only:

```text
existing generator
      ↓
CLI generate
      ↓
STEP/GLB
      ↓
4–6 fixed renders
      ↓
validation.json
      ↓
agent edits joinery
      ↓
repeat
```

Choose one joint you already know is wrong.

Success criteria:

1. The agent can run the generator itself.
2. The agent can inspect the rendered result.
3. It can correlate the visual failure with relevant implementation code.
4. It can make and test multiple changes autonomously.
5. Deterministic validation passes.
6. Final renders are materially improved.
7. You only need to review the result rather than participate in each iteration.

If that works, then expand to the framing library and molding/profile library.

---

# Directional Principle

The core principle for this refactor is:

> **Build the agent workbench around the deterministic library you already have before rebuilding the library around the future architecture.**

The procedural implementation gives the agent something concrete to work against. The agent loop gives you a way to finally complete the portions that stalled. The resulting working behavior then gives the IR refactor a much stronger target.

That keeps the three concerns separate:

```text
finish geometry
learn how agents interact with CAD
design the durable semantic architecture
```

They can reinforce one another without requiring all three to be solved at the same time.
