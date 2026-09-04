# CAD Coordinate Systems

This document records the coordinate contract introduced by ADR-0001 and
ADR-0002.

## Global Building Coordinates

The global building coordinate system is anchored at the `cornerstone`.

- `cornerstone`: front-left exterior foundation corner at grade.
- `(0, 0, 0)`: the cornerstone.
- `+X`: left to right across the front elevation.
- `+Y`: front to rear along building depth.
- `+Z`: up from grade.
- Units are inches until export.

New placement code should reason in this coordinate system.

## Legacy CadQuery Coordinates

The existing procedural builders are not migrated all at once. Most current
geometry still uses the historical CadQuery convention where depth frequently
extends in negative `Y`.

Compatibility helpers translate new cornerstone placement semantics into the
legacy CadQuery coordinates while the migration proceeds. The first migrated
slice is windows.

## Window Local Coordinates

Reusable window geometry is built in local coordinates before wall placement.

- Origin: lower-left exterior corner of the window opening.
- `+X`: left to right across the opening.
- `+Y`: exterior to interior through wall depth.
- `+Z`: bottom to top.

The window assembly must not know whether it will be placed on the front, rear,
left, or right wall. Wall placement owns that relationship.

## Transform Ownership

- A part owns its local geometry.
- An assembly owns child-to-parent placement.
- A wall opening owns window-to-wall placement.
- The building owns wall-to-building placement from the cornerstone.

Positioning fixes should be made at the level that owns the failed relationship.
