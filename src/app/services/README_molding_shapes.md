# Molding Shapes Library for CadQuery

A comprehensive Python library for creating common architectural molding shapes using the CadQuery library. This library provides configurable functions to generate various classical molding profiles with customizable dimensions, proportions, and styling options.

## Features

- **Ovolo Molding**: Classic convex molding with quarter-circle/ellipse profile
- **Bead Molding**: Small, round molding for decorative purposes
- **Astragal Molding**: Semicircular convex molding for transitions
- **Torus Molding**: Doughnut-shaped molding for prominent architectural elements
- **Cavetto Molding**: Concave molding with quarter-circle/ellipse profile
- **Cyma Recta Molding**: S-shaped molding with convex top and concave bottom
- **Cyma Reversa Molding**: S-shaped molding with concave top and convex bottom
- **Scotia Molding**: Deep concave molding with pronounced shadow effects
- **Fillet Molding**: Small convex molding for transitions and edge softening
- **Composite Profiles**: Pre-defined classical architectural profiles combining multiple molding shapes
- **Custom Composite Builder**: Fluent interface for creating custom composite molding profiles
- **Advanced Features**: Series creation, mirroring, scaling, and historical profile library
- **Configurable Parameters**: Adjustable dimensions, curve sharpness, and proportions
- **Multiple Variants**: Basic, filleted, and series versions for ovolo
- **High Precision**: Configurable curve segments for smooth or detailed profiles
- **Easy Integration**: Works seamlessly with CadQuery and CQ-Editor

## Installation

### Prerequisites

- Python 3.7+
- CadQuery library
- CQ-Editor (optional, for 3D visualization)

### Setup

1. Install CadQuery:
```bash
pip install cadquery
```

2. Download the molding shapes library:
```python
# Place molding_shapes.py in your project directory
```

3. Import the library:
```python
from molding_shapes import (
    MoldingShapes, 
    create_ovolo, create_ovolo_with_fillet, create_ovolo_series,
    create_bead, create_astragal, create_torus, create_cavetto,
    create_cyma_recta, create_cyma_reversa, create_scotia, create_fillet,
    CompositeMolding, ClassicalProfiles, CustomComposite, 
    AdvancedComposite, ProfileLibrary
)
```

## Quick Start

### Basic Ovolo

```python
import cadquery as cq
from molding_shapes import create_ovolo

# Create a simple ovolo molding
ovolo = create_ovolo(
    width=12,      # 12mm wide
    height=6,      # 6mm tall
    length=100,    # 100mm long
    radius_ratio=0.6  # Gentle curve
)

# Display in CQ-Editor
show_object(ovolo)
```

### Advanced Ovolo with Filleted Edges

```python
from molding_shapes import create_ovolo_with_fillet

# Create an ovolo with rounded edges
filleted_ovolo = create_ovolo_with_fillet(
    width=15,
    height=8,
    length=150,
    radius_ratio=0.7,
    fillet_radius=2.0  # 2mm fillet radius
)

show_object(filleted_ovolo)
```

### Series of Ovolos

```python
from molding_shapes import create_ovolo_series

# Create a repeating pattern
ovolo_pattern = create_ovolo_series(
    count=5,        # 5 moldings
    width=8,
    height=4,
    length=200,
    spacing=3,      # 3mm between moldings
    radius_ratio=0.5
)

show_object(ovolo_pattern)
```

### Bead Molding

```python
from molding_shapes import create_bead

# Create a decorative bead
bead = create_bead(
    diameter=10,    # 10mm diameter
    length=150,     # 150mm long
    segments=32     # Smooth curve
)

show_object(bead)
```

### Astragal Molding

```python
from molding_shapes import create_astragal

# Create a semicircular astragal
astragal = create_astragal(
    width=8,        # 8mm wide
    height=8,       # 8mm tall
    length=200,     # 200mm long
    segments=32
)

show_object(astragal)
```

### Torus Molding

```python
from molding_shapes import create_torus

# Create a doughnut-shaped torus
torus = create_torus(
    major_radius=20,    # 20mm major radius
    minor_radius=6,     # 6mm minor radius
    length=100,         # 100mm long
    segments=32
)

show_object(torus)
```

### Cavetto Molding

