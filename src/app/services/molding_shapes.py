"""
Molding Shapes Library for CadQuery

This library provides functions to create common architectural molding shapes
using the CadQuery library. Each shape is designed to be configurable with
parameters for scale, proportions, and dimensions.

Author: AI Assistant
License: MIT
"""

import cadquery as cq
import math
from typing import Optional, Tuple, Union


class MoldingShapes:
    """
    A collection of common architectural molding shapes created with CadQuery.
    
    This class provides methods to generate various molding profiles including
    ovolo, bead, astragal, torus, cavetto, cyma recta, cyma reversa, scotia, 
    fillet, and other classical architectural molding shapes.
    """
    
    def __init__(self):
        """Initialize the MoldingShapes class."""
        pass
    
    @staticmethod
    def ovolo(
        width: float = 10.0,
        height: float = 5.0,
        length: float = 100.0,
        radius_ratio: float = 0.6,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create an ovolo molding shape.
        
        An ovolo is a convex molding with a quarter-circle or quarter-ellipse
        profile. It's one of the most common classical molding shapes.
        
        Args:
            width (float): The width (projection) of the molding in mm. Default: 10.0
            height (float): The height of the molding in mm. Default: 5.0
            length (float): The length of the molding in mm. Default: 100.0
            radius_ratio (float): Ratio of the curve radius to height (0.0-1.0). 
                                Default: 0.6 (creates a gentle curve)
            segments (int): Number of segments for the curve approximation. 
                          Higher values = smoother curve. Default: 32
            centered (bool): Whether to center the molding at origin. Default: True
            name (str, optional): Name for the object (for documentation purposes)
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the ovolo molding
            
        Example:
            >>> molding = MoldingShapes()
            >>> ovolo = molding.ovolo(width=15, height=8, length=200)
            >>> show_object(ovolo)
        """
        # Validate inputs
        if width <= 0 or height <= 0 or length <= 0:
            raise ValueError("Width, height, and length must be positive values")
        
        if not 0.0 <= radius_ratio <= 1.0:
            raise ValueError("Radius ratio must be between 0.0 and 1.0")
        
        if segments < 8:
            raise ValueError("Segments must be at least 8 for a reasonable curve")
        
        # Calculate the radius of the quarter-circle/ellipse
        # The radius is determined by the radius_ratio and the height
        radius = height * radius_ratio
        
        # Create the 2D profile of the ovolo
        # Start from the bottom-left corner and create a quarter-circle/ellipse
        profile_points = []
        
        # Add the starting point (bottom-left)
        profile_points.append((0, 0))
        
        # Generate points for the quarter-circle/ellipse
        for i in range(segments + 1):
            # Angle from 0 to π/2 (0 to 90 degrees)
            angle = (i / segments) * (math.pi / 2)
            
            # Calculate x and y coordinates
            # For a true quarter-circle, both x and y would use the same radius
            # For an ovolo, we can adjust the proportions
            x = radius * math.sin(angle)
            y = radius * math.cos(angle)
            
            # Scale to fit the desired height and width
            x_scaled = x * (width / radius)
            y_scaled = y * (height / radius)
            
            profile_points.append((x_scaled, y_scaled))
        
        # Add the end point (top-right)
        profile_points.append((width, height))
        
        # Create the 2D profile using CadQuery
        profile = cq.Workplane("XZ").polyline(profile_points).close()
        
        # Extrude the profile to create the 3D molding
        molding = profile.extrude(length)
        
        # Center the molding if requested
        if centered:
            molding = molding.translate((-width/2, -length/2, -height/2))
        
        return molding
    
    @staticmethod
    def ovolo_with_fillet(
        width: float = 10.0,
        height: float = 5.0,
        length: float = 100.0,
        radius_ratio: float = 0.6,
        fillet_radius: float = 1.0,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create an ovolo molding with filleted edges.
        
        This creates an ovolo shape with rounded edges for a softer appearance.
        
        Args:
            width (float): The width (projection) of the molding in mm. Default: 10.0
            height (float): The height of the molding in mm. Default: 5.0
            length (float): The length of the molding in mm. Default: 100.0
            radius_ratio (float): Ratio of the curve radius to height (0.0-1.0). 
                                Default: 0.6
            fillet_radius (float): Radius of the fillet on the edges. Default: 1.0
            segments (int): Number of segments for the curve approximation. Default: 32
            centered (bool): Whether to center the molding at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the filleted ovolo molding
        """
        # Create the base ovolo
        base_ovolo = MoldingShapes.ovolo(
            width=width,
            height=height,
            length=length,
            radius_ratio=radius_ratio,
            segments=segments,
            centered=False  # We'll center it later
        )
        
        # Apply fillets to the edges
        # Fillet the top and bottom edges
        filleted = base_ovolo.edges("|Z").fillet(fillet_radius)
        
        # Center if requested
        if centered:
            filleted = filleted.translate((-width/2, -length/2, -height/2))
        
        return filleted
    
    @staticmethod
    def ovolo_series(
        count: int = 3,
        width: float = 10.0,
        height: float = 5.0,
        length: float = 100.0,
        radius_ratio: float = 0.6,
        spacing: float = 2.0,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create a series of ovolo moldings arranged side by side.
        
        This is useful for creating repeating patterns or decorative elements.
        
        Args:
            count (int): Number of ovolo moldings to create. Default: 3
            width (float): Width of each individual molding. Default: 10.0
            height (float): Height of each individual molding. Default: 5.0
            length (float): Length of each molding. Default: 100.0
            radius_ratio (float): Radius ratio for each molding. Default: 0.6
            spacing (float): Spacing between moldings. Default: 2.0
            segments (int): Number of segments for curve approximation. Default: 32
            centered (bool): Whether to center the series at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the series of ovolo moldings
        """
        if count <= 0:
            raise ValueError("Count must be a positive integer")
        
        # Create the first ovolo
        first_ovolo = MoldingShapes.ovolo(
            width=width,
            height=height,
            length=length,
            radius_ratio=radius_ratio,
            segments=segments,
            centered=False
        )
        
        # Calculate total width for centering
        total_width = count * width + (count - 1) * spacing
        
        # Create additional ovolos and union them
        result = first_ovolo
        for i in range(1, count):
            # Calculate offset for this ovolo
            offset_x = i * (width + spacing)
            
            # Create and position the ovolo
            ovolo = MoldingShapes.ovolo(
                width=width,
                height=height,
                length=length,
                radius_ratio=radius_ratio,
                segments=segments,
                centered=False
            ).translate((offset_x, 0, 0))
            
            # Union with the result
            result = result.union(ovolo)
        
        # Center if requested
        if centered:
            result = result.translate((-total_width/2, -length/2, -height/2))
        
        return result
    
    @staticmethod
    def bead(
        diameter: float = 8.0,
        length: float = 100.0,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create a bead molding shape.
        
        A bead is a small, round molding that projects from a surface.
        It's typically used for decorative purposes and as a transition element.
        
        Args:
            diameter (float): The diameter of the bead in mm. Default: 8.0
            length (float): The length of the bead in mm. Default: 100.0
            segments (int): Number of segments for the circular profile. Default: 32
            centered (bool): Whether to center the bead at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the bead molding
        """
        if diameter <= 0 or length <= 0:
            raise ValueError("Diameter and length must be positive values")
        
        if segments < 8:
            raise ValueError("Segments must be at least 8 for a reasonable circle")
        
        # Create a cylinder for the bead
        bead = cq.Workplane("XY").cylinder(length, diameter/2)
        
        # Center if requested
        if centered:
            bead = bead.translate((0, 0, -length/2))
        
        return bead
    
    @staticmethod
    def astragal(
        width: float = 6.0,
        height: float = 6.0,
        length: float = 100.0,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create an astragal molding shape.
        
        An astragal is a small convex molding, typically semicircular in profile.
        It's often used as a transition between different architectural elements.
        
        Args:
            width (float): The width of the astragal in mm. Default: 6.0
            height (float): The height of the astragal in mm. Default: 6.0
            length (float): The length of the astragal in mm. Default: 100.0
            segments (int): Number of segments for the semicircular profile. Default: 32
            centered (bool): Whether to center the astragal at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the astragal molding
        """
        if width <= 0 or height <= 0 or length <= 0:
            raise ValueError("Width, height, and length must be positive values")
        
        if segments < 8:
            raise ValueError("Segments must be at least 8 for a reasonable curve")
        
        # Create the semicircular profile
        radius = min(width, height) / 2
        profile_points = []
        
        # Start from the bottom center
        profile_points.append((0, 0))
        
        # Generate points for the semicircle
        for i in range(segments + 1):
            angle = (i / segments) * math.pi  # 0 to π (180 degrees)
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            # Scale to fit the desired dimensions
            x_scaled = x * (width / (2 * radius))
            y_scaled = y * (height / (2 * radius))
            
            profile_points.append((x_scaled, y_scaled))
        
        # Add the end point
        profile_points.append((0, 0))
        
        # Create the 2D profile
        profile = cq.Workplane("XZ").polyline(profile_points).close()
        
        # Extrude to create the 3D molding
        astragal = profile.extrude(length)
        
        # Center if requested
        if centered:
            astragal = astragal.translate((-width/2, -length/2, -height/2))
        
        return astragal
    
    @staticmethod
    def torus(
        major_radius: float = 15.0,
        minor_radius: float = 5.0,
        length: float = 100.0,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create a torus molding shape.
        
        A torus is a doughnut-shaped molding with a circular cross-section.
        It's used for decorative purposes and as a prominent architectural element.
        
        Args:
            major_radius (float): The major radius (center to center of tube) in mm. Default: 15.0
            minor_radius (float): The minor radius (radius of the tube) in mm. Default: 5.0
            length (float): The length of the torus in mm. Default: 100.0
            segments (int): Number of segments for the circular profiles. Default: 32
            centered (bool): Whether to center the torus at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the torus molding
        """
        if major_radius <= 0 or minor_radius <= 0 or length <= 0:
            raise ValueError("Major radius, minor radius, and length must be positive values")
        
        if minor_radius >= major_radius:
            raise ValueError("Minor radius must be less than major radius")
        
        if segments < 8:
            raise ValueError("Segments must be at least 8 for a reasonable circle")
        
        # Create a torus by revolving a circle around an axis
        # First, create a circle at the major radius distance
        circle_center = (major_radius, 0, 0)
        
        # Create the torus by revolving a circle
        torus = cq.Workplane("XY").workplane(offset=0).center(circle_center[0], circle_center[1]).circle(minor_radius).revolve(360, (0, 0, 0), (0, 0, 1))
        
        # Extrude to the desired length
        torus = torus.extrude(length)
        
        # Center if requested
        if centered:
            torus = torus.translate((0, -length/2, 0))
        
        return torus
    
    @staticmethod
    def cavetto(
        width: float = 10.0,
        height: float = 5.0,
        length: float = 100.0,
        radius_ratio: float = 0.6,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create a cavetto molding shape.
        
        A cavetto is a concave molding with a quarter-circle or quarter-ellipse
        profile. It's the opposite of an ovolo and creates a recessed effect.
        
        Args:
            width (float): The width (projection) of the molding in mm. Default: 10.0
            height (float): The height of the molding in mm. Default: 5.0
            length (float): The length of the molding in mm. Default: 100.0
            radius_ratio (float): Ratio of the curve radius to height (0.0-1.0). 
                                Default: 0.6 (creates a gentle curve)
            segments (int): Number of segments for the curve approximation. Default: 32
            centered (bool): Whether to center the molding at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the cavetto molding
        """
        if width <= 0 or height <= 0 or length <= 0:
            raise ValueError("Width, height, and length must be positive values")
        
        if not 0.0 <= radius_ratio <= 1.0:
            raise ValueError("Radius ratio must be between 0.0 and 1.0")
        
        if segments < 8:
            raise ValueError("Segments must be at least 8 for a reasonable curve")
        
        # Calculate the radius of the quarter-circle/ellipse
        radius = height * radius_ratio
        
        # Create the 2D profile of the cavetto (concave version of ovolo)
        profile_points = []
        
        # Add the starting point (bottom-left)
        profile_points.append((0, 0))
        
        # Generate points for the quarter-circle/ellipse (concave)
        for i in range(segments + 1):
            # Angle from π/2 to 0 (90 to 0 degrees) for concave curve
            angle = (math.pi / 2) - (i / segments) * (math.pi / 2)
            
            # Calculate x and y coordinates
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            # Scale to fit the desired height and width
            x_scaled = x * (width / radius)
            y_scaled = y * (height / radius)
            
            profile_points.append((x_scaled, y_scaled))
        
        # Add the end point (top-right)
        profile_points.append((width, height))
        
        # Create the 2D profile using CadQuery
        profile = cq.Workplane("XZ").polyline(profile_points).close()
        
        # Extrude the profile to create the 3D molding
        molding = profile.extrude(length)
        
        # Center the molding if requested
        if centered:
            molding = molding.translate((-width/2, -length/2, -height/2))
        
        return molding
    
    @staticmethod
    def cyma_recta(
        width: float = 12.0,
        height: float = 8.0,
        length: float = 100.0,
        convex_ratio: float = 0.4,
        concave_ratio: float = 0.4,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create a cyma recta molding shape.
        
        A cyma recta is an S-shaped molding with a convex curve at the top
        and a concave curve at the bottom. It's a classic classical molding.
        
        Args:
            width (float): The width (projection) of the molding in mm. Default: 12.0
            height (float): The height of the molding in mm. Default: 8.0
            length (float): The length of the molding in mm. Default: 100.0
            convex_ratio (float): Ratio for the convex curve (0.0-1.0). Default: 0.4
            concave_ratio (float): Ratio for the concave curve (0.0-1.0). Default: 0.4
            segments (int): Number of segments for curve approximation. Default: 32
            centered (bool): Whether to center the molding at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the cyma recta molding
        """
        if width <= 0 or height <= 0 or length <= 0:
            raise ValueError("Width, height, and length must be positive values")
        
        if not 0.0 <= convex_ratio <= 1.0 or not 0.0 <= concave_ratio <= 1.0:
            raise ValueError("Convex and concave ratios must be between 0.0 and 1.0")
        
        if segments < 8:
            raise ValueError("Segments must be at least 8 for a reasonable curve")
        
        # Calculate radii for both curves
        convex_radius = height * convex_ratio
        concave_radius = height * concave_ratio
        
        # Create the S-shaped profile
        profile_points = []
        
        # Start from the bottom-left
        profile_points.append((0, 0))
        
        # Generate points for the concave curve (bottom part)
        concave_segments = segments // 2
        for i in range(concave_segments + 1):
            # Angle from π/2 to 0 (90 to 0 degrees)
            angle = (math.pi / 2) - (i / concave_segments) * (math.pi / 2)
            
            x = concave_radius * math.cos(angle)
            y = concave_radius * math.sin(angle)
            
            # Scale and position
            x_scaled = x * (width / (2 * concave_radius))
            y_scaled = y * (height / (2 * concave_radius))
            
            profile_points.append((x_scaled, y_scaled))
        
        # Generate points for the convex curve (top part)
        convex_segments = segments - concave_segments
        for i in range(1, convex_segments + 1):
            # Angle from 0 to π/2 (0 to 90 degrees)
            angle = (i / convex_segments) * (math.pi / 2)
            
            x = convex_radius * math.sin(angle)
            y = convex_radius * math.cos(angle)
            
            # Scale and position (offset by the concave part)
            x_scaled = x * (width / (2 * convex_radius)) + width/2
            y_scaled = y * (height / (2 * convex_radius)) + height/2
            
            profile_points.append((x_scaled, y_scaled))
        
        # Add the end point (top-right)
        profile_points.append((width, height))
        
        # Create the 2D profile
        profile = cq.Workplane("XZ").polyline(profile_points).close()
        
        # Extrude to create the 3D molding
        molding = profile.extrude(length)
        
        # Center if requested
        if centered:
            molding = molding.translate((-width/2, -length/2, -height/2))
        
        return molding
    
    @staticmethod
    def cyma_reversa(
        width: float = 12.0,
        height: float = 8.0,
        length: float = 100.0,
        convex_ratio: float = 0.4,
        concave_ratio: float = 0.4,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create a cyma reversa molding shape.
        
        A cyma reversa is an S-shaped molding with a concave curve at the top
        and a convex curve at the bottom. It's the reverse of cyma recta.
        
        Args:
            width (float): The width (projection) of the molding in mm. Default: 12.0
            height (float): The height of the molding in mm. Default: 8.0
            length (float): The length of the molding in mm. Default: 100.0
            convex_ratio (float): Ratio for the convex curve (0.0-1.0). Default: 0.4
            concave_ratio (float): Ratio for the concave curve (0.0-1.0). Default: 0.4
            segments (int): Number of segments for curve approximation. Default: 32
            centered (bool): Whether to center the molding at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the cyma reversa molding
        """
        if width <= 0 or height <= 0 or length <= 0:
            raise ValueError("Width, height, and length must be positive values")
        
        if not 0.0 <= convex_ratio <= 1.0 or not 0.0 <= concave_ratio <= 1.0:
            raise ValueError("Convex and concave ratios must be between 0.0 and 1.0")
        
        if segments < 8:
            raise ValueError("Segments must be at least 8 for a reasonable curve")
        
        # Calculate radii for both curves
        convex_radius = height * convex_ratio
        concave_radius = height * concave_ratio
        
        # Create the reverse S-shaped profile
        profile_points = []
        
        # Start from the bottom-left
        profile_points.append((0, 0))
        
        # Generate points for the convex curve (bottom part)
        convex_segments = segments // 2
        for i in range(convex_segments + 1):
            # Angle from 0 to π/2 (0 to 90 degrees)
            angle = (i / convex_segments) * (math.pi / 2)
            
            x = convex_radius * math.sin(angle)
            y = convex_radius * math.cos(angle)
            
            # Scale and position
            x_scaled = x * (width / (2 * convex_radius))
            y_scaled = y * (height / (2 * convex_radius))
            
            profile_points.append((x_scaled, y_scaled))
        
        # Generate points for the concave curve (top part)
        concave_segments = segments - convex_segments
        for i in range(1, concave_segments + 1):
            # Angle from π/2 to 0 (90 to 0 degrees)
            angle = (math.pi / 2) - (i / concave_segments) * (math.pi / 2)
            
            x = concave_radius * math.cos(angle)
            y = concave_radius * math.sin(angle)
            
            # Scale and position (offset by the convex part)
            x_scaled = x * (width / (2 * concave_radius)) + width/2
            y_scaled = y * (height / (2 * concave_radius)) + height/2
            
            profile_points.append((x_scaled, y_scaled))
        
        # Add the end point (top-right)
        profile_points.append((width, height))
        
        # Create the 2D profile
        profile = cq.Workplane("XZ").polyline(profile_points).close()
        
        # Extrude to create the 3D molding
        molding = profile.extrude(length)
        
        # Center if requested
        if centered:
            molding = molding.translate((-width/2, -length/2, -height/2))
        
        return molding
    
    @staticmethod
    def scotia(
        width: float = 12.0,
        height: float = 8.0,
        length: float = 100.0,
        depth_ratio: float = 0.7,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create a scotia molding shape.
        
        A scotia is a deep concave molding with a more pronounced curve than a cavetto.
        It's typically used in classical architecture for shadow effects and transitions.
        
        Args:
            width (float): The width (projection) of the molding in mm. Default: 12.0
            height (float): The height of the molding in mm. Default: 8.0
            length (float): The length of the molding in mm. Default: 100.0
            depth_ratio (float): Ratio controlling the depth of the concave curve (0.0-1.0). 
                               Default: 0.7 (creates a deep, pronounced curve)
            segments (int): Number of segments for the curve approximation. Default: 32
            centered (bool): Whether to center the molding at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the scotia molding
        """
        if width <= 0 or height <= 0 or length <= 0:
            raise ValueError("Width, height, and length must be positive values")
        
        if not 0.0 <= depth_ratio <= 1.0:
            raise ValueError("Depth ratio must be between 0.0 and 1.0")
        
        if segments < 8:
            raise ValueError("Segments must be at least 8 for a reasonable curve")
        
        # Calculate the radius for the deep concave curve
        # For scotia, we use a larger radius to create a deeper, more pronounced curve
        radius = height * depth_ratio * 1.5  # Deeper than cavetto
        
        # Create the 2D profile of the scotia (deep concave curve)
        profile_points = []
        
        # Add the starting point (bottom-left)
        profile_points.append((0, 0))
        
        # Generate points for the deep concave curve
        for i in range(segments + 1):
            # Angle from π/2 to 0 (90 to 0 degrees) for concave curve
            angle = (math.pi / 2) - (i / segments) * (math.pi / 2)
            
            # Calculate x and y coordinates
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            # Scale to fit the desired height and width
            # For scotia, we want the curve to extend deeper into the surface
            x_scaled = x * (width / radius)
            y_scaled = y * (height / radius)
            
            profile_points.append((x_scaled, y_scaled))
        
        # Add the end point (top-right)
        profile_points.append((width, height))
        
        # Create the 2D profile using CadQuery
        profile = cq.Workplane("XZ").polyline(profile_points).close()
        
        # Extrude the profile to create the 3D molding
        molding = profile.extrude(length)
        
        # Center the molding if requested
        if centered:
            molding = molding.translate((-width/2, -length/2, -height/2))
        
        return molding
    
    @staticmethod
    def fillet(
        width: float = 4.0,
        height: float = 4.0,
        length: float = 100.0,
        radius_ratio: float = 0.8,
        segments: int = 32,
        centered: bool = True,
        name: Optional[str] = None
    ) -> cq.Workplane:
        """
        Create a fillet molding shape.
        
        A fillet is a small convex molding, typically used as a transition element
        or to soften edges. It's smaller and more subtle than an ovolo.
        
        Args:
            width (float): The width (projection) of the molding in mm. Default: 4.0
            height (float): The height of the molding in mm. Default: 4.0
            length (float): The length of the molding in mm. Default: 100.0
            radius_ratio (float): Ratio of the curve radius to height (0.0-1.0). 
                                Default: 0.8 (creates a gentle, subtle curve)
            segments (int): Number of segments for the curve approximation. Default: 32
            centered (bool): Whether to center the molding at origin. Default: True
            name (str, optional): Name for the object
        
        Returns:
            cq.Workplane: A CadQuery workplane containing the fillet molding
        """
        if width <= 0 or height <= 0 or length <= 0:
            raise ValueError("Width, height, and length must be positive values")
        
        if not 0.0 <= radius_ratio <= 1.0:
            raise ValueError("Radius ratio must be between 0.0 and 1.0")
        
        if segments < 8:
            raise ValueError("Segments must be at least 8 for a reasonable curve")
        
        # Calculate the radius of the quarter-circle/ellipse
        # For fillet, we use a gentle curve (higher radius_ratio)
        radius = height * radius_ratio
        
        # Create the 2D profile of the fillet (small convex curve)
        profile_points = []
        
        # Add the starting point (bottom-left)
        profile_points.append((0, 0))
        
        # Generate points for the quarter-circle/ellipse
        for i in range(segments + 1):
            # Angle from 0 to π/2 (0 to 90 degrees)
            angle = (i / segments) * (math.pi / 2)
            
            # Calculate x and y coordinates
            x = radius * math.sin(angle)
            y = radius * math.cos(angle)
            
            # Scale to fit the desired height and width
            x_scaled = x * (width / radius)
            y_scaled = y * (height / radius)
            
            profile_points.append((x_scaled, y_scaled))
        
        # Add the end point (top-right)
        profile_points.append((width, height))
        
        # Create the 2D profile using CadQuery
        profile = cq.Workplane("XZ").polyline(profile_points).close()
        
        # Extrude the profile to create the 3D molding
        molding = profile.extrude(length)
        
        # Center the molding if requested
        if centered:
            molding = molding.translate((-width/2, -length/2, -height/2))
        
        return molding


class CompositeMolding:
    """
    A class for creating composite molding profiles by combining multiple
    individual molding shapes into classical architectural arrangements.
    """
    
    def __init__(self, name: str = "composite_molding"):
        """Initialize the composite molding builder."""
        self.name = name
        self.elements = []
        self.total_height = 0
        self.total_width = 0
        self.current_z_offset = 0
    
    def add_element(self, molding_type: str, **kwargs) -> 'CompositeMolding':
        """
        Add a molding element to the composite profile.
        
        Args:
            molding_type (str): Type of molding to add (ovolo, scotia, fillet, etc.)
            **kwargs: Parameters for the specific molding type
        
        Returns:
            CompositeMolding: Self for method chaining
        """
        # Get the appropriate creation function
        creation_functions = {
            'ovolo': MoldingShapes.ovolo,
            'ovolo_with_fillet': MoldingShapes.ovolo_with_fillet,
            'bead': MoldingShapes.bead,
            'astragal': MoldingShapes.astragal,
            'torus': MoldingShapes.torus,
            'cavetto': MoldingShapes.cavetto,
            'cyma_recta': MoldingShapes.cyma_recta,
            'cyma_reversa': MoldingShapes.cyma_reversa,
            'scotia': MoldingShapes.scotia,
            'fillet': MoldingShapes.fillet
        }
        
        if molding_type not in creation_functions:
            raise ValueError(f"Unknown molding type: {molding_type}")
        
        # Set default parameters
        element_params = kwargs.copy()
        if 'centered' not in element_params:
            element_params['centered'] = False  # We'll position manually
        
        # Create the molding element
        element = creation_functions[molding_type](**element_params)
        
        # Calculate dimensions
        width = element_params.get('width', element_params.get('diameter', 10))
        height = element_params.get('height', element_params.get('diameter', 10))
        
        # For torus, use major_radius * 2 as width
        if molding_type == 'torus':
            width = element_params.get('major_radius', 15) * 2
        
        # Store element information
        element_info = {
            'type': molding_type,
            'element': element,
            'width': width,
            'height': height,
            'z_offset': self.current_z_offset,
            'params': element_params
        }
        
        self.elements.append(element_info)
        
        # Update total dimensions
        self.total_width = max(self.total_width, width)
        self.total_height += height
        
        # Update z offset for next element
        self.current_z_offset += height
        
        return self
    
    def build(self, length: float = 100.0) -> cq.Workplane:
        """
        Build the complete composite molding.
        
        Args:
            length (float): Length of the composite molding
        
        Returns:
            cq.Workplane: Complete composite molding
        """
        if not self.elements:
            raise ValueError("No elements added to composite molding")
        
        # Start with the first element
        result = self.elements[0]['element'].translate((0, 0, self.elements[0]['z_offset']))
        
        # Add remaining elements
        for element_info in self.elements[1:]:
            positioned_element = element_info['element'].translate((0, 0, element_info['z_offset']))
            result = result.union(positioned_element)
        
        # Center the result
        result = result.translate((-self.total_width/2, -length/2, -self.total_height/2))
        
        return result
    
    def get_dimensions(self) -> dict:
        """
        Get the total dimensions of the composite molding.
        
        Returns:
            dict: Dictionary with width, height, and element count
        """
        return {
            'width': self.total_width,
            'height': self.total_height,
            'element_count': len(self.elements),
            'elements': [elem['type'] for elem in self.elements]
        }


class ClassicalProfiles:
    """Pre-defined classical architectural molding profiles."""
    
    @staticmethod
    def doric_base(length: float = 100.0) -> cq.Workplane:
        """Create a Doric order base molding profile."""
        return CompositeMolding("doric_base") \
            .add_element("scotia", width=12, height=6, depth_ratio=0.8) \
            .add_element("fillet", width=3, height=3, radius_ratio=0.8) \
            .add_element("torus", major_radius=8, minor_radius=3) \
            .add_element("fillet", width=3, height=3, radius_ratio=0.8) \
            .add_element("astragal", width=6, height=6) \
            .build(length)
    
    @staticmethod
    def ionic_base(length: float = 100.0) -> cq.Workplane:
        """Create an Ionic order base molding profile."""
        return CompositeMolding("ionic_base") \
            .add_element("scotia", width=14, height=8, depth_ratio=0.7) \
            .add_element("fillet", width=4, height=4, radius_ratio=0.8) \
            .add_element("torus", major_radius=10, minor_radius=4) \
            .add_element("fillet", width=4, height=4, radius_ratio=0.8) \
            .add_element("ovolo", width=12, height=6, radius_ratio=0.6) \
            .add_element("fillet", width=3, height=3, radius_ratio=0.8) \
            .add_element("astragal", width=8, height=8) \
            .build(length)
    
    @staticmethod
    def corinthian_capital(length: float = 100.0) -> cq.Workplane:
        """Create a Corinthian capital molding profile."""
        return CompositeMolding("corinthian_capital") \
            .add_element("astragal", width=10, height=10) \
            .add_element("fillet", width=4, height=4, radius_ratio=0.8) \
            .add_element("ovolo", width=16, height=8, radius_ratio=0.7) \
            .add_element("cyma_recta", width=18, height=10, convex_ratio=0.5, concave_ratio=0.5) \
            .add_element("bead", diameter=8) \
            .add_element("cyma_reversa", width=16, height=8, convex_ratio=0.4, concave_ratio=0.4) \
            .build(length)
    
    @staticmethod
    def crown_molding(length: float = 100.0) -> cq.Workplane:
        """Create a traditional crown molding profile."""
        return CompositeMolding("crown_molding") \
            .add_element("cavetto", width=8, height=4, radius_ratio=0.6) \
            .add_element("fillet", width=2, height=2, radius_ratio=0.8) \
            .add_element("ovolo", width=12, height=6, radius_ratio=0.7) \
            .add_element("cyma_recta", width=14, height=8, convex_ratio=0.5, concave_ratio=0.5) \
            .add_element("bead", diameter=6) \
            .build(length)
    
    @staticmethod
    def base_molding(length: float = 100.0) -> cq.Workplane:
        """Create a traditional base molding profile."""
        return CompositeMolding("base_molding") \
            .add_element("torus", major_radius=12, minor_radius=4) \
            .add_element("fillet", width=3, height=3, radius_ratio=0.8) \
            .add_element("scotia", width=10, height=6, depth_ratio=0.7) \
            .add_element("fillet", width=3, height=3, radius_ratio=0.8) \
            .add_element("astragal", width=8, height=8) \
            .build(length)
    
    @staticmethod
    def doric_capital(length: float = 100.0) -> cq.Workplane:
        """Create a Doric capital molding profile."""
        return CompositeMolding("doric_capital") \
            .add_element("astragal", width=8, height=8) \
            .add_element("fillet", width=3, height=3, radius_ratio=0.8) \
            .add_element("ovolo", width=12, height=6, radius_ratio=0.6) \
            .add_element("cyma_recta", width=14, height=8, convex_ratio=0.4, concave_ratio=0.4) \
            .build(length)
    
    @staticmethod
    def ionic_capital(length: float = 100.0) -> cq.Workplane:
        """Create an Ionic capital molding profile."""
        return CompositeMolding("ionic_capital") \
            .add_element("astragal", width=10, height=10) \
            .add_element("fillet", width=4, height=4, radius_ratio=0.8) \
            .add_element("ovolo", width=14, height=7, radius_ratio=0.7) \
            .add_element("cyma_recta", width=16, height=9, convex_ratio=0.5, concave_ratio=0.5) \
            .add_element("bead", diameter=6) \
            .build(length)


class CustomComposite:
    """Builder for custom composite molding profiles."""
    
    def __init__(self):
        """Initialize the custom composite builder."""
        self.composite = CompositeMolding("custom")
    
    def scotia(self, width: float = 12.0, height: float = 8.0, 
               depth_ratio: float = 0.7, **kwargs) -> 'CustomComposite':
        """Add a scotia element."""
        self.composite.add_element("scotia", width=width, height=height, 
                                 depth_ratio=depth_ratio, **kwargs)
        return self
    
    def fillet(self, width: float = 4.0, height: float = 4.0, 
               radius_ratio: float = 0.8, **kwargs) -> 'CustomComposite':
        """Add a fillet element."""
        self.composite.add_element("fillet", width=width, height=height, 
                                 radius_ratio=radius_ratio, **kwargs)
        return self
    
    def ovolo(self, width: float = 10.0, height: float = 5.0, 
              radius_ratio: float = 0.6, **kwargs) -> 'CustomComposite':
        """Add an ovolo element."""
        self.composite.add_element("ovolo", width=width, height=height, 
                                 radius_ratio=radius_ratio, **kwargs)
        return self
    
    def cavetto(self, width: float = 10.0, height: float = 5.0, 
                radius_ratio: float = 0.6, **kwargs) -> 'CustomComposite':
        """Add a cavetto element."""
        self.composite.add_element("cavetto", width=width, height=height, 
                                 radius_ratio=radius_ratio, **kwargs)
        return self
    
    def cyma_recta(self, width: float = 12.0, height: float = 8.0, 
                   convex_ratio: float = 0.4, concave_ratio: float = 0.4, 
                   **kwargs) -> 'CustomComposite':
        """Add a cyma recta element."""
        self.composite.add_element("cyma_recta", width=width, height=height, 
                                 convex_ratio=convex_ratio, concave_ratio=concave_ratio, **kwargs)
        return self
    
    def cyma_reversa(self, width: float = 12.0, height: float = 8.0, 
                     convex_ratio: float = 0.4, concave_ratio: float = 0.4, 
                     **kwargs) -> 'CustomComposite':
        """Add a cyma reversa element."""
        self.composite.add_element("cyma_reversa", width=width, height=height, 
                                 convex_ratio=convex_ratio, concave_ratio=concave_ratio, **kwargs)
        return self
    
    def astragal(self, width: float = 6.0, height: float = 6.0, **kwargs) -> 'CustomComposite':
        """Add an astragal element."""
        self.composite.add_element("astragal", width=width, height=height, **kwargs)
        return self
    
    def torus(self, major_radius: float = 15.0, minor_radius: float = 5.0, **kwargs) -> 'CustomComposite':
        """Add a torus element."""
        self.composite.add_element("torus", major_radius=major_radius, minor_radius=minor_radius, **kwargs)
        return self
    
    def bead(self, diameter: float = 8.0, **kwargs) -> 'CustomComposite':
        """Add a bead element."""
        self.composite.add_element("bead", diameter=diameter, **kwargs)
        return self
    
    def build(self, length: float = 100.0) -> cq.Workplane:
        """Build the custom composite molding."""
        return self.composite.build(length)
    
    def get_dimensions(self) -> dict:
        """Get the total dimensions of the custom composite."""
        return self.composite.get_dimensions()


class AdvancedComposite:
    """Advanced composite molding features."""
    
    @staticmethod
    def create_series(profile_func, count: int = 3, spacing: float = 2.0, 
                     length: float = 100.0) -> cq.Workplane:
        """
        Create a series of composite moldings.
        
        Args:
            profile_func: Function that creates a composite profile
            count (int): Number of profiles to create
            spacing (float): Spacing between profiles
            length (float): Length of each profile
        
        Returns:
            cq.Workplane: Combined series of profiles
        """
        if count <= 0:
            raise ValueError("Count must be a positive integer")
        
        # Create the first profile
        first_profile = profile_func(length)
        result = first_profile
        
        # Get dimensions for spacing calculation
        composite = CompositeMolding()
        # We need to determine the width from the profile function
        # For now, we'll use a reasonable default
        profile_width = 20  # This could be improved by analyzing the profile
        
        # Create additional profiles
        for i in range(1, count):
            profile = profile_func(length)
            offset_x = i * (profile_width + spacing)
            positioned_profile = profile.translate((offset_x, 0, 0))
            result = result.union(positioned_profile)
        
        return result
    
    @staticmethod
    def create_mirrored(profile_func, length: float = 100.0) -> cq.Workplane:
        """
        Create a mirrored version of a profile.
        
        Args:
            profile_func: Function that creates a composite profile
            length (float): Length of the profile
        
        Returns:
            cq.Workplane: Original and mirrored profiles combined
        """
        original = profile_func(length)
        mirrored = original.mirror("XZ")
        
        # Position them side by side
        mirrored = mirrored.translate((40, 0, 0))
        
        return original.union(mirrored)
    
    @staticmethod
    def scale_profile(profile: cq.Workplane, scale_factor: float) -> cq.Workplane:
        """
        Scale an entire composite profile.
        
        Args:
            profile (cq.Workplane): The profile to scale
            scale_factor (float): Scale factor (1.0 = no change)
        
        Returns:
            cq.Workplane: Scaled profile
        """
        if scale_factor <= 0:
            raise ValueError("Scale factor must be positive")
        
        return profile.scale(scale_factor)


class ProfileLibrary:
    """Library of historical and regional molding profiles."""
    
    @staticmethod
    def georgian_crown(length: float = 100.0) -> cq.Workplane:
        """Georgian period crown molding."""
        return CompositeMolding("georgian_crown") \
            .add_element("cavetto", width=6, height=3, radius_ratio=0.6) \
            .add_element("fillet", width=2, height=2, radius_ratio=0.8) \
            .add_element("ovolo", width=10, height=5, radius_ratio=0.7) \
            .add_element("cyma_recta", width=12, height=7, convex_ratio=0.5, concave_ratio=0.5) \
            .add_element("bead", diameter=5) \
            .build(length)
    
    @staticmethod
    def victorian_base(length: float = 100.0) -> cq.Workplane:
        """Victorian period base molding."""
        return CompositeMolding("victorian_base") \
            .add_element("torus", major_radius=15, minor_radius=5) \
            .add_element("fillet", width=4, height=4, radius_ratio=0.8) \
            .add_element("scotia", width=12, height=8, depth_ratio=0.8) \
            .add_element("fillet", width=4, height=4, radius_ratio=0.8) \
            .add_element("ovolo", width=14, height=7, radius_ratio=0.7) \
            .add_element("astragal", width=10, height=10) \
            .build(length)
    
    @staticmethod
    def art_deco_profile(length: float = 100.0) -> cq.Workplane:
        """Art Deco style molding profile."""
        return CompositeMolding("art_deco") \
            .add_element("fillet", width=2, height=2, radius_ratio=0.9) \
            .add_element("ovolo", width=8, height=4, radius_ratio=0.8) \
            .add_element("fillet", width=2, height=2, radius_ratio=0.9) \
            .add_element("cyma_recta", width=10, height=6, convex_ratio=0.6, concave_ratio=0.6) \
            .add_element("fillet", width=2, height=2, radius_ratio=0.9) \
            .build(length)
    
    @staticmethod
    def modern_minimal(length: float = 100.0) -> cq.Workplane:
        """Modern minimalist molding profile."""
        return CompositeMolding("modern_minimal") \
            .add_element("fillet", width=3, height=3, radius_ratio=0.9) \
            .add_element("ovolo", width=6, height=3, radius_ratio=0.8) \
            .add_element("fillet", width=3, height=3, radius_ratio=0.9) \
            .build(length)


# Convenience functions for direct access
def create_ovolo(
    width: float = 10.0,
    height: float = 5.0,
    length: float = 100.0,
    radius_ratio: float = 0.6,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create an ovolo molding.
    
    This is a direct wrapper around MoldingShapes.ovolo() for easier access.
    
    Args:
        width (float): The width (projection) of the molding in mm. Default: 10.0
        height (float): The height of the molding in mm. Default: 5.0
        length (float): The length of the molding in mm. Default: 100.0
        radius_ratio (float): Ratio of the curve radius to height (0.0-1.0). Default: 0.6
        segments (int): Number of segments for the curve approximation. Default: 32
        centered (bool): Whether to center the molding at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the ovolo molding
    """
    return MoldingShapes.ovolo(
        width=width,
        height=height,
        length=length,
        radius_ratio=radius_ratio,
        segments=segments,
        centered=centered,
        name=name
    )


def create_ovolo_with_fillet(
    width: float = 10.0,
    height: float = 5.0,
    length: float = 100.0,
    radius_ratio: float = 0.6,
    fillet_radius: float = 1.0,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create a filleted ovolo molding.
    
    Args:
        width (float): The width (projection) of the molding in mm. Default: 10.0
        height (float): The height of the molding in mm. Default: 5.0
        length (float): The length of the molding in mm. Default: 100.0
        radius_ratio (float): Ratio of the curve radius to height (0.0-1.0). Default: 0.6
        fillet_radius (float): Radius of the fillet on the edges. Default: 1.0
        segments (int): Number of segments for the curve approximation. Default: 32
        centered (bool): Whether to center the molding at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the filleted ovolo molding
    """
    return MoldingShapes.ovolo_with_fillet(
        width=width,
        height=height,
        length=length,
        radius_ratio=radius_ratio,
        fillet_radius=fillet_radius,
        segments=segments,
        centered=centered,
        name=name
    )


def create_ovolo_series(
    count: int = 3,
    width: float = 10.0,
    height: float = 5.0,
    length: float = 100.0,
    radius_ratio: float = 0.6,
    spacing: float = 2.0,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create a series of ovolo moldings.
    
    Args:
        count (int): Number of ovolo moldings to create. Default: 3
        width (float): Width of each individual molding. Default: 10.0
        height (float): Height of each individual molding. Default: 5.0
        length (float): Length of each molding. Default: 100.0
        radius_ratio (float): Radius ratio for each molding. Default: 0.6
        spacing (float): Spacing between moldings. Default: 2.0
        segments (int): Number of segments for curve approximation. Default: 32
        centered (bool): Whether to center the series at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the series of ovolo moldings
    """
    return MoldingShapes.ovolo_series(
        count=count,
        width=width,
        height=height,
        length=length,
        radius_ratio=radius_ratio,
        spacing=spacing,
        segments=segments,
        centered=centered,
        name=name
    )


def create_bead(
    diameter: float = 8.0,
    length: float = 100.0,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create a bead molding.
    
    Args:
        diameter (float): The diameter of the bead in mm. Default: 8.0
        length (float): The length of the bead in mm. Default: 100.0
        segments (int): Number of segments for the circular profile. Default: 32
        centered (bool): Whether to center the bead at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the bead molding
    """
    return MoldingShapes.bead(
        diameter=diameter,
        length=length,
        segments=segments,
        centered=centered,
        name=name
    )


def create_astragal(
    width: float = 6.0,
    height: float = 6.0,
    length: float = 100.0,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create an astragal molding.
    
    Args:
        width (float): The width of the astragal in mm. Default: 6.0
        height (float): The height of the astragal in mm. Default: 6.0
        length (float): The length of the astragal in mm. Default: 100.0
        segments (int): Number of segments for the semicircular profile. Default: 32
        centered (bool): Whether to center the astragal at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the astragal molding
    """
    return MoldingShapes.astragal(
        width=width,
        height=height,
        length=length,
        segments=segments,
        centered=centered,
        name=name
    )


def create_torus(
    major_radius: float = 15.0,
    minor_radius: float = 5.0,
    length: float = 100.0,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create a torus molding.
    
    Args:
        major_radius (float): The major radius (center to center of tube) in mm. Default: 15.0
        minor_radius (float): The minor radius (radius of the tube) in mm. Default: 5.0
        length (float): The length of the torus in mm. Default: 100.0
        segments (int): Number of segments for the circular profiles. Default: 32
        centered (bool): Whether to center the torus at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the torus molding
    """
    return MoldingShapes.torus(
        major_radius=major_radius,
        minor_radius=minor_radius,
        length=length,
        segments=segments,
        centered=centered,
        name=name
    )


def create_cavetto(
    width: float = 10.0,
    height: float = 5.0,
    length: float = 100.0,
    radius_ratio: float = 0.6,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create a cavetto molding.
    
    Args:
        width (float): The width (projection) of the molding in mm. Default: 10.0
        height (float): The height of the molding in mm. Default: 5.0
        length (float): The length of the molding in mm. Default: 100.0
        radius_ratio (float): Ratio of the curve radius to height (0.0-1.0). Default: 0.6
        segments (int): Number of segments for the curve approximation. Default: 32
        centered (bool): Whether to center the molding at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the cavetto molding
    """
    return MoldingShapes.cavetto(
        width=width,
        height=height,
        length=length,
        radius_ratio=radius_ratio,
        segments=segments,
        centered=centered,
        name=name
    )


def create_cyma_recta(
    width: float = 12.0,
    height: float = 8.0,
    length: float = 100.0,
    convex_ratio: float = 0.4,
    concave_ratio: float = 0.4,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create a cyma recta molding.
    
    Args:
        width (float): The width (projection) of the molding in mm. Default: 12.0
        height (float): The height of the molding in mm. Default: 8.0
        length (float): The length of the molding in mm. Default: 100.0
        convex_ratio (float): Ratio for the convex curve (0.0-1.0). Default: 0.4
        concave_ratio (float): Ratio for the concave curve (0.0-1.0). Default: 0.4
        segments (int): Number of segments for curve approximation. Default: 32
        centered (bool): Whether to center the molding at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the cyma recta molding
    """
    return MoldingShapes.cyma_recta(
        width=width,
        height=height,
        length=length,
        convex_ratio=convex_ratio,
        concave_ratio=concave_ratio,
        segments=segments,
        centered=centered,
        name=name
    )


def create_cyma_reversa(
    width: float = 12.0,
    height: float = 8.0,
    length: float = 100.0,
    convex_ratio: float = 0.4,
    concave_ratio: float = 0.4,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create a cyma reversa molding.
    
    Args:
        width (float): The width (projection) of the molding in mm. Default: 12.0
        height (float): The height of the molding in mm. Default: 8.0
        length (float): The length of the molding in mm. Default: 100.0
        convex_ratio (float): Ratio for the convex curve (0.0-1.0). Default: 0.4
        concave_ratio (float): Ratio for the concave curve (0.0-1.0). Default: 0.4
        segments (int): Number of segments for curve approximation. Default: 32
        centered (bool): Whether to center the molding at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the cyma reversa molding
    """
    return MoldingShapes.cyma_reversa(
        width=width,
        height=height,
        length=length,
        convex_ratio=convex_ratio,
        concave_ratio=concave_ratio,
        segments=segments,
        centered=centered,
        name=name
    )


def create_scotia(
    width: float = 12.0,
    height: float = 8.0,
    length: float = 100.0,
    depth_ratio: float = 0.7,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create a scotia molding.
    
    Args:
        width (float): The width (projection) of the molding in mm. Default: 12.0
        height (float): The height of the molding in mm. Default: 8.0
        length (float): The length of the molding in mm. Default: 100.0
        depth_ratio (float): Ratio controlling the depth of the concave curve (0.0-1.0). Default: 0.7
        segments (int): Number of segments for the curve approximation. Default: 32
        centered (bool): Whether to center the molding at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the scotia molding
    """
    return MoldingShapes.scotia(
        width=width,
        height=height,
        length=length,
        depth_ratio=depth_ratio,
        segments=segments,
        centered=centered,
        name=name
    )


def create_fillet(
    width: float = 4.0,
    height: float = 4.0,
    length: float = 100.0,
    radius_ratio: float = 0.8,
    segments: int = 32,
    centered: bool = True,
    name: Optional[str] = None
) -> cq.Workplane:
    """
    Convenience function to create a fillet molding.
    
    Args:
        width (float): The width (projection) of the molding in mm. Default: 4.0
        height (float): The height of the molding in mm. Default: 4.0
        length (float): The length of the molding in mm. Default: 100.0
        radius_ratio (float): Ratio of the curve radius to height (0.0-1.0). Default: 0.8
        segments (int): Number of segments for the curve approximation. Default: 32
        centered (bool): Whether to center the molding at origin. Default: True
        name (str, optional): Name for the object
    
    Returns:
        cq.Workplane: A CadQuery workplane containing the fillet molding
    """
    return MoldingShapes.fillet(
        width=width,
        height=height,
        length=length,
        radius_ratio=radius_ratio,
        segments=segments,
        centered=centered,
        name=name
    )


# Example usage and testing
if __name__ == "__main__":
    # Create a simple ovolo for testing
    ovolo = create_ovolo(width=15, height=8, length=200, radius_ratio=0.7)
    
    # Show the result (this will work in CQ-Editor)
    show_object(ovolo)
    
    print("Ovolo molding created successfully!")
    print(f"Dimensions: {15}mm × {8}mm × {200}mm")
    print(f"Radius ratio: 0.7")