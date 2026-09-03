"""
Foundation builder service using CadQuery.
"""
import cadquery as cq
from app.models.building import Foundation
from app.models.floorplan import Dimensions


class FoundationBuilder:
    """Builds foundation geometry using CadQuery."""
    
    @staticmethod
    def build(foundation: Foundation, dimensions: Dimensions) -> cq.Assembly:
        """
        Build the foundation structure.
        
        Args:
            foundation: Foundation specification
            dimensions: Building dimensions
            
        Returns:
            CadQuery Assembly with foundation geometry and color
        """
        # Get block dimensions
        if foundation.foundation_block_size and len(foundation.foundation_block_size) >= 3:
            block_length = foundation.foundation_block_size[0]
            block_width = foundation.foundation_block_size[1]
            block_height = foundation.foundation_block_size[2]
        else:
            block_length = 40.0
            block_width = 14.0
            block_height = 14.0
        
        joint = foundation.foundation_block_joint
        
        # Building dimensions
        foundation_width = dimensions.front
        foundation_depth = dimensions.left
        
        # Create assembly with color
        foundation_assembly = cq.Assembly()
        block_color = cq.Color(0.7, 0.7, 0.7)
        
        # Generate blocks for each course
        for course_idx in range(foundation.foundation_courses):
            z_offset = course_idx * (block_height + joint)
            
            # Front wall (along X axis)
            x_pos = 0
            block_idx = 0
            while x_pos + block_length <= foundation_width:
                block = (
                    cq.Workplane("XY")
                    .box(block_length, block_width, block_height)
                    .translate((x_pos + block_length/2, block_width/2, z_offset + block_height/2))
                )
                foundation_assembly.add(block, name=f"front_c{course_idx}_b{block_idx}", color=block_color)
                x_pos += block_length + joint
                block_idx += 1
            
            # Rear wall (along X axis)
            x_pos = 0
            block_idx = 0
            while x_pos + block_length <= foundation_width:
                block = (
                    cq.Workplane("XY")
                    .box(block_length, block_width, block_height)
                    .translate((x_pos + block_length/2, -foundation_depth + block_width/2, z_offset + block_height/2))
                )
                foundation_assembly.add(block, name=f"rear_c{course_idx}_b{block_idx}", color=block_color)
                x_pos += block_length + joint
                block_idx += 1
            
            # Left wall (along Y axis, excluding corners to avoid overlap)
            y_pos = block_width + joint
            block_idx = 0
            while y_pos + block_length <= foundation_depth - block_width:
                block = (
                    cq.Workplane("XY")
                    .box(block_width, block_length, block_height)
                    .translate((block_width/2, -y_pos - block_length/2, z_offset + block_height/2))
                )
                foundation_assembly.add(block, name=f"left_c{course_idx}_b{block_idx}", color=block_color)
                y_pos += block_length + joint
                block_idx += 1
            
            # Right wall (along Y axis, excluding corners to avoid overlap)
            y_pos = block_width + joint
            block_idx = 0
            while y_pos + block_length <= foundation_depth - block_width:
                block = (
                    cq.Workplane("XY")
                    .box(block_width, block_length, block_height)
                    .translate((foundation_width - block_width/2, -y_pos - block_length/2, z_offset + block_height/2))
                )
                foundation_assembly.add(block, name=f"right_c{course_idx}_b{block_idx}", color=block_color)
                y_pos += block_length + joint
                block_idx += 1
        
        return foundation_assembly
