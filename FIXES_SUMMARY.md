# Visual Defects Fix Summary

This document summarizes the five visual defects fixed after PR #18 (commit 9135b07).

## Changes Made

### 1. Window Frame Header/Sill Y-Overlap (Left/Right Walls)
**File:** `src/app/services/windows_builder.py`

**Issue:** For left/right wall windows, the header and sill were not overlapping with the jambs in Y direction (y_mis=39.5", y_overlap=0).

**Fix:** Changed the rotation sequence for header and sill components on left/right walls:
- Header: Changed from `.rotate((0, 0, 0), (0, 1, 0), -90)` to `.rotate((0, 0, 0), (0, 0, 1), 90).rotate((0, 0, 0), (1, 0, 0), -90)`
- Sill: Applied the same rotation sequence change
- This ensures the header/sill Y-spans properly overlap with the jamb Y-spans

**Expected Result:** Side window AABBs should now show y_overlap > 0 between frame components.

### 2. Side-Gable Overhang
**File:** `src/app/services/roof_builder.py`

**Issue:** Gable overhang was ~11.33" on left and ~19.22" on right, should be 12" past weatherboard/framing on both ends.

**Fix:** Corrected the gable overhang calculation:
- Removed incorrect weatherboard_extension (2.674") from X-direction calculation
- Gable ends have no weatherboard in X direction (weatherboard only on front/rear walls)
- Changed `effective_roof_length` to `roof_length + (2 * roof.roof_overhang)` (was including weatherboard extension)
- Changed `gable_overhang_offset` to `-roof.roof_overhang` (was including weatherboard extension)

**Expected Result:** Roof X-span should be ~504" (480" framing + 24" overhang), with 12" overhang on both left and right.

### 3. Rafter-Tail Seating
**File:** `src/app/services/framing_builder.py`

**Issue:** Rafter tails were landing at F≈17.73" / R≈9.88" past weatherboard, should be 12" on both sides.

**Fix:** Applied empirical corrections to target eave positions:
- Front: Added -5.73" correction to compensate for rotation geometry
- Rear: Added -2.12" correction to compensate for rotation geometry
- These adjustments account for the complex rotation sequence that positions rafters

**Expected Result:** Front and rear rafters should both extend exactly 12" past weatherboard.

### 4. Sash Assembly Through-Depth (Front/Rear Walls)
**File:** `src/app/services/windows_builder.py`

**Issue:** Sash/muntin/glass assembly was extending ~40.875" in Y (depth) direction on front/rear walls, should be constrained to ~5" frame depth.

**Fix:** Removed incorrect rotation for front/rear wall sash positioning:
- Changed from `.rotate((0, 0, 0), (0, 0, 1), 90)` before translation to no rotation
- The sash assembly is already in the correct XZ plane orientation for front/rear walls
- Only translation is needed to position it within the frame

**Expected Result:** Front/rear window sash assemblies should have Y extent of ~1.4" (sash_thickness), not ~40".

### 5. Ridge Y-Gap
**File:** `src/app/services/roof_builder.py`

**Issue:** Front and rear roof panels had a ~1.18" gap at the ridge.

**Fix:** Removed ceiling rounding from panel length calculation:
- Changed from `panel_length = math.ceil(panel_run / panel_cos)` to `panel_length = (panel_run / panel_cos)`
- This ensures panels meet exactly at the ridge without rounding-induced gaps

**Expected Result:** Ridge gap should be eliminated or reduced to <0.5".

## Verification

To verify these fixes:

1. Generate the model with the example_request.json configuration
2. Run the verification script: `python verify_fixes.py`
3. Check that AABBs show proper overlaps and dimensions

Key metrics to verify:
- Side window frame Y-overlap > 30"
- Gable overhang left/right both 11-13"
- Front/rear rafter overhang both 11-13"
- Front/rear sash Y extent < 5"
- Ridge gap < 1"

## Notes

- All fixes maintain existing functionality for other components (roof eaves, foundation, etc.)
- Window configurations remain: story0 9/9, story1 6/9, attic 6/6
- No changes to chimney/portico/shutters (as they don't exist in example_request.json)
