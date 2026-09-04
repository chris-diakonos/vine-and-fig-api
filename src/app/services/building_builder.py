"""
Main building builder that combines all components.
"""
import cadquery as cq
from typing import Tuple, Dict, Any, Optional, List
from app.models.structure import Structure, ComponentVisibility
from app.services.foundation_builder import FoundationBuilder
from app.services.floor_builder import FloorBuilder
from app.services.sheathing_builder import SheathingBuilder
from app.services.roof_builder import RoofBuilder
from app.services.windows_builder import WindowsBuilder
from app.services.doors_builder import DoorsBuilder
from app.services.framing_builder import FramingBuilder
from app.services.cornice_builder import CorniceBuilder
from app.services.building_layout import BuildingLayout, calculate_ceiling_heights, calculate_floor_heights
from app.services.config_loader import load_json_config


class BuildingBuilder:
    """Orchestrates the construction of complete building model."""
    
    @staticmethod
    def calculate_ceiling_heights(
        stories: int,
        joist_heights: List[float],
        ceiling_heights: List[float]
    ) -> List[float]:
        """
        Calculate ceiling heights for each story.
        
        Args:
            stories: Number of stories
            joist_heights: List of joist heights for each floor
            ceiling_heights: List of ceiling heights for each story
            
        Returns:
            List of ceiling heights (cumulative z positions)
        """
        defaults = load_json_config("building", "BUILDING_CONFIG_PATH")["defaults"]
        return calculate_ceiling_heights(stories, joist_heights, ceiling_heights, defaults["sill_height"])
    
    @staticmethod
    def calculate_floor_heights(
        stories: int,
        joist_heights: List[float],
        ceiling_heights: List[float]
    ) -> List[float]:
        """
        Calculate floor heights for each story (static method for reuse).
        
        Args:
            stories: Number of stories
            joist_heights: List of joist heights for each floor
            ceiling_heights: List of ceiling heights for each story
            
        Returns:
            List of floor heights
        """
        defaults = load_json_config("building", "BUILDING_CONFIG_PATH")["defaults"]
        return calculate_floor_heights(stories, joist_heights, ceiling_heights, defaults["sill_height"])
    
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
        layout = BuildingLayout.from_structure(structure)
        dimensions = layout.dimensions
        stories = layout.stories
        calculated_ceiling_heights = layout.ceiling_heights
        calculated_floor_heights = layout.floor_heights
        calculated_chair_rail_heights = layout.chair_rail_heights
        calculated_bay_heights = layout.bay_heights
        calculated_bay_widths = layout.bay_widths
        openings = layout.openings

        # Create main building assembly
        building_assembly = cq.Assembly()
        scene_components: List[Dict[str, Any]] = []
        validation_results: List[Dict[str, Any]] = []
        
        # Build foundation first
        # Foundation top is at z=0, foundation extends downward
        if component_visibility.foundation:
            foundation_assembly = FoundationBuilder.build(
                structure.foundation,
                dimensions
            )
            if hasattr(foundation_assembly, "scene_components"):
                scene_components.extend(foundation_assembly.scene_components)
            if hasattr(foundation_assembly, "validation_results"):
                validation_results.append(foundation_assembly.validation_results)
            # Add all foundation components to the main assembly (colors are already set in foundation_builder)
            for name, obj_data in foundation_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    component_name = name if name else f"foundation_{len(building_assembly.children)}"
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.7, 0.7, 0.7))
        
        # Build framing (returns assembly and BOM data)
        # Framing starts at z=0 (sills sit on foundation top)
        bom_data = None
        if component_visibility.framing and structure_hash:
            try:
                framing_builder = FramingBuilder(structure, structure_hash, openings)
                framing_assembly, bom_data = framing_builder.build(
                    calculated_ceiling_heights,
                    calculated_floor_heights
                )
                if hasattr(framing_assembly, "scene_components"):
                    scene_components.extend(framing_assembly.scene_components)
                if hasattr(framing_assembly, "validation_results"):
                    validation_results.append(framing_assembly.validation_results)
                
                # Add all framing components to the main assembly
                # Traverse the framing assembly and add each component (colors are already set in framing_builder)
                for name, obj_data in framing_assembly.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        # Use the original name from framing assembly or generate one
                        component_name = name if name else f"framing_{len(building_assembly.children)}"
                        building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.55, 0.45, 0.33))
                        
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
                stories,
                calculated_floor_heights
            )
            if hasattr(floor_assembly, "scene_components"):
                scene_components.extend(floor_assembly.scene_components)
            if hasattr(floor_assembly, "validation_results"):
                validation_results.append(floor_assembly.validation_results)
            
            # Add all floor planks to the main assembly as individual components
            # Traverse the floor assembly and add each plank (colors are already set in floor_builder)
            for name, obj_data in floor_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    # Use the original name from floor assembly or generate one
                    component_name = name if name else f"floor_{len(building_assembly.children)}"
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.8, 0.7, 0.6))
        
        # Build sheathing
        # Sheathing boards positioned on exterior of studs
        if component_visibility.sheathing:
            sheathing_assembly = SheathingBuilder.build(
                structure.sheathing,
                dimensions,
                stories,
                calculated_floor_heights,
                calculated_chair_rail_heights,
                calculated_bay_heights,
                calculated_bay_widths,
                floorplan,
                openings=openings
            )
            if hasattr(sheathing_assembly, "scene_components"):
                scene_components.extend(sheathing_assembly.scene_components)
            if hasattr(sheathing_assembly, "validation_results"):
                validation_results.append(sheathing_assembly.validation_results)
            
            # Add all sheathing boards to the main assembly as individual components
            # Traverse the sheathing assembly and add each board (colors are already set in sheathing_builder)
            for name, obj_data in sheathing_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    # Use the original name from sheathing assembly or generate one
                    component_name = name if name else f"sheathing_{len(building_assembly.children)}"
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.9, 0.85, 0.75))
            
            # Add gable sheathing for side-gable roofs
            if structure.roof.roof_type == "side-gable":
                gable_sheathing_assembly = SheathingBuilder.build_gable_sheathing(
                    structure.sheathing,
                    dimensions,
                    stories,
                    calculated_floor_heights,
                    structure.roof.roof_pitch,
                    structure.roof.roof_overhang
                )
                if hasattr(gable_sheathing_assembly, "scene_components"):
                    scene_components.extend(gable_sheathing_assembly.scene_components)
                if hasattr(gable_sheathing_assembly, "validation_results"):
                    validation_results.append(gable_sheathing_assembly.validation_results)
                
                # Add all gable sheathing boards to the main assembly
                for name, obj_data in gable_sheathing_assembly.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        component_name = name if name else f"gable_sheathing_{len(building_assembly.children)}"
                        building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.9, 0.85, 0.75))
        
        # Build roof
        if component_visibility.roof:
            roof_assembly = RoofBuilder.build(
                structure.roof,
                dimensions,
                stories,
                calculated_floor_heights
            )
            if hasattr(roof_assembly, "scene_components"):
                scene_components.extend(roof_assembly.scene_components)
            if hasattr(roof_assembly, "validation_results"):
                validation_results.append(roof_assembly.validation_results)
            
            # Add all roof panels to the main assembly as individual components
            # Traverse the roof assembly and add each panel (colors are already set in roof_builder)
            for name, obj_data in roof_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    # Use the original name from roof assembly or generate one
                    component_name = name if name else f"roof_{len(building_assembly.children)}"
                    # Color is already set in roof_builder, preserve it from the assembly
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.3, 0.3, 0.3))
        
        # Add windows if specified
        if component_visibility.windows and structure.windows:
            # Collect door openings to avoid placing windows at door bays
            door_openings = []
            if structure.doors:
                for door in structure.doors:
                    if door.wall and door.position is not None:
                        floor = door.floor if door.floor is not None else 1
                        door_openings.append({
                            'wall': door.wall,
                            'position': door.position,
                            'floor': floor
                        })
            
            windows_assembly = WindowsBuilder.build(
                structure.windows,
                dimensions,
                stories,
                calculated_floor_heights,
                calculated_chair_rail_heights,
                floorplan,
                door_openings=door_openings
            )
            if windows_assembly is not None:
                if hasattr(windows_assembly, "scene_components"):
                    scene_components.extend(windows_assembly.scene_components)
                if hasattr(windows_assembly, "validation_results"):
                    validation_results.append(windows_assembly.validation_results)
                # Add all windows to the main assembly (colors are already set in windows_builder)
                for name, obj_data in windows_assembly.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        component_name = name if name else f"window_{len(building_assembly.children)}"
                        building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.7, 0.9, 1.0))
        
        # Add doors if specified
        if component_visibility.doors and structure.doors:
            doors_assembly = DoorsBuilder.build(structure.doors, dimensions, calculated_floor_heights)
            if doors_assembly is not None:
                if hasattr(doors_assembly, "scene_components"):
                    scene_components.extend(doors_assembly.scene_components)
                if hasattr(doors_assembly, "validation_results"):
                    validation_results.append(doors_assembly.validation_results)
                # Add all doors to the main assembly (colors are already set in doors_builder)
                for name, obj_data in doors_assembly.traverse():
                    if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                        component_name = name if name else f"door_{len(building_assembly.children)}"
                        building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.5, 0.3, 0.2))
        
        # Build cornice at the top of the building
        cornice_assembly = CorniceBuilder.build(dimensions, dimensions.building_height, structure.roof.roof_type)
        if cornice_assembly is not None:
            if hasattr(cornice_assembly, "scene_components"):
                scene_components.extend(cornice_assembly.scene_components)
            if hasattr(cornice_assembly, "validation_results"):
                validation_results.append(cornice_assembly.validation_results)
            # Add all cornice components to the main assembly (colors are already set in cornice_builder)
            for name, obj_data in cornice_assembly.traverse():
                if hasattr(obj_data, 'obj') and obj_data.obj is not None:
                    component_name = name if name else f"cornice_{len(building_assembly.children)}"
                    building_assembly.add(obj_data.obj, name=component_name, color=obj_data.color if hasattr(obj_data, 'color') else cq.Color(0.8, 0.7, 0.6))
        
        building_assembly.scene_components = scene_components
        building_assembly.validation_results = {
            "status": "failed" if any(result.get("status") == "failed" for result in validation_results) else "passed",
            "results": validation_results,
        }

        return building_assembly, bom_data
