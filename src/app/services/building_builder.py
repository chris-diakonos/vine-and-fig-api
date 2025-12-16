"""
Main building builder that combines all components.
"""
import cadquery as cq
from typing import Tuple, Dict, Any, Optional
from app.models.structure import Structure, ComponentVisibility
from app.services.foundation_builder import FoundationBuilder
from app.services.floor_builder import FloorBuilder
from app.services.sheathing_builder import SheathingBuilder
from app.services.roof_builder import RoofBuilder
from app.services.openings_builder import OpeningsBuilder
from app.services.framing_builder import FramingBuilder


class BuildingBuilder:
    """Orchestrates the construction of complete building model."""
    
    @staticmethod
    def build(
        structure: Structure, 
        structure_hash: Optional[str] = None,
        component_visibility: Optional[ComponentVisibility] = None
    ) -> Tuple[cq.Assembly, Optional[Dict[str, Any]]]:
        """
        Build a complete building from structure specification.
        
        All components are added to a single assembly to ensure proper alignment
        and enable proper glTF export with component separation.
        
        Args:
            structure: Complete structure specification
            structure_hash: Optional structure hash for BOM tracking
            component_visibility: Optional visibility flags for each component (defaults to all visible)
            
        Returns:
            Tuple of (CadQuery Assembly with complete building geometry, BOM data dictionary)
        """
        # Default to all components visible if not specified
        if component_visibility is None:
            component_visibility = ComponentVisibility()
        
        floorplan = structure.floorplan
        dimensions = floorplan.dimensions
        
        # Create main building assembly
        building_assembly = cq.Assembly()
        
        # Build foundation first
        # Foundation top is at z=0, foundation extends downward
        if component_visibility.foundation:
            foundation = FoundationBuilder.build(
                structure.foundation,
                dimensions
            )
            building_assembly.add(foundation, name="foundation", color=cq.Color(0.7, 0.7, 0.7))  # Gray
        
        # Build framing (returns assembly and BOM data)
        # Framing starts at z=0 (sills sit on foundation top)
        bom_data = None
        if component_visibility.framing and structure_hash:
            try:
                framing_builder = FramingBuilder(structure, structure_hash)
                framing_assembly, bom_data = framing_builder.build()
                
                # Add all framing components to the main assembly
                # Traverse the framing assembly and add each component
                for name, obj_data in framing_assembly.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        # Use the original name from framing assembly or generate one
                        component_name = name if name else f"framing_{len(building_assembly.children)}"
                        building_assembly.add(obj_data.obj, name=component_name, color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                        
            except Exception as e:
                # If framing fails, continue without it but log the error
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Framing construction failed: {e}")
        
        # Build floors
        # Floors sit on top of joists (which sit on sills/girts)
        # Floor positions are calculated based on joist positions
        if component_visibility.floors:
            floor_assembly = FloorBuilder.build(
                structure.flooring,
                dimensions,
                floorplan.stories,
                floorplan.ceiling_heights,
                floorplan.joist_heights
            )
            
            # Add all floor planks to the main assembly as individual components
            # Traverse the floor assembly and add each plank
            for name, obj_data in floor_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    # Use the original name from floor assembly or generate one
                    component_name = name if name else f"floor_{len(building_assembly.children)}"
                    building_assembly.add(obj_data.obj, name=component_name, color=cq.Color(0.8, 0.7, 0.6))  # Light wood
        
        # Build sheathing
        # Sheathing boards positioned on exterior of studs
        if component_visibility.sheathing:
            sheathing = SheathingBuilder.build(
                structure.sheathing,
                dimensions,
                floorplan.stories,
                floorplan.ceiling_heights
            )
            building_assembly.add(sheathing, name="sheathing", color=cq.Color(0.9, 0.85, 0.75))  # Light sheathing
        
        # Build roof
        if component_visibility.roof:
            roof = RoofBuilder.build(
                structure.roof,
                dimensions,
                floorplan.stories,
                floorplan.ceiling_heights
            )
            building_assembly.add(roof, name="roof", color=cq.Color(0.3, 0.3, 0.3))  # Dark roof
        
        # Add windows if specified
        if component_visibility.windows and structure.windows:
            windows = OpeningsBuilder.build_windows(structure.windows, dimensions)
            if windows is not None:
                building_assembly.add(windows, name="windows", color=cq.Color(0.7, 0.9, 1.0))  # Light blue
        
        # Add doors if specified
        if component_visibility.doors and structure.doors:
            doors = OpeningsBuilder.build_doors(structure.doors, dimensions)
            if doors is not None:
                building_assembly.add(doors, name="doors", color=cq.Color(0.5, 0.3, 0.2))  # Brown
        
        return building_assembly, bom_data
