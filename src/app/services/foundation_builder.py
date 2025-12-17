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
        # Calculate foundation height based on courses
        # Each course includes block height + joint thickness
        if foundation.foundation_block_size:
            block_height = foundation.foundation_block_size[2] if len(foundation.foundation_block_size) > 2 else 8
        else:
            # Default block sizes based on type
            block_height = 8 if foundation.foundation_type == "limestone-block" else 8
        
        course_height = block_height + foundation.foundation_block_joint
        total_foundation_height = foundation.foundation_courses * course_height
        
        # Foundation should be slightly wider than building
        foundation_overhang = 12  # inches
        
        foundation_width = dimensions.front + (2 * foundation_overhang)
        foundation_depth = dimensions.left + (2 * foundation_overhang)
        
        # Create foundation as a box
        foundation_obj = (
            cq.Workplane("XY")
            .box(foundation_width, foundation_depth, total_foundation_height)
            .translate((0, 0, -total_foundation_height / 2))
        )
        
        # Add visual texture for blocks (simplified representation)
        # In production, you could add actual block courses with joints
        
        # Create assembly with color
        foundation_assembly = cq.Assembly()
        foundation_assembly.add(foundation_obj, name="foundation", color=cq.Color(0.7, 0.7, 0.7))  # Gray
        
        return foundation_assembly
