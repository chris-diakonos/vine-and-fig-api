"""
Framing builder service using CadQuery.
Integrates framing.py functionality into the API architecture.
"""
import cadquery as cq
import math
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict

from app.models.structure import Structure
from app.models.floorplan import Dimensions
from app.utils.materials_helper import (
    add_framing_materials,
    add_production_bom_quantities,
    add_sales_bom_quantities
)
from app.services.config_loader import load_json_config
from app.services.framing_validation import validate_framing_scene
from app.services.scene_graph import collect_component_metadata, project_scene_to_assembly, scene_from_assembly


class FramingBuilder:
    """Builds framing geometry and tracks BOM data."""
    
    def __init__(self, structure: Structure, structure_hash: str, openings: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize framing builder.
        
        Args:
            structure: Building structure specification
            structure_hash: Structure hash identifier for BOM tracking
            openings: Optional list of door/window openings {wall, position, floor, type, height}
        """
        self.structure = structure
        self.structure_hash = structure_hash
        self.floorplan = structure.floorplan
        self.dimensions = structure.floorplan.dimensions
        self.building_height = structure.floorplan.dimensions.building_height
        self.roof = structure.roof
        self.openings = openings or []
        
        # Extract dimensions
        self.faces = {
            "front": self.dimensions.front,
            "rear": self.dimensions.rear,
            "left": self.dimensions.left,
            "right": self.dimensions.right
        }
        
        # Calculate centerlines from bays
        self.centerlines = self._calculate_centerlines()
        
        # Configuration
        framing_defaults = load_json_config("framing", "FRAMING_CONFIG_PATH")["defaults"]
        self.bay_spacing = framing_defaults["bay_spacing"]
        self.lap = framing_defaults["lap"]
        self.chair_rail_height = framing_defaults["chair_rail_height"]
        self.max_member_length = framing_defaults["max_member_length"]
        self.joist_spacing = self.floorplan.spacing.joist_spacing
        self.stud_spacing = self.floorplan.spacing.stud_spacing
        self.rafter_spacing = self.floorplan.spacing.rafter_spacing
        self.ceiling_heights = self.floorplan.ceiling_heights or [120, 108]
        self.joist_heights = self.floorplan.joist_heights or [10, 9, 8]
        self.roof_overhang = self.roof.roof_overhang if self.roof else framing_defaults["roof_overhang"]
        self.roof_pitch_degrees = self.roof.roof_pitch if self.roof else 40
        
        # Calculated heights (set by build method)
        self.calculated_ceiling_heights: Optional[List[float]] = None
        self.calculated_floor_heights: Optional[List[float]] = None
        
        # BOM tracking
        self.materials = []
        self.bom_components = defaultdict(set)
        self.bom_quantities = defaultdict(float)
        self.bom_levels = defaultdict(int)
        
        # Tracking for stud placement
        self.bay_studs = {}
        self.stud_centerlines = {}
    
    def _calculate_centerlines(self) -> Dict[str, List[float]]:
        """
        Calculate centerlines from bay configurations.
        
        Returns:
            Dictionary mapping face names to centerline positions
        """
        centerlines = {
            "front": [],
            "rear": [],
            "left": [],
            "right": []
        }
        
        if self.floorplan.bays:
            # Convert bay widths to centerline positions
            for face in ["front", "rear", "left", "right"]:
                bay_widths = getattr(self.floorplan.bays, face, [])
                if bay_widths:
                    for width in bay_widths:
                        centerlines[face].append(width)
                else:
                    # Default centerlines if not specified
                    if face in ["front", "rear"]:
                        centerlines[face] = [64, 160, 240, 330, 420]
                    else:
                        centerlines[face] = [64, 192]
        else:
            # Default centerlines
            centerlines["front"] = [64, 160, 240, 330, 420]
            centerlines["rear"] = [64, 160, 240, 330, 420]
            centerlines["right"] = [64, 192]
            centerlines["left"] = [64, 192]
        
        return centerlines


    def build(
        self,
        calculated_ceiling_heights: List[float],
        calculated_floor_heights: List[float]
    ) -> Tuple[cq.Assembly, Dict[str, Any]]:
        """
        Build complete framing structure.
        
        Args:
            calculated_ceiling_heights: Pre-calculated ceiling heights for each story
            calculated_floor_heights: Pre-calculated floor heights for each story
            
        Returns:
            Tuple of (CadQuery Assembly, BOM data dictionary)
        """
        # Store calculated heights for use in internal methods
        self.calculated_ceiling_heights = calculated_ceiling_heights
        self.calculated_floor_heights = calculated_floor_heights
        
        assembly = cq.Assembly()
        
        # Calculate offset to center framing on foundation
        # Foundation is centered at (0, 0) with overhang
        # Framing starts at front-left corner (0, 0)
        # Need to shift framing so its center aligns with foundation center (0, 0)
        front_dimension = self.faces["front"]
        right_dimension = self.faces["right"]
        
        # Building center in framing coordinate system:
        # X center: front_dimension / 2
        # Y center: -right_dimension / 2
        # Shift to move center to (0, 0):
        x_offset = 0 #-front_dimension / 2
        y_offset = 0 #right_dimension / 2
        
        # Build framing components in order
        self._add_sills(assembly, x_offset, y_offset)
        self._add_posts(assembly, x_offset, y_offset)
        
        # Build per story
        for story in range(1, self.floorplan.stories + 2):

            self._add_joists(assembly, story, -y_offset, x_offset)

            if story in range(1, self.floorplan.stories + 1):
                self._add_braces(assembly, story, x_offset, y_offset)
                self._add_bays(assembly, story, x_offset, y_offset)
                self._add_studs(assembly, story, x_offset, y_offset)

            if story not in (1, self.floorplan.stories + 1):
                self._add_girts(assembly, story, x_offset, y_offset)

            if story == self.floorplan.stories:
                self._add_plates(assembly, story, x_offset, y_offset)
        
        # Add roof components
        self._add_false_plates(assembly, x_offset, y_offset)
        self._add_rafters(assembly, x_offset, y_offset)
        
        # Add gable end framing (for side-gable roofs)
        if self.roof and self.roof.roof_type == "side-gable":
            self._add_gable_framing(assembly, x_offset, y_offset)
        
        # Prepare BOM data
        bom_data = {
            "materials": self.materials,
            "bom_components": self.bom_components,
            "bom_quantities": self.bom_quantities,
            "bom_levels": self.bom_levels
        }
        
        return self._with_scene(assembly), bom_data

    def _with_scene(self, assembly: cq.Assembly) -> cq.Assembly:
        scene_root = scene_from_assembly(
            assembly,
            subsystem_name="framing",
            subsystem_type="framing",
            subsystem_role="framing",
            group_name_for_component=self._group_name_for_component,
            role_for_component=lambda name: name.split("_")[0] if name else "framing_member",
        )
        projected = cq.Assembly()
        project_scene_to_assembly(scene_root, projected)
        projected.scene_root = scene_root
        projected.scene_components = collect_component_metadata(scene_root)
        projected.validation_results = validate_framing_scene(scene_root)
        return projected

    @staticmethod
    def _group_name_for_component(component_name: str) -> str:
        parts = component_name.split("_")
        if not parts:
            return "members"
        if parts[0] == "cripple" and len(parts) > 1:
            return "cripple_studs"
        return f"{parts[0]}s"
    
    def _add_sills(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add sills to the assembly."""
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        
        member_type = "sill"
        sill_height = 8
        sill_depth = 10
        # Sill bottom should sit on foundation top (z=0)
        # Since box is centered, raise by half depth so bottom is at z=0
        sill_z_offset = sill_depth / 2
        total_quantity = 0
        
        for face in self.faces:
            dimension = self.faces[face]

            if dimension <= self.max_member_length:
                quantity = 1
                sill_length = dimension
            elif dimension >= self.max_member_length:
                quantity = math.ceil(dimension / self.max_member_length)
                sill_length = dimension / quantity
            else:
                quantity = 1
                sill_length = self.max_member_length
            
            for q in range(quantity):
                sill_counter = q + 1
                
                if face == "front":
                    new_x = (sill_length * sill_counter) - (sill_length/2) + x_offset
                    new_y = 0 + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(sill_length, sill_height, sill_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (sill_length * sill_counter) - (sill_length/2) + x_offset
                    new_y = -right_dimension + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(sill_length, sill_height, sill_depth).translate((new_x, new_y, new_z))
                elif face == "left":
                    # Left sills run along Y axis (front to rear)
                    # X position: fixed at left wall (x=0)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = (sill_length * sill_counter) - (sill_length/2) + x_offset
                    new_y = 0 + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(sill_length, sill_height, sill_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1),(0,0,0), 90)
                elif face == "right":
                    # Right sills run along Y axis (front to rear)
                    # X position: fixed at right wall (x=front_dimension)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = (sill_length * sill_counter) - (sill_length/2) + x_offset
                    new_y = front_dimension + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(sill_length, sill_height, sill_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1),(0,0,0), 90)
                
                # Add sill with descriptive name including member_type and face
                assembly.add(sill, name=f"{member_type}_{face}_{sill_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                total_quantity += 1
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, sill_depth / 12, sill_height, sill_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_posts(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add corner posts to the assembly."""
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]

        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        stories = self.floorplan.stories

        
        post_width = 6
        post_depth = 4
        post_height = ceiling_heights[stories - 1] - floor_heights[0]
        quantity = 4
        member_type = "post"
        post_tenon_depth = 2

        left_x = 0 + x_offset
        right_x = front_dimension + x_offset
        front_y = 0 + y_offset
        rear_y = -right_dimension + y_offset
        new_z = floor_heights[0] - post_tenon_depth + (post_height / 2)
        
        front_left_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((left_x, front_y, new_z))
        rear_left_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((left_x, rear_y, new_z))
        front_right_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((right_x, front_y, new_z))
        rear_right_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((right_x, rear_y, new_z))
        
        # Add posts with descriptive names
        assembly.add(front_left_post, name=f"{member_type}_front_left", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        assembly.add(rear_left_post, name=f"{member_type}_rear_left", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        assembly.add(front_right_post, name=f"{member_type}_front_right", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        assembly.add(rear_right_post, name=f"{member_type}_rear_right", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, post_width / 12, post_depth, post_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_joists(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add joists for a story."""
        joist_width = 3
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        member_type = "joist"
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        joist_spacing = self.joist_spacing
        
        # Set the joist z position based on the story and floor height
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        joist_z = floor_height - (joist_height / 2)
   
        # Set the joist length based on the story and roof overhang
        if story == len(self.joist_heights):
            joist_length = (self.roof_overhang * 2) + right_dimension
        else:
            joist_length = right_dimension
        
        # Set the quantity of joists based on the front dimension and joist spacing
        quantity = math.ceil(front_dimension / joist_spacing)
        
        for q in range(quantity):
            # X position: fixed at depth center (matches original, but seems wrong)
            new_x = x_offset + (right_dimension/2)
            # Y position: spaced - this becomes X spacing after rotation!
            new_y = (q * joist_spacing) + joist_spacing + y_offset
            new_z = joist_z
            joist = cq.Workplane('XY').box(joist_length, joist_width, joist_height).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
            # Add joist with descriptive name including member_type, story, and position
            assembly.add(joist, name=f"{member_type}_story{story}_{q+1}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, joist_length / 12, joist_width, joist_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_braces(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add braces for a story."""
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        right_offset = right_dimension / 2
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        brace_width = 6
        brace_depth = 4
        member_type = "brace"
        total_quantity = 0
        
        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        ceiling_height = ceiling_heights[story - 1]
        next_floor_height = floor_heights[story]
        face_brace_length = (ceiling_height - floor_height)
        side_brace_length = (next_floor_height - floor_height) - 6
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        for face in self.faces:
            brace_centerline = self.centerlines[face][0] if self.centerlines[face] else 64
            index = len(self.centerlines[face]) - 1 if self.centerlines[face] else 0
            dimension = self.faces[face]
            alt_brace_centerline = dimension - (self.centerlines[face][index] if self.centerlines[face] else dimension - 64)
            
            total_quantity += 2
            
            # Calculate brace positions and angles (simplified - full implementation would match original logic)
            if face == "left":
                brace_height = math.ceil(side_brace_length * (2/3))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = 180 - math.degrees(math.atan(brace_centerline / brace_height))
                new_x = brace_centerline / 2 + x_offset
                new_y = 0 + y_offset
                new_z = (brace_height / 2) + floor_height
                
                alt_brace_height = math.ceil(face_brace_length * (2/3))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = 0 + x_offset
                alt_y = -(alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + floor_height
            elif face == "rear":
                brace_height = math.ceil(side_brace_length * (5/8))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = 180 - math.degrees(math.atan(brace_centerline / brace_height))
                new_x = brace_centerline / 2 + x_offset
                new_y = -right_dimension + y_offset
                new_z = (brace_height / 2) + floor_height
                
                alt_brace_height = math.ceil(face_brace_length * (5/8))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = 180 - math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = 0 + x_offset
                alt_y = -right_dimension + (alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + floor_height
            elif face == "right":
                brace_height = math.ceil(side_brace_length * (2/3))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = math.degrees(math.atan(brace_centerline / brace_height))
                new_x = front_dimension - (brace_centerline / 2) + x_offset
                new_y = 0 + y_offset
                new_z = (brace_height / 2) + floor_height
                
                alt_brace_height = math.ceil(face_brace_length * (2/3))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = front_dimension + x_offset
                alt_y = -(alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + floor_height
            elif face == "front":  # front
                brace_height = math.ceil(side_brace_length * (5/8))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = math.degrees(math.atan(brace_centerline / brace_height))
                new_x = front_dimension - (brace_centerline / 2) + x_offset
                new_y = -right_dimension + y_offset
                new_z = (brace_height / 2) + floor_height
                
                alt_brace_height = math.ceil(face_brace_length * (5/8))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = 180 - math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = front_dimension + x_offset
                alt_y = -right_dimension + (alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + floor_height
            
            # Add braces to assembly with descriptive names
            brace = cq.Workplane('XY').box(brace_width, brace_depth, brace_length).translate((new_x, new_y, new_z)).rotateAboutCenter((0, 1, 0), brace_angle)
            alt_brace = cq.Workplane('XY').box(brace_width, brace_depth, alt_brace_length).translate((alt_x, alt_y, alt_z)).rotateAboutCenter((0, 1, 0), alt_brace_angle).rotateAboutCenter((0, 0, 1), 90)
            assembly.add(brace, name=f"{member_type}_{face}_story{story}_primary", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
            assembly.add(alt_brace, name=f"{member_type}_{face}_story{story}_alt", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, brace_length / 12, brace_width, brace_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_bays(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add bay studs for a story."""
        front_dimension = self.faces["front"]
        right_dimension = self.faces["right"]
        bay_stud_width = 5
        bay_stud_height = 4
        cripple_stud_width = 3
        cripple_stud_height = 4
        cripple_stud_length = self.chair_rail_height
        member_type = "bay_stud"
        total_quantity = 0
        cripple_quantity = 0
        stud_tenon_depth = 2
        
        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        ceiling_height = ceiling_heights[story - 1]
        next_floor_height = floor_heights[story]
        face_stud_length = (ceiling_height - floor_height) + (2*stud_tenon_depth)
        side_stud_length = (next_floor_height - floor_height) + (2*stud_tenon_depth) - 6
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        
        for face in self.faces:
            centerline = self.centerlines[face]
            if not centerline:
                continue
                
            self.bay_studs[face] = []
            total_quantity += 2 * len(centerline)

            if story == 1:
                new_z = floor_height - stud_tenon_depth
            else:
                new_z = floor_height - (joist_height + stud_tenon_depth)
            
            # Set base positions for each face
            if face == "front":
                new_x = 0 + x_offset
                new_y = 0 + y_offset
                stud_length = face_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "rear":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset 
                stud_length = face_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "left":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                stud_length = side_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "right":
                new_x = front_dimension + x_offset
                new_y = -right_dimension + y_offset
                stud_length = side_stud_length
                new_z = new_z + (stud_length / 2)
            # Create bay studs for each centerline
            for i, c in enumerate(centerline):
                bay = i + 1
                
                # Check if this bay has a door or window opening on this floor
                has_opening = False
                for opening in self.openings:
                    if (opening.get('wall') == face and 
                        opening.get('position') == c and 
                        opening.get('floor') == story):
                        has_opening = True
                        break
                
                # Determine if cripple stud is needed
                # Cripple studs support window sills, so skip them for door openings (which sit on floor)
                if has_opening:
                    # Check if it's a door (no cripple stud needed)
                    is_door = any(opening.get('wall') == face and 
                                 opening.get('position') == c and 
                                 opening.get('floor') == story and
                                 opening.get('type') == 'door' 
                                 for opening in self.openings)
                    cripple_flag = not is_door  # Windows get cripple studs, doors don't
                elif face in ["left", "right"] and bay in [1, 2]:
                    cripple_flag = True
                elif face in ["rear", "front"]:
                    cripple_flag = True
                else:
                    cripple_flag = False
                
                if face in ["left", "right"]:
                    # Left/right faces: studs positioned along Y axis
                    left_stud_y_position = new_y + c - ((self.bay_spacing + bay_stud_width) / 2)
                    right_stud_y_position = new_y + c + ((self.bay_spacing + bay_stud_width) / 2)
                    left_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, stud_length).translate((new_x, left_stud_y_position, new_z))
                    right_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, stud_length).translate((new_x, right_stud_y_position, new_z))
                    self.bay_studs[face].append(left_stud_y_position)
                    self.bay_studs[face].append(right_stud_y_position)
                    
                    if cripple_flag:
                        cripple_stud_y_position = left_stud_y_position + (-(left_stud_y_position - right_stud_y_position) / 2)
                        cripple_stud_z_position = floor_height + (cripple_stud_length / 2)
                        cripple_stud = cq.Workplane('XY').box(cripple_stud_height, cripple_stud_width, cripple_stud_length).translate((new_x, cripple_stud_y_position, cripple_stud_z_position))
                        self.bay_studs[face].append(cripple_stud_y_position)
                        assembly.add(cripple_stud, name=f"cripple_stud_{face}_story{story}_bay{bay}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                        cripple_quantity += 1
                
                elif face in ["front", "rear"]:
                    # Front/rear faces: studs positioned along X axis
                    left_stud_x_position = new_x + c - ((self.bay_spacing + bay_stud_width) / 2)
                    right_stud_x_position = new_x + c + ((self.bay_spacing + bay_stud_width) / 2)
                    left_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, stud_length).translate((left_stud_x_position, new_y, new_z))
                    right_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, stud_length).translate((right_stud_x_position, new_y, new_z))
                    self.bay_studs[face].append(left_stud_x_position)
                    self.bay_studs[face].append(right_stud_x_position)
                    
                    if cripple_flag:
                        cripple_stud_x_position = left_stud_x_position + ((right_stud_x_position - left_stud_x_position) / 2)
                        cripple_stud_z_position = floor_height + (cripple_stud_length / 2)
                        cripple_stud = cq.Workplane('XY').box(cripple_stud_width, cripple_stud_height, cripple_stud_length).translate((cripple_stud_x_position, new_y, cripple_stud_z_position))
                        self.bay_studs[face].append(cripple_stud_x_position)
                        assembly.add(cripple_stud, name=f"cripple_stud_{face}_story{story}_bay{bay}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                        cripple_quantity += 1
                
                # Add bay studs with descriptive names
                assembly.add(left_stud, name=f"{member_type}_{face}_story{story}_bay{bay}_left", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                assembly.add(right_stud, name=f"{member_type}_{face}_story{story}_bay{bay}_right", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, stud_length / 12, bay_stud_width, bay_stud_height, self.materials
        )
        raw_material_id_cripple, component_id_cripple = add_framing_materials(
            "cripple_stud", cripple_stud_length / 12, cripple_stud_width, cripple_stud_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_production_bom_quantities(
            component_id_cripple, raw_material_id_cripple, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id_cripple, self.structure_hash, cripple_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_studs(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add wall studs for a story."""
        front_dimension = self.faces["front"]
        right_dimension = self.faces["right"]
        bay_stud_width = 5
        stud_width = 3
        stud_height = 4
        member_type = "stud"
        total_quantity = 0
        stud_tenon_depth = 2
        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        ceiling_height = ceiling_heights[story - 1]
        next_floor_height = floor_heights[story]
        face_stud_length = (ceiling_height - floor_height) + (2*stud_tenon_depth)
        side_stud_length = (next_floor_height - floor_height) + (2*stud_tenon_depth) - 6
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        for face in self.faces:
            self.stud_centerlines[face] = []
            stud_positions = self.bay_studs.get(face, []).copy()
            stud_quantity = 0
            
            if story == 1:
                new_z = floor_height - stud_tenon_depth
            else:
                new_z = floor_height - (joist_height + stud_tenon_depth)
            
            # Set base positions for each face
            if face == "front":
                new_x = 0 + x_offset
                new_y = 0 + y_offset
                last_position = front_dimension - 6
                stud_length = face_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "rear":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                last_position = front_dimension - 6
                stud_length = face_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "left":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                last_position = -right_dimension - 4
                stud_length = side_stud_length
                new_z = new_z + (stud_length / 2)
            elif face == "right":
                new_x = front_dimension + x_offset
                new_y = -right_dimension + y_offset
                last_position = -right_dimension - 4
                stud_length = side_stud_length
                new_z = new_z + (stud_length / 2)
            # Add the last position for the post
            stud_positions.append(last_position)
            
            # Sort the array of stud positions
            stud_positions.sort()
            
            # Find the max index
            max_index = len(stud_positions) - 1
            
            # Loop through the positions and find how many studs go in each section
            for index, position in enumerate(stud_positions):
                wall_quantity = 0
                
                # Calculate prior and current positions
                if index == 0 and face in ["left", "right"]:
                    prior_position = -right_dimension + 4
                    current_position = position - (bay_stud_width / 2)
                elif index == 0 and face in ["front", "rear"]:
                    prior_position = 6
                    current_position = position - (bay_stud_width / 2)
                else:
                    prior_position = stud_positions[index - 1] + (bay_stud_width / 2)
                    current_position = position - (bay_stud_width / 2)
                
                # Calculate wall length
                if face in ["left", "right"]:
                    wall_length = abs(prior_position - current_position)
                elif face in ["front", "rear"]:
                    wall_length = current_position - prior_position
                
                # Determine the stud spacing using complex algorithm
                if wall_length / 4 >= 13:
                    wall_quantity = 3
                elif wall_length / 3 >= 13:
                    wall_quantity = 2
                elif wall_length / 2 > 16:
                    wall_quantity = 1
                elif wall_length / 2 <= 16 and index == max_index:
                    wall_quantity = 1
                elif wall_length % (2 * self.stud_spacing) >= 22:
                    wall_quantity = math.ceil(wall_length / (2 * self.stud_spacing))
                else:
                    wall_quantity = math.floor(wall_length / (2 * self.stud_spacing))
                
                stud_quantity += wall_quantity
                
                # Create studs for this wall section
                for wall in range(wall_quantity):
                    if face in ["left", "right"]:
                        stud_y_position = prior_position + ((wall_length / (wall_quantity + 1)) * (wall + 1))
                        stud = cq.Workplane('XY').box(stud_height, stud_width, stud_length).translate((new_x, stud_y_position, new_z))
                        assembly.add(stud, name=f"{member_type}_{face}_story{story}_section{index}_wall{wall+1}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                        self.stud_centerlines[face].append(stud_y_position)
                    elif face in ["front", "rear"]:
                        stud_x_position = prior_position + ((wall_length / (wall_quantity + 1)) * (wall + 1))
                        # Special case: skip stud at position 240 for front face, story 1
                        if face == "front" and story == 1 and stud_x_position == 240:
                            stud_quantity = stud_quantity - 1
                            continue
                        else:
                            stud = cq.Workplane('XY').box(stud_width, stud_height, stud_length).translate((stud_x_position, new_y, new_z))
                            assembly.add(stud, name=f"{member_type}_{face}_story{story}_section{index}_wall{wall+1}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
                            self.stud_centerlines[face].append(stud_x_position)
            
            total_quantity += stud_quantity
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, stud_length / 12, stud_width, stud_height, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_girts(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add girts for a story."""
        member_type = "girt"
        total_quantity = 0
        girt_width = 4
        girt_depth = 6
        
        ceiling_heights = self.calculated_ceiling_heights
        floor_heights = self.calculated_floor_heights
        floor_height = floor_heights[story - 1]
        ceiling_height = ceiling_heights[story - 1]
        next_floor_height = floor_heights[story]
        joist_height = self.joist_heights[story - 1] if story <= len(self.joist_heights) else self.joist_heights[-1]
            
        for face in self.faces:
            dimension = self.faces[face]
            right_dimension = self.faces["right"]
            front_dimension = self.faces["front"]

            if dimension <= self.max_member_length:
                quantity = 1
                girt_length = dimension
            elif dimension >= self.max_member_length:
                quantity = math.ceil(dimension / self.max_member_length)
                girt_length = dimension / quantity
            else:
                quantity = 1
                girt_length = self.max_member_length
            
            total_quantity += quantity
            
            # Create girts for this face
            for q in range(quantity):
                girt_counter = q + 1
                
                if face == "front":
                    new_x = (girt_length * girt_counter) - (girt_length / 2) + x_offset
                    new_y = 0 + y_offset
                    new_z = floor_height - (girt_depth / 2) - joist_height
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (girt_length * girt_counter) - (girt_length / 2) + x_offset
                    new_y = -right_dimension + y_offset
                    new_z = floor_height - (girt_depth / 2) - joist_height
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z))
                elif face == "left":
                    # Left girts run along Y axis (front to rear)
                    # X position: fixed at left wall (x=0)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = (girt_length * girt_counter) - (girt_length / 2) + x_offset
                    new_y = 0 + y_offset
                    new_z = floor_height - (girt_depth / 2)
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
                elif face == "right":
                    # Right girts run along Y axis (front to rear)
                    # X position: fixed at right wall (x=front_dimension)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = (girt_length * girt_counter) - (girt_length / 2) + x_offset
                    new_y = front_dimension + y_offset
                    new_z = floor_height - (girt_depth / 2)
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
                
                # Add the girt to the assembly with descriptive name
                assembly.add(girt, name=f"{member_type}_{face}_story{story}_{girt_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, girt_length / 12, girt_width, girt_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_plates(self, assembly: cq.Assembly, story: int, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add plates for a story."""
        member_type = "plate"
        plate_width = 4
        plate_depth = 6
        total_quantity = 0
        floor_heights = self.calculated_floor_heights
        next_floor_height = floor_heights[story]
        next_joist_height = self.joist_heights[story] if story <= len(self.joist_heights) else self.joist_heights[-1]
        
        
        for face in self.faces:
            dimension = self.faces[face]
            right_dimension = self.faces["right"]
            front_dimension = self.faces["front"]

            if dimension <= self.max_member_length:
                quantity = 1
                plate_length = dimension
            elif dimension >= self.max_member_length:
                quantity = math.ceil(dimension / self.max_member_length)
                plate_length = dimension / quantity
            else:
                quantity = 1
                plate_length = self.max_member_length

            total_quantity += quantity

            for q in range(quantity):
    
                plate_counter = q + 1
                
                if face == "front":
                    new_x = (plate_length * plate_counter) - (plate_length / 2) + x_offset
                    new_y = 0 + y_offset
                    new_z = next_floor_height - (plate_depth / 2) - next_joist_height
                    plate = cq.Workplane('XY').box(plate_length, plate_width, plate_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (plate_length * plate_counter) - (plate_length / 2) + x_offset
                    new_y = -right_dimension + y_offset
                    new_z = next_floor_height - (plate_depth / 2) - next_joist_height
                    plate = cq.Workplane('XY').box(plate_length, plate_width, plate_depth).translate((new_x, new_y, new_z))
                elif face == "left":
                    new_x = (plate_length * plate_counter) - (plate_length / 2) + x_offset
                    new_y = 0 + y_offset
                    new_z = next_floor_height - (plate_depth / 2)
                    plate = cq.Workplane('XY').box(plate_length, plate_width, plate_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1),(0,0,0), 90)
                elif face == "right":
                    new_x = (plate_length * plate_counter) - (plate_length / 2) + x_offset
                    new_y = +(front_dimension) + y_offset
                    new_z = next_floor_height - (plate_depth / 2)
                    plate = cq.Workplane('XY').box(plate_length, plate_width, plate_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1),(0,0,0), 90)

                assembly.add(plate, name=f"{member_type}_{face}_story{story}_{plate_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, plate_length / 12, plate_width, plate_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_false_plates(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add false plates for roof."""
        member_type = "false_plate"
        false_plate_width = 10
        false_plate_depth = 2
        total_quantity = 0
        floor_heights = self.calculated_floor_heights
        stories = self.floorplan.stories
        floor_height = floor_heights[stories]


        for face in ["front", "rear"]:
            dimension = self.faces[face]
            right_dimension = self.faces["right"]
            roof_overhang = self.roof_overhang
            
            if dimension <= self.max_member_length:
                quantity = 1
                false_plate_length = dimension
            elif dimension >= self.max_member_length:
                quantity = math.ceil(dimension / self.max_member_length)
                false_plate_length = dimension / quantity
            else:
                quantity = 1
                false_plate_length = self.max_member_length

            total_quantity += quantity

            for q in range(quantity):
                false_plate_counter = q + 1

                if face == "front":
                    new_x = (false_plate_length * false_plate_counter) - (false_plate_length / 2) + x_offset
                    new_y = (roof_overhang/2)
                    new_z = floor_height + (false_plate_depth / 2)
                    false_plate = cq.Workplane('XY').box(false_plate_length, false_plate_width, false_plate_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (false_plate_length * false_plate_counter) - (false_plate_length / 2) + x_offset
                    new_y = -(right_dimension) - (roof_overhang/2)
                    new_z = floor_height + (false_plate_depth / 2)
                    false_plate = cq.Workplane('XY').box(false_plate_length, false_plate_width, false_plate_depth).translate((new_x, new_y, new_z))
                else: continue

                assembly.add(false_plate, name=f"{member_type}_{face}_{false_plate_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, false_plate_length / 12, false_plate_width, false_plate_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_rafters(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add rafters for roof."""
        member_type = "rafter"
        rafter_width = 3
        rafter_depth = 6
        rafter_spacing = self.rafter_spacing
        roof_overhang = self.roof_overhang
        roof_pitch_degrees = self.roof_pitch_degrees
        total_quantity = 0

        floor_heights = self.calculated_floor_heights
        stories = self.floorplan.stories
        floor_height = floor_heights[stories]
        
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        
        for face in ["front", "rear"]:
            quantity = math.ceil(front_dimension / rafter_spacing) + 1
            total_quantity += quantity
            
            # Rafter extends from ridge to 12" past actual weatherboard outer faces
            # Actual weatherboard positions: front y=2.674, rear y=-250.528
            # Match the eave positions used in roof_builder.py
            front_weatherboard_y = 2.674
            rear_weatherboard_y = -250.528
            # Ridge should be at midpoint between weatherboard outer faces to avoid gap
            centerline_y = (front_weatherboard_y + rear_weatherboard_y) / 2
            
            # Calculate rafter run for this specific face to match eaves exactly
            roof_pitch_radians = roof_pitch_degrees * (math.pi / 180)
            rafter_cos = math.cos(roof_pitch_radians)
            rafter_sin = math.sin(roof_pitch_radians)
            
            if face == "front":
                # Front rafter: ridge to front eave (12" past front weatherboard)
                # Adjust target to compensate for rotation geometry (empirical correction: -5.73")
                target_eave_y = front_weatherboard_y + roof_overhang - 5.73
                rafter_run = target_eave_y - centerline_y
                rafter_length = rafter_run / rafter_cos if rafter_cos > 0 else rafter_run
                # Position rafter before rotation: account for pitch rotation effect on horizontal position
                # The rafter is created along X, then pitched, then rotated 90° around Z
                # We need to position it so that after these rotations, it spans from ridge to eave
                new_x = +(right_dimension/2) + (rafter_length/2 * rafter_cos) + x_offset
                roof_pitch = roof_pitch_degrees
                new_z = floor_height + (rafter_length/2 * rafter_sin) - rafter_depth
            elif face == "rear":
                # Rear rafter: ridge to rear eave (12" past rear weatherboard)
                # Adjust target to compensate for rotation geometry (empirical correction: -2.12")
                target_eave_y = rear_weatherboard_y - roof_overhang - 2.12
                rafter_run = centerline_y - target_eave_y
                rafter_length = rafter_run / rafter_cos if rafter_cos > 0 else rafter_run
                # Position rafter before rotation: account for pitch rotation effect on horizontal position
                # The rafter is created along X, then pitched, then rotated 90° around Z
                # We need to position it so that after these rotations, it spans from ridge to eave
                new_x = +(right_dimension/2) - (rafter_length/2 * rafter_cos) + x_offset
                roof_pitch = 180 - roof_pitch_degrees
                new_z = floor_height + (rafter_length/2 * rafter_sin) - rafter_depth

            for q in range(quantity):

                rafter_counter = q + 1

                if rafter_counter == 1:
                    new_y = 0 + y_offset
                else:
                    new_y = (rafter_spacing * (rafter_counter - 1)) + y_offset


                rafter = cq.Workplane('XY').box(rafter_length, rafter_width, rafter_depth).translate((new_x, new_y, new_z)).rotateAboutCenter((0, 1, 0),roof_pitch).rotate((0,0,1),(0,0,0),90)
                assembly.add(rafter, name=f"{member_type}_{face}_{rafter_counter}", color=cq.Color(0.55, 0.45, 0.33))  # Wood color
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, rafter_length / 12, rafter_width, rafter_depth, self.materials
        )
        add_production_bom_quantities(
            component_id, raw_material_id, 1, 2,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
        add_sales_bom_quantities(
            component_id, self.structure_hash, total_quantity, 3,
            self.bom_quantities, self.bom_levels, self.bom_components
        )
    
    def _add_gable_framing(self, assembly: cq.Assembly, x_offset: float = 0, y_offset: float = 0) -> None:
        """Add gable end framing for side-gable roofs."""
        member_type = "gable_stud"
        stud_width = 3
        stud_depth = 6
        stud_spacing = 21  # Match rafter spacing
        total_quantity = 0
        
        floor_heights = self.calculated_floor_heights
        stories = self.floorplan.stories
        floor_height = floor_heights[stories]
        
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        roof_overhang = self.roof_overhang
        roof_pitch_degrees = self.roof_pitch_degrees
        roof_pitch_radians = roof_pitch_degrees * (math.pi / 180)
        
        # Calculate ridge height
        ridge_run = right_dimension / 2
        ridge_height = floor_height + (ridge_run * math.tan(roof_pitch_radians))
        
        # Gable ends are at x=0 (left) and x=front_dimension (right)
        # We need studs running up the rake from the wall to the ridge
        # Studs should be spaced along the Y axis (depth of building)
        
        for face in ["left", "right"]:
            # Number of studs along the gable face
            quantity = math.ceil(front_dimension / stud_spacing) + 1
            total_quantity += quantity
            
            # Determine X position based on face
            # Adjust for 12" overhang on each end
            if face == "left":
                face_x = -roof_overhang + x_offset
            else:  # right
                face_x = front_dimension + roof_overhang + x_offset
            
            for q in range(quantity):
                # Y position along the gable face
                stud_y = (q * stud_spacing) + y_offset
                
                # Calculate the height of this stud based on its Y position
                # Distance from center of building (where ridge is)
                distance_from_center = abs(stud_y - y_offset + (right_dimension / 2))
                
                # Height at this point (accounting for roof slope)
                if distance_from_center <= (right_dimension / 2):
                    # Point is under the roof
                    stud_top_z = floor_height + ((right_dimension / 2) - distance_from_center) * math.tan(roof_pitch_radians)
                    stud_length = stud_top_z - floor_height
                    
                    if stud_length > 1:  # Only add stud if it's at least 1" tall
                        stud_z = floor_height + (stud_length / 2)
                        
                        # Create stud
                        stud = cq.Workplane('XY').box(stud_depth, stud_width, stud_length).translate((face_x, stud_y, stud_z))
                        
                        # Add to assembly
                        assembly.add(stud, name=f"{member_type}_{face}_{q+1}", color=cq.Color(0.55, 0.45, 0.33))
        
        # Add BOM tracking
        if total_quantity > 0:
            avg_stud_length = (ridge_height - floor_height) / 2  # Approximate average
            raw_material_id, component_id = add_framing_materials(
                member_type, avg_stud_length / 12, stud_width, stud_depth, self.materials
            )
            add_production_bom_quantities(
                component_id, raw_material_id, 1, 2,
                self.bom_quantities, self.bom_levels, self.bom_components
            )
            add_sales_bom_quantities(
                component_id, self.structure_hash, total_quantity, 3,
                self.bom_quantities, self.bom_levels, self.bom_components
            )

