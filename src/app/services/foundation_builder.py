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
        
        # Calculate total foundation height
        total_foundation_height = foundation.foundation_courses * (block_height + joint)
        
        # Create assembly with color
        foundation_assembly = cq.Assembly()
        block_color = cq.Color(0.7, 0.7, 0.7)
        
        # Generate blocks for each course
        # Foundation extends downward from z=0, so blocks are positioned at negative z
        for course_idx in range(foundation.foundation_courses):
            # Calculate z position for this course (downward from top at z=0)
            z_offset = -total_foundation_height + course_idx * (block_height + joint) + block_height/2
            
            # Front wall (along X axis)
            x_pos = 0
            block_idx = 0
            while x_pos + block_length <= foundation_width:
                block = (
                    cq.Workplane("XY")
                    .box(block_length, block_width, block_height)
                    .translate((x_pos + block_length/2, block_width/2, z_offset))
                )
                foundation_assembly.add(block, name=f"front_c{course_idx}_b{block_idx}", color=block_color)
                x_pos += block_length + joint
                block_idx += 1
            
            # Add one more block to close the right corner gap
            if x_pos < foundation_width - block_width:
                block = (
                    cq.Workplane("XY")
                    .box(block_length, block_width, block_height)
                    .translate((x_pos + block_length/2, block_width/2, z_offset))
                )
                foundation_assembly.add(block, name=f"front_c{course_idx}_b{block_idx}", color=block_color)
            
            # Rear wall (along X axis)
            x_pos = 0
            block_idx = 0
            while x_pos + block_length <= foundation_width:
                block = (
                    cq.Workplane("XY")
                    .box(block_length, block_width, block_height)
                    .translate((x_pos + block_length/2, -foundation_depth + block_width/2, z_offset))
                )
                foundation_assembly.add(block, name=f"rear_c{course_idx}_b{block_idx}", color=block_color)
                x_pos += block_length + joint
                block_idx += 1
            
            # Add one more block to close the right corner gap
            if x_pos < foundation_width - block_width:
                block = (
                    cq.Workplane("XY")
                    .box(block_length, block_width, block_height)
                    .translate((x_pos + block_length/2, -foundation_depth + block_width/2, z_offset))
                )
                foundation_assembly.add(block, name=f"rear_c{course_idx}_b{block_idx}", color=block_color)
            
            # Left wall (along Y axis, start right after front corner block to close gap)
            y_pos = 0
            block_idx = 0
            while y_pos + block_length <= foundation_depth:
                # Skip blocks that would overlap with corners
                if y_pos < block_width or y_pos + block_length > foundation_depth - block_width:
                    y_pos += block_length + joint
                    continue
                    
                block = (
                    cq.Workplane("XY")
                    .box(block_width, block_length, block_height)
                    .translate((block_width/2, -y_pos - block_length/2, z_offset))
                )
                foundation_assembly.add(block, name=f"left_c{course_idx}_b{block_idx}", color=block_color)
                y_pos += block_length + joint
                block_idx += 1
            
            # Right wall (along Y axis, start right after front corner block to close gap)
            y_pos = 0
            block_idx = 0
            while y_pos + block_length <= foundation_depth:
                # Skip blocks that would overlap with corners
                if y_pos < block_width or y_pos + block_length > foundation_depth - block_width:
                    y_pos += block_length + joint
                    continue
                    
                block = (
                    cq.Workplane("XY")
                    .box(block_width, block_length, block_height)
                    .translate((foundation_width - block_width/2, -y_pos - block_length/2, z_offset))
                )
                foundation_assembly.add(block, name=f"right_c{course_idx}_b{block_idx}", color=block_color)
                y_pos += block_length + joint
                block_idx += 1
        
        return foundation_assembly