```python
from molding_shapes import create_cavetto

# Create a concave cavetto
cavetto = create_cavetto(
    width=12,       # 12mm wide
    height=6,       # 6mm tall
    length=150,     # 150mm long
    radius_ratio=0.6
)

show_object(cavetto)
```

### Cyma Recta Molding

```python
from molding_shapes import create_cyma_recta

# Create an S-shaped cyma recta
cyma_recta = create_cyma_recta(
    width=14,           # 14mm wide
    height=8,           # 8mm tall
    length=200,         # 200mm long
    convex_ratio=0.4,   # Convex curve ratio
    concave_ratio=0.4   # Concave curve ratio
)

show_object(cyma_recta)
```

### Cyma Reversa Molding

```python
from molding_shapes import create_cyma_reversa

# Create a reverse S-shaped cyma reversa
cyma_reversa = create_cyma_reversa(
    width=14,           # 14mm wide
    height=8,           # 8mm tall
    length=200,         # 200mm long
    convex_ratio=0.4,   # Convex curve ratio
    concave_ratio=0.4   # Concave curve ratio
)

show_object(cyma_reversa)
```

### Scotia Molding

```python
from molding_shapes import create_scotia

# Create a deep concave scotia
scotia = create_scotia(
    width=14,       # 14mm wide
    height=8,       # 8mm tall
    length=200,     # 200mm long
    depth_ratio=0.7 # Deep concave curve
)

show_object(scotia)
```

### Fillet Molding

```python
from molding_shapes import create_fillet

# Create a small transition fillet
fillet = create_fillet(
    width=5,        # 5mm wide
    height=5,       # 5mm tall
    length=150,     # 150mm long
    radius_ratio=0.8 # Gentle curve
)

show_object(fillet)
```

### Classical Composite Profiles

```python
from molding_shapes import ClassicalProfiles

# Create a Doric order base molding
doric_base = ClassicalProfiles.doric_base(length=200)

# Create an Ionic order base molding
ionic_base = ClassicalProfiles.ionic_base(length=200)

# Create a Corinthian capital
corinthian_capital = ClassicalProfiles.corinthian_capital(length=200)

# Create a traditional crown molding
crown_molding = ClassicalProfiles.crown_molding(length=200)

show_object(doric_base)
```

### Custom Composite Builder

```python
from molding_shapes import CustomComposite

# Create a custom composite profile using fluent interface
custom_profile = CustomComposite() \
    .scotia(width=12, height=6, depth_ratio=0.7) \
    .fillet(width=3, height=3, radius_ratio=0.8) \
    .ovolo(width=10, height=5, radius_ratio=0.6) \
    .cyma_recta(width=14, height=8, convex_ratio=0.5, concave_ratio=0.5) \
    .build(length=200)

show_object(custom_profile)
```

### Historical Profile Library

```python
from molding_shapes import ProfileLibrary

# Create a Georgian period crown molding
georgian_crown = ProfileLibrary.georgian_crown(length=200)

# Create a Victorian period base molding
victorian_base = ProfileLibrary.victorian_base(length=200)

# Create an Art Deco style profile
art_deco = ProfileLibrary.art_deco_profile(length=200)

show_object(georgian_crown)
```

### Advanced Composite Features

```python
from molding_shapes import AdvancedComposite, ClassicalProfiles

# Create a series of crown moldings
crown_series = AdvancedComposite.create_series(
    ClassicalProfiles.crown_molding,
    count=5,
    spacing=10,
    length=150
)

# Create mirrored base moldings
mirrored_base = AdvancedComposite.create_mirrored(
    ClassicalProfiles.base_molding,
    length=150
)

# Scale a profile
original = ClassicalProfiles.corinthian_capital(length=150)
scaled = AdvancedComposite.scale_profile(original, 1.5)

show_object(crown_series)
```

## API Reference

### MoldingShapes Class

The main class containing all molding shape methods.

#### `MoldingShapes.ovolo()`

Creates a basic ovolo molding shape.

**Parameters:**
- `width` (float): The width (projection) of the molding in mm. Default: 10.0
- `height` (float): The height of the molding in mm. Default: 5.0
- `length` (float): The length of the molding in mm. Default: 100.0
- `radius_ratio` (float): Ratio of the curve radius to height (0.0-1.0). Default: 0.6
- `segments` (int): Number of segments for curve approximation. Default: 32
- `centered` (bool): Whether to center the molding at origin. Default: True
- `name` (str, optional): Name for the object

