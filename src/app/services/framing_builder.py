"""
Framing builder service using CadQuery.
Integrates framing.py functionality into the API architecture.
"""
import cadquery as cq
import math
from typing import Dict, Any, List, Tuple
from collections import defaultdict

from app.models.structure import Structure
from app.models.floorplan import Dimensions
from app.utils.materials_helper import (
    add_framing_materials,
    add_production_bom_quantities,
    add_sales_bom_quantities
)


class FramingBuilder:
    """Builds framing geometry and tracks BOM data."""
    
    def __init__(self, structure: Structure, structure_hash: str):
        """
        Initialize framing builder.
        
        Args:
            structure: Building structure specification
            structure_hash: Structure hash identifier for BOM tracking
        """
        self.structure = structure
        self.structure_hash = structure_hash
        self.floorplan = structure.floorplan
        self.dimensions = structure.floorplan.dimensions
        self.roof = structure.roof
        
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
        self.bay_spacing = 37
        self.lap = 8
        self.chair_rail_height = 30
        self.joist_spacing = self.floorplan.spacing.joist_spacing
        self.stud_spacing = self.floorplan.spacing.stud_spacing
        self.rafter_spacing = self.floorplan.spacing.rafter_spacing
        self.ceiling_heights = self.floorplan.ceiling_heights or [120, 108]
        self.joist_heights = self.floorplan.joist_heights or [10, 9, 8]
        self.roof_overhang = 12  # Default, could come from roof config
        self.roof_pitch_degrees = self.roof.roof_pitch if self.roof else 40
        
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
                    cumulative = 0
                    for width in bay_widths:
                        cumulative += width / 2
                        centerlines[face].append(cumulative)
                        cumulative += width / 2
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
    
    def build(self) -> Tuple[cq.Assembly, Dict[str, Any]]:
        """
        Build complete framing structure.
        
        Returns:
            Tuple of (CadQuery Assembly, BOM data dictionary)
        """
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
        x_offset = -front_dimension / 2
        y_offset = right_dimension / 2
        
        # Build framing components in order
        self._add_sills(assembly, x_offset, y_offset)
        self._add_posts(assembly, x_offset, y_offset)
        
        # Build per story
        for story in range(1, self.floorplan.stories + 1):
            self._add_joists(assembly, story, x_offset, y_offset)
            self._add_braces(assembly, story, x_offset, y_offset)
            self._add_bays(assembly, story, x_offset, y_offset)
            self._add_studs(assembly, story, x_offset, y_offset)
            self._add_girts(assembly, story, x_offset, y_offset)
            self._add_plates(assembly, story, x_offset, y_offset)
        
        # Add roof components
        self._add_false_plates(assembly, x_offset, y_offset)
        self._add_rafters(assembly, x_offset, y_offset)
        
        # Prepare BOM data
        bom_data = {
            "materials": self.materials,
            "bom_components": self.bom_components,
            "bom_quantities": self.bom_quantities,
            "bom_levels": self.bom_levels
        }
        
        return assembly, bom_data
    
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
            quantity = int(dimension / 240)
            
            for q in range(quantity):
                sill_counter = q + 1
                
                if face == "front":
                    new_x = (dimension / quantity) * sill_counter - 120 + x_offset
                    new_y = 0 + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(240, sill_height, sill_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (dimension / quantity) * sill_counter - 120 + x_offset
                    new_y = -right_dimension + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(240, sill_height, sill_depth).translate((new_x, new_y, new_z))
                elif face == "left":
                    # Left sills run along Y axis (front to rear)
                    # X position: fixed at left wall (x=0)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = 0 + x_offset
                    new_y = (right_dimension / quantity) * sill_counter - 120 + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(240, sill_height, sill_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
                elif face == "right":
                    # Right sills run along Y axis (front to rear)
                    # X position: fixed at right wall (x=front_dimension)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = front_dimension + x_offset
                    new_y = (right_dimension / quantity) * sill_counter - 120 + y_offset
                    new_z = sill_z_offset
                    sill = cq.Workplane('XY').box(240, sill_height, sill_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
                
                assembly.add(sill)
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
        right_offset = right_dimension / 2
        
        post_width = 6
        post_depth = 4
        post_height = 230
        quantity = 4
        member_type = "post"
        
        front_left_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((0 + x_offset, 0 + y_offset, right_offset))
        rear_left_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((0 + x_offset, -right_dimension + y_offset, right_offset))
        front_right_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((front_dimension + x_offset, 0 + y_offset, right_offset))
        rear_right_post = cq.Workplane('XY').box(post_width, post_depth, post_height).translate((front_dimension + x_offset, -right_dimension + y_offset, right_offset))
        
        assembly.add(front_left_post)
        assembly.add(rear_left_post)
        assembly.add(front_right_post)
        assembly.add(rear_right_post)
        
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
        
        # Sill dimensions (matching _add_sills)
        sill_depth = 10
        sill_z_offset = sill_depth / 2  # Sill bottom at z=0, top at z=10
        
        # Calculate previous ceiling height
        previous_ceiling_height = 0
        if story > 1:
            for p in range(story - 1):
                previous_ceiling_height += self.ceiling_heights[p] + (self.joist_heights[p] / 2)
        
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        
        if story == len(self.joist_heights):
            joist_length = (self.roof_overhang * 2) + right_dimension
            previous_ceiling_height = previous_ceiling_height - 4
        else:
            joist_length = right_dimension
        
        # For first story, joists sit on top of sills (level with top of sill at z=10)
        # Since joist box is centered, we need to add half joist height to position bottom at z=10
        if story == 1:
            # First floor joists: bottom at top of sill (z = sill_depth = 10)
            # Box is centered, so center is at z = 10 + (joist_height / 2)
            joist_z = sill_depth + (joist_height / 2)
        else:
            # Upper story joists: use previous_ceiling_height calculation
            # Box is centered, so we need to add half joist height
            joist_z = previous_ceiling_height + (joist_height / 2)
        
        quantity = math.ceil(front_dimension / self.joist_spacing)
        
        # Match original positioning pattern exactly:
        # Original: new_x = right_dimension/2 (fixed), new_y = (q * joist_spacing) + joist_spacing (spaced)
        # Apply offsets to center on foundation
        for q in range(quantity):
            # X position: match original pattern (right_dimension/2) with offset
            new_x = right_dimension / 2 + x_offset
            # Y position: spaced along Y as in original, with offset
            new_y = (q * self.joist_spacing) + self.joist_spacing + y_offset
            new_z = joist_z
            joist = cq.Workplane('XY').box(joist_length, joist_width, joist_height).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
            assembly.add(joist)
        
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
        
        current_ceiling_height = self.ceiling_heights[story - 1] if story <= len(self.ceiling_heights) else self.ceiling_heights[-1]
        
        # Calculate prior and next ceiling heights
        if story == 1:
            prior_ceiling_height = 0
            joist_height_adjustment = 0
        else:
            prior_ceiling_height = self.ceiling_heights[story - 2]
            joist_height_adjustment = (self.joist_heights[story - 2] / 2) - (joist_height / 2)
        
        if len(self.ceiling_heights) > story:
            next_ceiling_height = self.ceiling_heights[story]
        else:
            next_ceiling_height = 0
        
        for face in self.faces:
            brace_centerline = self.centerlines[face][0] if self.centerlines[face] else 64
            index = len(self.centerlines[face]) - 1 if self.centerlines[face] else 0
            dimension = self.faces[face]
            alt_brace_centerline = dimension - (self.centerlines[face][index] if self.centerlines[face] else dimension - 64)
            
            total_quantity += 2
            
            # Set ceiling heights based on story and face
            if story == 1:
                alt_ceiling_height = next_ceiling_height + joist_height_adjustment
                ceiling_height = current_ceiling_height
                previous_ceiling_height = 0
                alt_previous_ceiling_height = 0
            elif story == 2:
                alt_ceiling_height = prior_ceiling_height
                ceiling_height = current_ceiling_height
                previous_ceiling_height = prior_ceiling_height + joist_height_adjustment
                alt_previous_ceiling_height = current_ceiling_height + joist_height_adjustment
            else:
                ceiling_height = current_ceiling_height
                alt_ceiling_height = current_ceiling_height
                previous_ceiling_height = prior_ceiling_height + joist_height_adjustment
                alt_previous_ceiling_height = prior_ceiling_height + joist_height_adjustment
            
            # Calculate brace positions and angles (simplified - full implementation would match original logic)
            if face == "left":
                brace_height = math.ceil(ceiling_height * (2/3))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = 180 - math.degrees(math.atan(brace_centerline / brace_height))
                new_x = brace_centerline / 2 + x_offset
                new_y = 0 + y_offset
                new_z = (brace_height / 2) + previous_ceiling_height
                
                alt_brace_height = math.ceil(alt_ceiling_height * (2/3))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = 0 + x_offset
                alt_y = -(alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + alt_previous_ceiling_height
            elif face == "rear":
                brace_height = math.ceil(ceiling_height * (5/8))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = 180 - math.degrees(math.atan(brace_centerline / brace_height))
                new_x = brace_centerline / 2 + x_offset
                new_y = -right_dimension + y_offset
                new_z = (brace_height / 2) + previous_ceiling_height
                
                alt_brace_height = math.ceil(alt_ceiling_height * (5/8))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = 180 - math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = 0 + x_offset
                alt_y = -right_dimension + (alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + alt_previous_ceiling_height
            elif face == "right":
                brace_height = math.ceil(ceiling_height * (2/3))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = math.degrees(math.atan(brace_centerline / brace_height))
                new_x = front_dimension - (brace_centerline / 2) + x_offset
                new_y = 0 + y_offset
                new_z = (brace_height / 2) + previous_ceiling_height
                
                alt_brace_height = math.ceil(alt_ceiling_height * (2/3))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = front_dimension + x_offset
                alt_y = -(alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + alt_previous_ceiling_height
            else:  # front
                brace_height = math.ceil(ceiling_height * (5/8))
                brace_length = math.sqrt(math.pow(brace_centerline, 2) + math.pow(brace_height, 2))
                brace_angle = math.degrees(math.atan(brace_centerline / brace_height))
                new_x = front_dimension - (brace_centerline / 2) + x_offset
                new_y = -right_dimension + y_offset
                new_z = (brace_height / 2) + previous_ceiling_height
                
                alt_brace_height = math.ceil(alt_ceiling_height * (5/8))
                alt_brace_length = math.sqrt(math.pow(alt_brace_centerline, 2) + math.pow(alt_brace_height, 2))
                alt_brace_angle = 180 - math.degrees(math.atan(alt_brace_centerline / alt_brace_height))
                alt_x = front_dimension + x_offset
                alt_y = -right_dimension + (alt_brace_centerline / 2) + y_offset
                alt_z = (alt_brace_height / 2) + alt_previous_ceiling_height
            
            # Add braces to assembly
            brace = cq.Workplane('XY').box(brace_width, brace_depth, brace_length).translate((new_x, new_y, new_z)).rotateAboutCenter((0, 1, 0), brace_angle)
            alt_brace = cq.Workplane('XY').box(brace_width, brace_depth, alt_brace_length).translate((alt_x, alt_y, alt_z)).rotateAboutCenter((0, 1, 0), alt_brace_angle).rotateAboutCenter((0, 0, 1), 90)
            assembly.add(brace)
            assembly.add(alt_brace)
        
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
        member_type = "bay_stud"
        total_quantity = 0
        cripple_quantity = 0
        
        # Find the current story ceiling height
        current_ceiling_height = self.ceiling_heights[story - 1] if story <= len(self.ceiling_heights) else self.ceiling_heights[-1]
        
        # Find the prior ceiling height
        if story == 1:
            prior_ceiling_height = 0
        else:
            prior_ceiling_height = self.ceiling_heights[story - 2]
        
        # Find the next ceiling height
        if len(self.ceiling_heights) > story:
            next_ceiling_height = self.ceiling_heights[story]
        else:
            next_ceiling_height = 0
        
        for face in self.faces:
            centerline = self.centerlines[face]
            if not centerline:
                continue
                
            self.bay_studs[face] = []
            total_quantity += 2 * len(centerline)
            
            # Set the ceiling height depending on the story and face
            # This ensures the mortises aren't at the same height on adjacent faces of the post
            if face in ["left", "right"] and story == 1:
                ceiling_height = next_ceiling_height
                previous_ceiling_height = 0
            elif face in ["left", "right"] and story == 2:
                ceiling_height = prior_ceiling_height
                previous_ceiling_height = current_ceiling_height
            else:
                ceiling_height = current_ceiling_height
                previous_ceiling_height = prior_ceiling_height
            
            # Set base positions for each face
            if face == "front":
                new_x = 0 + x_offset
                new_y = 0 + y_offset
                new_z = previous_ceiling_height + (ceiling_height / 2)
            elif face == "rear":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                new_z = previous_ceiling_height + (ceiling_height / 2)
            elif face == "left":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                new_z = previous_ceiling_height + (ceiling_height / 2)
            elif face == "right":
                new_x = front_dimension + x_offset
                new_y = -right_dimension + y_offset
                new_z = previous_ceiling_height + (ceiling_height / 2)
            
            # Create bay studs for each centerline
            for i, c in enumerate(centerline):
                bay = i + 1
                
                # Determine if cripple stud is needed
                if face in ["left", "right"] and bay in [1, 2]:
                    cripple_flag = True
                elif face == "front" and story == 1 and bay == 3:
                    cripple_flag = False
                elif face in ["rear", "front"]:
                    cripple_flag = True
                else:
                    cripple_flag = False
                
                if face in ["left", "right"]:
                    # Left/right faces: studs positioned along Y axis
                    left_stud_y_position = new_y + c - ((self.bay_spacing + bay_stud_width) / 2)
                    right_stud_y_position = new_y + c + ((self.bay_spacing + bay_stud_width) / 2)
                    left_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, ceiling_height).translate((new_x, left_stud_y_position, new_z))
                    right_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, ceiling_height).translate((new_x, right_stud_y_position, new_z))
                    self.bay_studs[face].append(left_stud_y_position)
                    self.bay_studs[face].append(right_stud_y_position)
                    
                    if cripple_flag:
                        cripple_stud_y_position = left_stud_y_position + (-(left_stud_y_position - right_stud_y_position) / 2)
                        cripple_stud_z_position = previous_ceiling_height + (self.chair_rail_height / 2)
                        cripple_stud = cq.Workplane('XY').box(cripple_stud_height, cripple_stud_width, self.chair_rail_height).translate((new_x, cripple_stud_y_position, cripple_stud_z_position))
                        self.bay_studs[face].append(cripple_stud_y_position)
                        assembly.add(cripple_stud)
                        cripple_quantity += 1
                
                elif face in ["front", "rear"]:
                    # Front/rear faces: studs positioned along X axis
                    left_stud_x_position = new_x + c - ((self.bay_spacing + bay_stud_width) / 2)
                    right_stud_x_position = new_x + c + ((self.bay_spacing + bay_stud_width) / 2)
                    left_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, ceiling_height).translate((left_stud_x_position, new_y, new_z))
                    right_stud = cq.Workplane('XY').box(bay_stud_width, bay_stud_height, ceiling_height).translate((right_stud_x_position, new_y, new_z))
                    self.bay_studs[face].append(left_stud_x_position)
                    self.bay_studs[face].append(right_stud_x_position)
                    
                    if cripple_flag:
                        cripple_stud_x_position = left_stud_x_position + ((right_stud_x_position - left_stud_x_position) / 2)
                        cripple_stud_z_position = previous_ceiling_height + (self.chair_rail_height / 2)
                        cripple_stud = cq.Workplane('XY').box(cripple_stud_width, cripple_stud_height, self.chair_rail_height).translate((cripple_stud_x_position, new_y, cripple_stud_z_position))
                        self.bay_studs[face].append(cripple_stud_x_position)
                        assembly.add(cripple_stud)
                        cripple_quantity += 1
                
                assembly.add(left_stud)
                assembly.add(right_stud)
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, ceiling_height / 12, bay_stud_width, bay_stud_height, self.materials
        )
        raw_material_id_cripple, component_id_cripple = add_framing_materials(
            "cripple_stud", self.chair_rail_height / 12, cripple_stud_width, cripple_stud_height, self.materials
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
        
        # Find the current story ceiling height
        current_ceiling_height = self.ceiling_heights[story - 1] if story <= len(self.ceiling_heights) else self.ceiling_heights[-1]
        
        # Find the prior ceiling height
        if story == 1:
            prior_ceiling_height = 0
        else:
            prior_ceiling_height = self.ceiling_heights[story - 2]
        
        # Find the next ceiling height
        if len(self.ceiling_heights) > story:
            next_ceiling_height = self.ceiling_heights[story]
        else:
            next_ceiling_height = 0
        
        for face in self.faces:
            self.stud_centerlines[face] = []
            stud_positions = self.bay_studs.get(face, []).copy()
            stud_quantity = 0
            
            # Set the ceiling height depending on the story and face
            # This ensures the mortises aren't at the same height on adjacent faces of the post
            if face in ["left", "right"] and story == 1:
                ceiling_height = next_ceiling_height
                previous_ceiling_height = 0
            elif face in ["left", "right"] and story == 2:
                ceiling_height = prior_ceiling_height
                previous_ceiling_height = current_ceiling_height
            else:
                ceiling_height = current_ceiling_height
                previous_ceiling_height = prior_ceiling_height
            
            # Set base positions for each face
            if face == "front":
                new_x = 0 + x_offset
                new_y = 0 + y_offset
                new_z = previous_ceiling_height + (ceiling_height / 2)
                last_position = front_dimension - 6
            elif face == "rear":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                new_z = previous_ceiling_height + (ceiling_height / 2)
                last_position = front_dimension - 6
            elif face == "left":
                new_x = 0 + x_offset
                new_y = -right_dimension + y_offset
                new_z = previous_ceiling_height + (ceiling_height / 2)
                last_position = -right_dimension - 4
            elif face == "right":
                new_x = front_dimension + x_offset
                new_y = -right_dimension + y_offset
                new_z = previous_ceiling_height + (ceiling_height / 2)
                last_position = -right_dimension - 4
            
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
                        stud = cq.Workplane('XY').box(4, 3, ceiling_height).translate((new_x, stud_y_position, new_z))
                        assembly.add(stud)
                        self.stud_centerlines[face].append(stud_y_position)
                    elif face in ["front", "rear"]:
                        stud_x_position = prior_position + ((wall_length / (wall_quantity + 1)) * (wall + 1))
                        # Special case: skip stud at position 240 for front face, story 1
                        if face == "front" and story == 1 and stud_x_position == 240:
                            stud_quantity = stud_quantity - 1
                            continue
                        else:
                            stud = cq.Workplane('XY').box(3, 4, ceiling_height).translate((stud_x_position, new_y, new_z))
                            assembly.add(stud)
                            self.stud_centerlines[face].append(stud_x_position)
            
            total_quantity += stud_quantity
        
        # Add BOM tracking
        raw_material_id, component_id = add_framing_materials(
            member_type, ceiling_height / 12, stud_width, stud_height, self.materials
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
        girt_length = 240
        
        # Find the current story ceiling height
        current_ceiling_height = self.ceiling_heights[story - 1] if story <= len(self.ceiling_heights) else self.ceiling_heights[-1]
        
        # Find the prior ceiling height
        if story == 1:
            prior_ceiling_height = 0
        else:
            prior_ceiling_height = self.ceiling_heights[story - 2]
        
        # Find the next ceiling height
        if len(self.ceiling_heights) > story:
            next_ceiling_height = self.ceiling_heights[story]
        else:
            next_ceiling_height = 0
        
        for face in self.faces:
            dimension = self.faces[face]
            right_dimension = self.faces["right"]
            front_dimension = self.faces["front"]
            quantity = int(dimension / 240)
            
            # Set the ceiling height depending on the story and face
            # This ensures the mortises aren't at the same height on adjacent faces of the post
            if face in ["left", "right"] and story == 1:
                ceiling_height = next_ceiling_height
                previous_ceiling_height = 0
            elif face in ["left", "right"] and story == 2:
                ceiling_height = prior_ceiling_height
                previous_ceiling_height = current_ceiling_height
            else:
                ceiling_height = current_ceiling_height
                previous_ceiling_height = prior_ceiling_height
            
            total_quantity += quantity
            
            # Create girts for this face
            for q in range(quantity):
                girt_counter = q + 1
                
                if face == "front":
                    new_x = (dimension / quantity) * girt_counter - (girt_length / 2) + x_offset
                    new_y = 0 + y_offset
                    new_z = previous_ceiling_height
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z))
                elif face == "rear":
                    new_x = (dimension / quantity) * girt_counter - (girt_length / 2) + x_offset
                    new_y = -right_dimension + y_offset
                    new_z = previous_ceiling_height
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z))
                elif face == "left":
                    # Left girts run along Y axis (front to rear)
                    # X position: fixed at left wall (x=0)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = 0 + x_offset
                    new_y = (right_dimension / quantity) * girt_counter - (girt_length / 2) + y_offset
                    new_z = previous_ceiling_height
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
                elif face == "right":
                    # Right girts run along Y axis (front to rear)
                    # X position: fixed at right wall (x=front_dimension)
                    # Y position: spaced along depth (right_dimension), similar to front/rear spacing
                    new_x = front_dimension + x_offset
                    new_y = (right_dimension / quantity) * girt_counter - (girt_length / 2) + y_offset
                    new_z = previous_ceiling_height
                    girt = cq.Workplane('XY').box(girt_length, girt_width, girt_depth).translate((new_x, new_y, new_z)).rotate((0, 0, 1), (0, 0, 0), 90)
                
                # Add the girt to the assembly
                assembly.add(girt)
        
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
        plate_length = 240
        total_quantity = 0
        
        ceiling_height = self.ceiling_heights[story - 1] if story <= len(self.ceiling_heights) else self.ceiling_heights[-1]
        if story == 1:
            previous_ceiling_height = 0
        else:
            previous_ceiling_height = self.ceiling_heights[story - 2]
        
        for face in self.faces:
            dimension = self.faces[face]
            quantity = int(dimension / 240)
            total_quantity += quantity
        
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
        false_plate_length = 240
        total_quantity = 0
        
        building_height = 0
        for index, value in enumerate(self.joist_heights):
            if index == 0:
                joist_height = 0
            else:
                joist_height = value
            
            if len(self.ceiling_heights) >= (index + 1):
                ceiling_height = self.ceiling_heights[index]
            else:
                ceiling_height = 0
            
            building_height += joist_height + ceiling_height
        
        for face in ["front", "rear"]:
            dimension = self.faces[face]
            quantity = int(dimension / 240)
            total_quantity += quantity
        
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
        total_quantity = 0
        
        building_height = -12
        for index, value in enumerate(self.joist_heights):
            if index == 0:
                joist_height = 0
            else:
                joist_height = value
            
            if len(self.ceiling_heights) >= (index + 1):
                ceiling_height = self.ceiling_heights[index]
            else:
                ceiling_height = 0
            
            building_height += joist_height + ceiling_height
        
        right_dimension = self.faces["right"]
        front_dimension = self.faces["front"]
        
        for face in ["front", "rear"]:
            quantity = int(front_dimension / self.rafter_spacing) + 2
            total_quantity += quantity
            
            rafter_run = (right_dimension / 2) + self.roof_overhang
            roof_pitch_radians = self.roof_pitch_degrees * (math.pi / 180)
            rafter_cos = math.cos(roof_pitch_radians)
            rafter_length = rafter_run / rafter_cos if rafter_cos > 0 else rafter_run
            rafter_height = 6
        
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

