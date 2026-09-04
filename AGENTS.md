# AGENTS.md

# Wicketgate CAD Agent Instructions

## Purpose

Wicketgate CAD is a deterministic parametric CAD system.

Agents may modify implementation code, tests, fixtures, and supporting tooling, but generated CAD artifacts are part of the validation surface. A task involving geometry is not complete merely because code compiles or automated tests pass.

The normal workflow is:

1. Understand the requested behavior.
2. Inspect the existing implementation before changing it.
3. Make the smallest coherent change.
4. Run relevant local tests.
5. Commit and push the change.
6. Wait for the corresponding GitHub Actions workflow.
7. Inspect the artifacts generated from that exact commit.
8. Visually evaluate the generated geometry.
9. If the result is incorrect, diagnose it and iterate.
10. Open a PR only after the acceptance criteria are satisfied or a design-review boundary has been reached.

Do not stop after modifying code if the task has geometric or visual acceptance criteria.

---

## Architectural Principles

Prefer deterministic implementations.

Use the agent for interpretation, diagnosis, implementation, and iterative refinement. Once behavior is understood, encode it in deterministic code, data, tests, or reusable geometry primitives.

Preserve existing abstractions unless the task demonstrates that they are inadequate.

Prefer:

- extending existing deterministic geometry code
- fixing general geometric rules
- adding reusable helpers
- improving validation
- adding regression fixtures
- preserving stable CLI and artifact contracts

Avoid:

- replacing deterministic behavior with model-generated behavior
- rewriting working subsystems unnecessarily
- solving local defects with fixture-specific hacks
- changing unrelated dimensions or member placement to hide a geometry problem
- bypassing the supported CLI or publication workflow without a clear diagnostic reason

## Scene Graph and Positioning Repairs

The generator is moving toward the ADR-0001 scene graph model:

> Build locally, assemble hierarchically, place once.

For positioning defects, classify the failure before changing code:

- **Local geometry:** the part is the wrong shape or dimensions in its own coordinate system.
- **Child-to-parent assembly:** a part is misplaced relative to the assembly that owns it.
- **Ancestor placement:** a complete assembly is misplaced on its parent.

Repair the smallest owning level. Do not add child-level world-space offsets to
compensate for parent placement bugs, and do not move sibling or ancestor
geometry simply to make one visual defect disappear.

The global building coordinate system is anchored at the `cornerstone`: the
front-left exterior foundation corner at grade is `(0, 0, 0)`. New placement code
should reason from that coordinate system and use compatibility helpers when it
must project into legacy CadQuery coordinates.

---

## Execution Environment

The supported CAD execution and publication path is GitHub Actions.

The normal geometry loop is:

```text
edit
  ↓
local tests
  ↓
commit
  ↓
push
  ↓
GitHub Actions
  ↓
generated artifacts in R2
  ↓
viewer / visual inspection
  ↓
evaluate
  ↓
repeat if necessary