**Returns:** `cq.Workplane` - A CadQuery workplane containing the ovolo molding

#### `MoldingShapes.ovolo_with_fillet()`

Creates an ovolo molding with filleted edges.

**Additional Parameters:**
- `fillet_radius` (float): Radius of the fillet on the edges. Default: 1.0

#### `MoldingShapes.ovolo_series()`

Creates a series of ovolo moldings arranged side by side.

**Additional Parameters:**
- `count` (int): Number of ovolo moldings to create. Default: 3
- `spacing` (float): Spacing between moldings. Default: 2.0

#### `MoldingShapes.bead()`

Creates a bead molding shape.

**Parameters:**
- `diameter` (float): The diameter of the bead in mm. Default: 8.0
- `length` (float): The length of the bead in mm. Default: 100.0
- `segments` (int): Number of segments for the circular profile. Default: 32
- `centered` (bool): Whether to center the bead at origin. Default: True
- `name` (str, optional): Name for the object

**Returns:** `cq.Workplane` - A CadQuery workplane containing the bead molding

#### `MoldingShapes.astragal()`

Creates an astragal molding shape.

**Parameters:**
- `width` (float): The width of the astragal in mm. Default: 6.0
- `height` (float): The height of the astragal in mm. Default: 6.0
- `length` (float): The length of the astragal in mm. Default: 100.0
- `segments` (int): Number of segments for the semicircular profile. Default: 32
- `centered` (bool): Whether to center the astragal at origin. Default: True
- `name` (str, optional): Name for the object

**Returns:** `cq.Workplane` - A CadQuery workplane containing the astragal molding

#### `MoldingShapes.torus()`

Creates a torus molding shape.

**Parameters:**
- `major_radius` (float): The major radius (center to center of tube) in mm. Default: 15.0
- `minor_radius` (float): The minor radius (radius of the tube) in mm. Default: 5.0
- `length` (float): The length of the torus in mm. Default: 100.0
- `segments` (int): Number of segments for the circular profiles. Default: 32
- `centered` (bool): Whether to center the torus at origin. Default: True
- `name` (str, optional): Name for the object

**Returns:** `cq.Workplane` - A CadQuery workplane containing the torus molding

#### `MoldingShapes.cavetto()`

Creates a cavetto molding shape.

**Parameters:**
- `width` (float): The width (projection) of the molding in mm. Default: 10.0
- `height` (float): The height of the molding in mm. Default: 5.0
- `length` (float): The length of the molding in mm. Default: 100.0
- `radius_ratio` (float): Ratio of the curve radius to height (0.0-1.0). Default: 0.6
- `segments` (int): Number of segments for the curve approximation. Default: 32
- `centered` (bool): Whether to center the molding at origin. Default: True
- `name` (str, optional): Name for the object

**Returns:** `cq.Workplane` - A CadQuery workplane containing the cavetto molding

#### `MoldingShapes.cyma_recta()`

Creates a cyma recta molding shape.

**Parameters:**
- `width` (float): The width (projection) of the molding in mm. Default: 12.0
- `height` (float): The height of the molding in mm. Default: 8.0
- `length` (float): The length of the molding in mm. Default: 100.0
- `convex_ratio` (float): Ratio for the convex curve (0.0-1.0). Default: 0.4
- `concave_ratio` (float): Ratio for the concave curve (0.0-1.0). Default: 0.4
- `segments` (int): Number of segments for curve approximation. Default: 32
- `centered` (bool): Whether to center the molding at origin. Default: True
- `name` (str, optional): Name for the object

**Returns:** `cq.Workplane` - A CadQuery workplane containing the cyma recta molding

#### `MoldingShapes.cyma_reversa()`

Creates a cyma reversa molding shape.

**Parameters:**
- `width` (float): The width (projection) of the molding in mm. Default: 12.0
- `height` (float): The height of the molding in mm. Default: 8.0
- `length` (float): The length of the molding in mm. Default: 100.0
- `convex_ratio` (float): Ratio for the convex curve (0.0-1.0). Default: 0.4
- `concave_ratio` (float): Ratio for the concave curve (0.0-1.0). Default: 0.4
- `segments` (int): Number of segments for curve approximation. Default: 32
- `centered` (bool): Whether to center the molding at origin. Default: True
- `name` (str, optional): Name for the object

