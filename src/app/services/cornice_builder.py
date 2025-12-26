"""
Cornice builder service using CadQuery.
Creates exterior cornice molding at the top of the building.
"""
import math
import cadquery as cq
from typing import Optional
from app.models.floorplan import Dimensions


class CorniceBuilder:
    """Builds exterior cornice geometry using CadQuery."""
    
    @staticmethod
    def _crown_molding(width: float, height: float) -> cq.Workplane:
        """
        Create a crown molding profile.
        
        Args:
            width: Width of the molding
            height: Height of the molding
            
        Returns:
            2D CadQuery Workplane profile
        """
        segments = 32
        increment = 90 / segments
        board_height = height / math.sqrt(2)
        fillet_height = (1 / 9) * board_height
        board_width = fillet_height
        profile_points = []

        # Top fillet
        profile_points.append((board_width, 0))
        profile_points.append((0, 0))
        profile_points.append((0, -board_width))

        # Cyma recta parameters
        cyma_recta_height = (4 / 9) * board_height
        cyma_recta_radius = cyma_recta_height / 2

        # Cyma recta concave parameters
        concave_center_x = 0
        concave_center_y = -board_width - cyma_recta_radius

        # Cyma recta concave arc
        for segment in range(1, segments):
            angle_degrees = 90 - (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = concave_center_x + (cyma_recta_radius * math.cos(angle_radians))
            arc_y = concave_center_y + (cyma_recta_radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Cyma recta convex parameters
        convex_center_x = 0 + (2 * cyma_recta_radius)
        convex_center_y = concave_center_y

        # Cyma recta convex arc
        for segment in range(1, segments):
            angle_degrees = 180 + (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = convex_center_x + (cyma_recta_radius * math.cos(angle_radians))
            arc_y = convex_center_y + (cyma_recta_radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Middle fillet
        profile_points.append((convex_center_x, convex_center_y - cyma_recta_radius))
        profile_points.append((convex_center_x, convex_center_y - cyma_recta_radius - fillet_height))
        profile_points.append((convex_center_x + fillet_height, convex_center_y - cyma_recta_radius - fillet_height))

        # Cyma reversa parameters
        cyma_reversa_height = (2 / 9) * board_height
        cyma_reversa_radius = cyma_reversa_height / 2
        
        # Cyma reversa convex parameters
        convex_center_x = convex_center_x + fillet_height + cyma_reversa_radius
        convex_center_y = convex_center_y - cyma_recta_radius - fillet_height

        # Cyma reversa convex arc
        for segment in range(1, segments):
            angle_degrees = 180 + (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = convex_center_x + (cyma_reversa_radius * math.cos(angle_radians))
            arc_y = convex_center_y + (cyma_reversa_radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Cyma reversa concave parameters
        concave_center_x = convex_center_x
        concave_center_y = convex_center_y - (cyma_reversa_radius * 2)
        
        # Cyma reversa concave arc
        for segment in range(1, segments):
            angle_degrees = 90 - (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = concave_center_x + (cyma_reversa_radius * math.cos(angle_radians))
            arc_y = concave_center_y + (cyma_reversa_radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Add the bottom fillet
        profile_points.append((concave_center_x + cyma_reversa_radius, concave_center_y))
        profile_points.append((concave_center_x + cyma_reversa_radius + board_width, concave_center_y))
        profile_points.append((concave_center_x + cyma_reversa_radius + board_width, concave_center_y + board_width))
            
        # Create the polyline
        profile = cq.Workplane("XZ").polyline(profile_points).close()

        return profile

    @staticmethod
    def _cavetto_board(
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        top_width: float = 1.0,
        bottom_width: float = 0.25,
        height: float = 8.0
    ) -> cq.Workplane:
        """
        Create a cavetto board profile.
        
        Args:
            offset_x: X offset for the profile
            offset_y: Y offset for the profile
            top_width: Width at the top
            bottom_width: Width at the bottom
            height: Height of the board
            
        Returns:
            2D CadQuery Workplane profile
        """
        segments = 32
        increment = 90 / segments
        radius = (top_width - bottom_width)
        profile_points = []

        # Append starting points
        profile_points.append((offset_x, offset_y))
        profile_points.append((offset_x + top_width, offset_y))
        profile_points.append((offset_x + top_width, offset_y - height))
        profile_points.append((offset_x + radius, offset_y - height))

        # Draw the arc
        center_x = offset_x
        center_y = offset_y - height

        for segment in range(1, segments):
            angle_degrees = 0 + (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = center_x + (radius * math.cos(angle_radians))
            arc_y = center_y + (radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Add the final point
        profile_points.append((center_x, center_y + radius))

        # Create the polyline
        profile = cq.Workplane("XZ").polyline(profile_points).close()

        return profile

    @staticmethod
    def _bed_molding(width: float, height: float) -> cq.Workplane:
        """
        Create a bed molding profile.
        
        Args:
            width: Width of the molding
            height: Height of the molding
            
        Returns:
            2D CadQuery Workplane profile
        """
        segments = 32
        increment = 90 / segments
        board_height = height / math.sqrt(2)
        fillet_height = (1 / 9) * board_height
        board_width = fillet_height
        profile_points = []

        # Top fillet
        profile_points.append((board_width, 0))
        profile_points.append((0, 0))
        profile_points.append((0, -board_width))
        profile_points.append((board_width, -board_width))

        # Ovolo parameters
        ovolo_height = (4 / 9) * board_height
        ovolo_radius = ovolo_height / 2

        # Ovolo convex parameters
        convex_center_x = board_width + ovolo_radius
        convex_center_y = -board_width

        # Cyma recta convex arc
        for segment in range(1, segments):
            angle_degrees = 180 + (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = convex_center_x + (ovolo_radius * math.cos(angle_radians))
            arc_y = convex_center_y + (ovolo_radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Middle fillet
        profile_points.append((convex_center_x, convex_center_y - ovolo_radius))
        profile_points.append((convex_center_x, convex_center_y - ovolo_radius - fillet_height))
        profile_points.append((convex_center_x + fillet_height, convex_center_y - ovolo_radius - fillet_height))

        # Cyma reversa parameters
        cyma_reversa_height = (2 / 9) * board_height
        cyma_reversa_radius = cyma_reversa_height / 2
        
        # Cyma reversa convex parameters
        convex_center_x = convex_center_x + fillet_height + cyma_reversa_radius
        convex_center_y = convex_center_y - ovolo_radius - fillet_height

        # Cyma reversa convex arc
        for segment in range(1, segments):
            angle_degrees = 180 + (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = convex_center_x + (cyma_reversa_radius * math.cos(angle_radians))
            arc_y = convex_center_y + (cyma_reversa_radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Cyma reversa concave parameters
        concave_center_x = convex_center_x
        concave_center_y = convex_center_y - (cyma_reversa_radius * 2)
        
        # Cyma reversa concave arc
        for segment in range(1, segments):
            angle_degrees = 90 - (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = concave_center_x + (cyma_reversa_radius * math.cos(angle_radians))
            arc_y = concave_center_y + (cyma_reversa_radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Add the bottom fillet
        profile_points.append((concave_center_x + cyma_reversa_radius, concave_center_y))
        profile_points.append((concave_center_x + cyma_reversa_radius + board_width, concave_center_y))
        profile_points.append((concave_center_x + cyma_reversa_radius + board_width, concave_center_y + board_width))
            
        # Create the polyline
        profile = cq.Workplane("XZ").polyline(profile_points).close()

        return profile

    @staticmethod
    def _cyma_reversa_band(width: float, height: float) -> cq.Workplane:
        """
        Create a cyma reversa band profile.
        
        Args:
            width: Width of the band
            height: Height of the band
            
        Returns:
            2D CadQuery Workplane profile
        """
        segments = 32
        increment = 90 / segments
        profile_points = []
        fillet_height = (1 / 3) * height

        # Add initial points
        profile_points.append((width, fillet_height))
        profile_points.append((-fillet_height, fillet_height))
        profile_points.append((-fillet_height, 0))
        profile_points.append((0, 0))
        profile_points.append((width, 0))
        
        
        # Cyma reversa parameters
        cyma_reversa_height = (2 / 3) * height
        cyma_reversa_radius = cyma_reversa_height / 2
        
        # Cyma reversa convex parameters
        convex_center_x = cyma_reversa_radius
        convex_center_y = 0

        # Cyma reversa convex arc
        for segment in range(1, segments):
            angle_degrees = 180 + (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = convex_center_x + (cyma_reversa_radius * math.cos(angle_radians))
            arc_y = convex_center_y + (cyma_reversa_radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Cyma reversa concave parameters
        concave_center_x = convex_center_x
        concave_center_y = convex_center_y - (cyma_reversa_radius * 2)
        
        # Cyma reversa concave arc
        for segment in range(1, segments):
            angle_degrees = 90 - (segment * increment)
            angle_radians = math.radians(angle_degrees)

            arc_x = concave_center_x + (cyma_reversa_radius * math.cos(angle_radians))
            arc_y = concave_center_y + (cyma_reversa_radius * math.sin(angle_radians))

            profile_points.append((arc_x, arc_y))

        # Add the final points
        profile_points.append((cyma_reversa_radius * 2, -height))
        profile_points.append((width, -height))

        # Create the polyline
        profile = cq.Workplane("XZ").polyline(profile_points).close()

        return profile

    @staticmethod
    def build(
        dimensions: Dimensions,
        building_height: float,
        roof_type: str
    ) -> Optional[cq.Assembly]:
        """
        Build Georgian cornice around the perimeter of the building.
        
        Args:
            dimensions: Building dimensions
            building_height: Total building height in inches (Z coordinate for top of building)
            roof_type: Type of roof ("side-gable", "front-gable", "hipped-gable", "side-gable-with-shed")
            
        Returns:
            CadQuery Assembly with cornice components, or None if dimensions are invalid
        """
        if not dimensions:
            return None
        
        # Create the cornice assembly
        cornice = cq.Assembly()
        
        # Determine which faces get cornice based on roof type
        if roof_type == "side-gable" or roof_type == "side-gable-with-shed":
            # Side gable: cornice on front and rear faces only
            faces_to_build = ["front", "rear"]
        elif roof_type == "front-gable":
            # Front gable: cornice on left and right faces only
            faces_to_build = ["left", "right"]
        elif roof_type == "hipped-gable":
            # Hipped roof: cornice on all 4 faces
            faces_to_build = ["front", "rear", "left", "right"]
        else:
            # Default to all faces if unknown roof type
            faces_to_build = ["front", "rear", "left", "right"]
        
        # Stud depth (standard)
        stud_depth = 6
        
        # Crown molding parameters
        crown_width = 1.0
        crown_height = 6.0
        crown_z_position = building_height - 18.0 # Position at top of building
        
        # Corona (cavetto + fascia) parameters
        corona_z_position = building_height - 18.0
        fascia_height = 0.75
        
        # Modillion spacing
        modillion_spacing = 9.0
        
        # Bed molding parameters
        bed_molding_height = 5.5
        
        # Build cornice for each face
        # Cornice is extruded along Y by default (from XZ plane profile)
        # Front/rear faces need it along X (rotate 90° around Z)
        # Left/right faces need it along Y (no rotation needed)
        # Added 10 inches to the front and rear faces to account for the stud depth
        face_map = {
            "front": (dimensions.front, 90, dimensions.front / 2, 20, 0),
            "rear": (dimensions.rear, 270, dimensions.front / 2, -dimensions.right - 20, 0),
            "left": (dimensions.left, 0, stud_depth / 2, dimensions.left / 2, 0),
            "right": (dimensions.right, 180, dimensions.front - stud_depth / 2, dimensions.right / 2, 0)
        }
        
        for face in faces_to_build:
            length, rotation, trans_x, trans_y, trans_z = face_map[face]
            if length > 0:
                CorniceBuilder._build_face_cornice(
                    cornice,
                    face,
                    length,
                    crown_width,
                    crown_height,
                    crown_z_position + trans_z,
                    corona_z_position + trans_z,
                    fascia_height,
                    modillion_spacing,
                    bed_molding_height,
                    rotation,
                    trans_x,
                    trans_y
                )
        
        return cornice

    @staticmethod
    def _build_face_cornice(
        assembly: cq.Assembly,
        face: str,
        length: float,
        crown_width: float,
        crown_height: float,
        crown_z_position: float,
        corona_z_position: float,
        fascia_height: float,
        modillion_spacing: float,
        bed_molding_height: float,
        rotation: float,
        trans_x: float,
        trans_y: float
    ) -> None:
        """
        Build cornice components for a single face and add them to the assembly.
        
        Args:
            assembly: Assembly to add components to
            face: Face name ("front", "rear", "left", "right")
            length: Length of the face
            crown_width: Width of crown molding
            crown_height: Height of crown molding
            crown_z_position: Z position for crown molding
            corona_z_position: Z position for corona
            fascia_height: Height of fascia
            modillion_spacing: Spacing between modillions
            bed_molding_height: Height of bed molding
            rotation: Rotation angle in degrees around Z axis
            trans_x: X translation
            trans_y: Y translation
        """
        # Helper to apply rotation, flip, centering, and translation to a component
        # Components are built along Y axis (extrusion), need to:
        # 1. Center them by shifting -length/2 in the extrusion direction (Y before rotation)
        # 2. Rotate around Z to align with face
        # 3. Flip 180° around appropriate axis to face outward
        # 4. Translate to face position (preserving Z coordinate)
        def transform_component(component, z_pos):
            """Apply centering, rotation, flip, and translation to face position."""
            # Center the component (shift by -length/2 in Y since extrusion starts at origin)
            component = component.translate((0, length / 2, 0))
            
            # Rotate around Z to align with face orientation
            if rotation != 0:
                component = component.rotate((0, 0, 0), (0, 0, 1), rotation)
            
            # Flip to face outward (180° rotation around the face's horizontal axis)
            if face == "front":
                # Front face: flip around X axis to face +Y (outward)
                component = component.rotate((0, 0, 0), (1, 0, 0), 180)
            elif face == "rear":
                # Rear face: flip around X axis to face -Y (outward)
                component = component.rotate((0, 0, 0), (1, 0, 0), 180)
            elif face == "left":
                # Left face: flip around Y axis to face -X (outward)
                component = component.rotate((0, 0, 0), (0, 1, 0), 180)
            elif face == "right":
                # Right face: flip around Y axis to face +X (outward)
                component = component.rotate((0, 0, 0), (0, 1, 0), 180)
            
            # Translate to face position (preserve Z coordinate from original component)
            return component.translate((trans_x, trans_y, z_pos))
        
        # Crown - built along Y axis (extrusion), then transformed
        crown = CorniceBuilder._crown_molding(crown_width, crown_height).extrude(length).translate((4.25, 0, 0))
        crown = transform_component(crown, crown_z_position)
        assembly.add(crown, name=f"{face}_crown", color=cq.Color(0.8, 0.7, 0.6))
        
        # Corona - Cavetto (note: original code had rotateAboutCenter(180) which is part of the cavetto positioning)
        cavetto = CorniceBuilder._cavetto_board().extrude(length).translate((8, 0, 0)).rotateAboutCenter((0, 0, 1), 180)
        cavetto = transform_component(cavetto, corona_z_position)
        assembly.add(cavetto, name=f"{face}_cavetto", color=cq.Color(0.8, 0.7, 0.6))
        
        # Corona - Fascia
        fascia = cq.Workplane("XZ").rect(10, fascia_height).extrude(length).translate((14, 0, -0.8))
        fascia = transform_component(fascia, corona_z_position)
        assembly.add(fascia, name=f"{face}_fascia", color=cq.Color(0.8, 0.7, 0.6))
        
        # Modillion backing
        modillion_backing = cq.Workplane("XZ").rect(4.5, 0.75).extrude(length).translate((19, 0, -3.5)).rotateAboutCenter((0, 1, 0), 90)
        modillion_backing = transform_component(modillion_backing, corona_z_position)
        assembly.add(modillion_backing, name=f"{face}_modillion_backing", color=cq.Color(0.8, 0.7, 0.6))
        
        # Modillions
        modillion_count = math.floor(length / modillion_spacing)
        for modillion_idx in range(0, modillion_count):
            modillion_x = length - (modillion_idx * modillion_spacing)
            modillion = cq.Workplane("XZ").rect(5.5, 3.0).extrude(3).translate((16.25, -modillion_x + modillion_spacing, -4))
            modillion = transform_component(modillion, corona_z_position)
            assembly.add(modillion, name=f"{face}_modillion_{modillion_idx}", color=cq.Color(0.8, 0.7, 0.6))
            
            modillion_band = CorniceBuilder._cyma_reversa_band(7, 1).extrude(3).translate((12, -modillion_x + modillion_spacing, -1.5))
            modillion_band = transform_component(modillion_band, corona_z_position)
            assembly.add(modillion_band, name=f"{face}_modillion_band_{modillion_idx}", color=cq.Color(0.8, 0.7, 0.6))
        
        # Bedmold
        bed = CorniceBuilder._bed_molding(0.75, bed_molding_height).extrude(length).translate((18, 0, -bed_molding_height))
        bed = transform_component(bed, crown_z_position)
        assembly.add(bed, name=f"{face}_bed_molding", color=cq.Color(0.8, 0.7, 0.6))