**Returns:** `cq.Workplane` - A CadQuery workplane containing the cyma reversa molding

#### `MoldingShapes.scotia()`

Creates a scotia molding shape.

**Parameters:**
- `width` (float): The width (projection) of the molding in mm. Default: 12.0
- `height` (float): The height of the molding in mm. Default: 8.0
- `length` (float): The length of the molding in mm. Default: 100.0
- `depth_ratio` (float): Ratio controlling the depth of the concave curve (0.0-1.0). Default: 0.7
- `segments` (int): Number of segments for the curve approximation. Default: 32
- `centered` (bool): Whether to center the molding at origin. Default: True
- `name` (str, optional): Name for the object

**Returns:** `cq.Workplane` - A CadQuery workplane containing the scotia molding

#### `MoldingShapes.fillet()`

Creates a fillet molding shape.

**Parameters:**
- `width` (float): The width (projection) of the molding in mm. Default: 4.0
- `height` (float): The height of the molding in mm. Default: 4.0
- `length` (float): The length of the molding in mm. Default: 100.0
- `radius_ratio` (float): Ratio of the curve radius to height (0.0-1.0). Default: 0.8
- `segments` (int): Number of segments for the curve approximation. Default: 32
- `centered` (bool): Whether to center the molding at origin. Default: True
- `name` (str, optional): Name for the object

**Returns:** `cq.Workplane` - A CadQuery workplane containing the fillet molding

### Convenience Functions

For easier access, the library provides direct functions:

- `create_ovolo()` - Direct access to ovolo creation
- `create_ovolo_with_fillet()` - Direct access to filleted ovolo
- `create_ovolo_series()` - Direct access to ovolo series
- `create_bead()` - Direct access to bead creation
- `create_astragal()` - Direct access to astragal creation
- `create_torus()` - Direct access to torus creation
- `create_cavetto()` - Direct access to cavetto creation
- `create_cyma_recta()` - Direct access to cyma recta creation
- `create_cyma_reversa()` - Direct access to cyma reversa creation
- `create_scotia()` - Direct access to scotia creation
- `create_fillet()` - Direct access to fillet creation

### Composite Molding Classes

#### `CompositeMolding`

The core class for creating composite molding profiles by combining multiple individual molding shapes.

**Methods:**
- `add_element(molding_type, **kwargs)` - Add a molding element to the composite profile
- `build(length)` - Build the complete composite molding
- `get_dimensions()` - Get the total dimensions of the composite molding

#### `ClassicalProfiles`

Pre-defined classical architectural molding profiles.

**Methods:**
- `doric_base(length)` - Create a Doric order base molding profile
- `ionic_base(length)` - Create an Ionic order base molding profile
- `corinthian_capital(length)` - Create a Corinthian capital molding profile
- `crown_molding(length)` - Create a traditional crown molding profile
- `base_molding(length)` - Create a traditional base molding profile
- `doric_capital(length)` - Create a Doric capital molding profile
- `ionic_capital(length)` - Create an Ionic capital molding profile

#### `CustomComposite`

Builder for custom composite molding profiles with fluent interface.

**Methods:**
- `scotia(width, height, depth_ratio, **kwargs)` - Add a scotia element
- `fillet(width, height, radius_ratio, **kwargs)` - Add a fillet element
- `ovolo(width, height, radius_ratio, **kwargs)` - Add an ovolo element
- `cavetto(width, height, radius_ratio, **kwargs)` - Add a cavetto element
- `cyma_recta(width, height, convex_ratio, concave_ratio, **kwargs)` - Add a cyma recta element
- `cyma_reversa(width, height, convex_ratio, concave_ratio, **kwargs)` - Add a cyma reversa element
- `astragal(width, height, **kwargs)` - Add an astragal element
- `torus(major_radius, minor_radius, **kwargs)` - Add a torus element
- `bead(diameter, **kwargs)` - Add a bead element
- `build(length)` - Build the custom composite molding
- `get_dimensions()` - Get the total dimensions of the custom composite

#### `AdvancedComposite`

Advanced composite molding features.

**Methods:**
- `create_series(profile_func, count, spacing, length)` - Create a series of composite moldings
- `create_mirrored(profile_func, length)` - Create a mirrored version of a profile
- `scale_profile(profile, scale_factor)` - Scale an entire composite profile

#### `ProfileLibrary`

Library of historical and regional molding profiles.

**Methods:**
- `georgian_crown(length)` - Georgian period crown molding
- `victorian_base(length)` - Victorian period base molding
- `art_deco_profile(length)` - Art Deco style molding profile
- `modern_minimal(length)` - Modern minimalist molding profile

## Parameter Guide

### Understanding the Parameters

#### Width and Height
- **Width**: The horizontal projection of the molding (how far it extends outward)
- **Height**: The vertical height of the molding (how tall it is)

#### Radius Ratio
The `radius_ratio` parameter controls the curve characteristics:
- **0.0**: Very sharp, almost angular curve
- **0.3**: Sharp, pronounced curve
- **0.6**: Moderate, classic ovolo curve (default)
- **0.8**: Gentle, subtle curve
- **1.0**: Very gentle, almost flat curve

#### Segments
The `segments` parameter controls curve smoothness:
- **16**: Low resolution, faster rendering
- **32**: Good balance (default)
- **64**: High resolution, very smooth curves
- **128**: Maximum smoothness (slower rendering)

#### Fillet Radius
When using filleted versions:
- **0.5**: Small, subtle fillet
- **1.0**: Standard fillet (default)
- **2.0**: Large, prominent fillet

#### Bead Parameters
For bead moldings:
- **diameter**: The diameter of the circular cross-section
- **segments**: Number of segments for the circular profile

#### Astragal Parameters
For astragal moldings:
- **width/height**: Dimensions of the semicircular profile
- **segments**: Number of segments for the semicircular curve

#### Torus Parameters
For torus moldings:
- **major_radius**: Distance from center to center of the tube
- **minor_radius**: Radius of the tube itself
- **segments**: Number of segments for both circular profiles

#### Cyma Parameters
For cyma recta and cyma reversa moldings:
- **convex_ratio**: Controls the convex curve portion (0.0-1.0)
- **concave_ratio**: Controls the concave curve portion (0.0-1.0)
- **segments**: Number of segments for the S-shaped curve

#### Scotia Parameters
For scotia moldings:
- **depth_ratio**: Controls the depth of the concave curve (0.0-1.0)
- **segments**: Number of segments for the deep concave curve

#### Fillet Parameters
For fillet moldings:
- **radius_ratio**: Controls the curve gentleness (0.0-1.0, higher = gentler)
- **segments**: Number of segments for the small convex curve

## Examples

### Example 1: Classic Crown Molding

```python
# Create a traditional crown molding profile
crown_molding = create_ovolo(
    width=25,
    height=15,
    length=3000,  # 3 meters
    radius_ratio=0.7,
    segments=64
)

show_object(crown_molding)
```

### Example 2: Decorative Base Molding

```python
# Create a decorative base molding with filleted edges
base_molding = create_ovolo_with_fillet(
    width=20,
    height=10,
    length=2000,
    radius_ratio=0.6,
    fillet_radius=2.5,
    segments=48
)

show_object(base_molding)
```

### Example 3: Repeating Pattern

```python
# Create a repeating decorative pattern
pattern = create_ovolo_series(
    count=8,
    width=6,
    height=3,
    length=1000,
    radius_ratio=0.5,
    spacing=4,
    segments=32
)

show_object(pattern)
```

### Example 4: Custom Architectural Element

```python
# Create a custom architectural element
architectural_element = create_ovolo(
    width=40,
    height=20,
    length=500,
    radius_ratio=0.8,
    segments=80
)

# Add some positioning
positioned_element = architectural_element.translate((0, 0, 10))

show_object(positioned_element)
```

### Example 5: Decorative Bead Molding

```python
# Create a series of decorative beads
bead_pattern = []
for i in range(5):
    bead = create_bead(
        diameter=8 + i * 2,  # Increasing diameter
        length=200,
        segments=32
    )
    bead = bead.translate((i * 25, 0, 0))
    bead_pattern.append(bead)

# Combine all beads
combined_beads = bead_pattern[0]
for bead in bead_pattern[1:]:
    combined_beads = combined_beads.union(bead)

show_object(combined_beads)
```

### Example 6: Classical Torus Molding

```python
# Create a large decorative torus
decorative_torus = create_torus(
    major_radius=30,
    minor_radius=8,
    length=300,
    segments=64
)

show_object(decorative_torus)
```

### Example 7: Cavetto and Ovolo Combination

```python
# Create a cavetto (concave) and ovolo (convex) combination
cavetto = create_cavetto(
    width=15, height=8, length=200, radius_ratio=0.7
)
ovolo = create_ovolo(
    width=15, height=8, length=200, radius_ratio=0.7
)

# Position them side by side
cavetto = cavetto.translate((0, 0, 0))
ovolo = ovolo.translate((25, 0, 0))

# Combine
combined = cavetto.union(ovolo)
show_object(combined)
```

### Example 8: Cyma Recta and Reversa Comparison

```python
# Create both cyma types for comparison
cyma_recta = create_cyma_recta(
    width=16, height=10, length=150,
    convex_ratio=0.5, concave_ratio=0.5
)
cyma_reversa = create_cyma_reversa(
    width=16, height=10, length=150,
    convex_ratio=0.5, concave_ratio=0.5
)

# Position side by side
cyma_recta = cyma_recta.translate((0, 0, 0))
cyma_reversa = cyma_reversa.translate((25, 0, 0))

# Combine
combined = cyma_recta.union(cyma_reversa)
show_object(combined)
```

### Example 9: Scotia and Cavetto Comparison

```python
# Create a scotia (deep concave) and cavetto (standard concave) comparison
scotia = create_scotia(
    width=12, height=6, length=150, depth_ratio=0.8
)
cavetto = create_cavetto(
    width=12, height=6, length=150, radius_ratio=0.6
)

# Position side by side
scotia = scotia.translate((0, 0, 0))
cavetto = cavetto.translate((20, 0, 0))

# Combine
combined = scotia.union(cavetto)
show_object(combined)
```

### Example 10: Fillet Transition Elements

```python
# Create a series of fillets for edge transitions
fillet_small = create_fillet(width=3, height=3, length=100, radius_ratio=0.8)
fillet_medium = create_fillet(width=5, height=5, length=100, radius_ratio=0.8)
fillet_large = create_fillet(width=8, height=8, length=100, radius_ratio=0.8)

# Position in a row
fillet_small = fillet_small.translate((0, 0, 0))
fillet_medium = fillet_medium.translate((15, 0, 0))
fillet_large = fillet_large.translate((30, 0, 0))

# Combine
combined = fillet_small.union(fillet_medium).union(fillet_large)
show_object(combined)
```

### Example 11: Complete Molding Profile

```python
# Create a complete classical molding profile
# Base scotia (deep concave)
base_scotia = create_scotia(width=10, height=6, length=300, depth_ratio=0.8)

# Fillet transition
fillet = create_fillet(width=4, height=4, length=300, radius_ratio=0.8)
fillet = fillet.translate((0, 0, 6))

# Ovolo above
ovolo = create_ovolo(width=12, height=6, length=300)
ovolo = ovolo.translate((0, 0, 10))

# Cyma recta on top
cyma_recta = create_cyma_recta(width=14, height=8, length=300)
cyma_recta = cyma_recta.translate((0, 0, 16))

# Bead at the top
bead = create_bead(diameter=6, length=300)
bead = bead.translate((0, 0, 24))

# Combine all elements
complete_profile = base_scotia.union(fillet).union(ovolo).union(cyma_recta).union(bead)
show_object(complete_profile)
```

### Example 12: Classical Architectural Orders

```python
# Create a complete Doric order
doric_base = ClassicalProfiles.doric_base(length=300)
doric_capital = ClassicalProfiles.doric_capital(length=300)
doric_capital = doric_capital.translate((0, 0, 30))  # Position above base
complete_doric = doric_base.union(doric_capital)

# Create a complete Ionic order
ionic_base = ClassicalProfiles.ionic_base(length=300)
ionic_capital = ClassicalProfiles.ionic_capital(length=300)
ionic_capital = ionic_capital.translate((0, 0, 35))  # Position above base
complete_ionic = ionic_base.union(ionic_capital)

# Position them side by side
complete_ionic = complete_ionic.translate((50, 0, 0))
complete_orders = complete_doric.union(complete_ionic)

show_object(complete_orders)
```

### Example 13: Custom Composite Profile

```python
# Create a custom composite profile with specific proportions
custom_profile = CustomComposite() \
    .astragal(width=8, height=8) \
    .fillet(width=3, height=3, radius_ratio=0.8) \
    .ovolo(width=12, height=6, radius_ratio=0.7) \
    .cyma_recta(width=14, height=8, convex_ratio=0.5, concave_ratio=0.5) \
    .bead(diameter=6) \
    .cyma_reversa(width=12, height=6, convex_ratio=0.4, concave_ratio=0.4) \
    .fillet(width=3, height=3, radius_ratio=0.8) \
    .astragal(width=8, height=8) \
    .build(length=300)

show_object(custom_profile)
```

### Example 14: Historical Style Comparison

```python
# Create profiles from different historical periods
georgian = ProfileLibrary.georgian_crown(length=200)
victorian = ProfileLibrary.victorian_base(length=200)
art_deco = ProfileLibrary.art_deco_profile(length=200)
modern = ProfileLibrary.modern_minimal(length=200)

# Position them for comparison
victorian = victorian.translate((50, 0, 0))
art_deco = art_deco.translate((100, 0, 0))
modern = modern.translate((150, 0, 0))

historical_comparison = georgian.union(victorian).union(art_deco).union(modern)
show_object(historical_comparison)
```

### Example 15: Advanced Composite Features

```python
# Create a series of crown moldings
crown_series = AdvancedComposite.create_series(
    ClassicalProfiles.crown_molding,
    count=5,
    spacing=15,
    length=200
)

# Create mirrored base moldings
mirrored_base = AdvancedComposite.create_mirrored(
    ClassicalProfiles.base_molding,
    length=200
)

# Scale a Corinthian capital
original_capital = ClassicalProfiles.corinthian_capital(length=200)
scaled_capital = AdvancedComposite.scale_profile(original_capital, 1.5)

# Position them for display
crown_series = crown_series.translate((0, 0, 0))
mirrored_base = mirrored_base.translate((0, 300, 0))
scaled_capital = scaled_capital.translate((0, 600, 0))

advanced_examples = crown_series.union(mirrored_base).union(scaled_capital)
show_object(advanced_examples)
```

## Tips and Best Practices

### Performance Optimization
- Use lower segment counts (16-32) for large-scale models
- Use higher segment counts (64-128) for detailed, close-up views
- Consider the final use case when choosing parameters

### Design Considerations
- **Radius Ratio**: Start with 0.6 for classic proportions, adjust based on design needs
- **Proportions**: Maintain good width-to-height ratios (typically 1.5:1 to 3:1)
- **Fillets**: Use filleted versions for softer, more modern appearances

### Integration with Other CadQuery Objects
```python
# Combine with other CadQuery objects
base = cq.Workplane("XY").box(100, 100, 10)
molding = create_ovolo(width=15, height=8, length=100)

# Position and combine
combined = base.union(molding.translate((0, 0, 10)))
show_object(combined)
```

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure `molding_shapes.py` is in your Python path
2. **CadQuery Not Found**: Install CadQuery with `pip install cadquery`
3. **Poor Curve Quality**: Increase the `segments` parameter
4. **Performance Issues**: Reduce `segments` or use simpler parameters

### Error Messages

- **"Width, height, and length must be positive values"**: Check that all dimension parameters are greater than 0
- **"Radius ratio must be between 0.0 and 1.0"**: Ensure radius_ratio is within the valid range
- **"Segments must be at least 8"**: Use at least 8 segments for reasonable curve approximation

## Future Enhancements

The library is designed to be extensible. Future versions may include:

- **Ogee Molding**: S-shaped molding profile
- **Egg and Dart**: Decorative molding patterns
- **Greek Key**: Geometric pattern moldings
- **Quirk**: Small decorative elements to complement fillets
- **Torus with Fillet**: Torus with rounded edges
- **More Historical Profiles**: Additional period-specific molding profiles
- **Regional Styles**: Regional architectural molding variations
- **3D Pattern Integration**: Integration with 3D pattern libraries

## Contributing

To contribute to this library:

1. Fork the repository
2. Create a feature branch
3. Add your molding shape implementation
4. Include comprehensive documentation
5. Add example usage
6. Submit a pull request

## License

This library is released under the MIT License. See the LICENSE file for details.

## Support

For questions, issues, or feature requests, please open an issue in the project repository.

---

**Happy Molding!** 🏛️