"""
Helper functions for materials and BOM calculations.
Adapted from bom-generator for use in the API.
"""
import math
from collections import defaultdict
from typing import List, Dict, Any, Tuple


def find_raw_material_id(length: float, width: float, height: float, member_type: str, category: str) -> str:
    """
    Generate a raw material ID based on dimensions and type.
    
    Args:
        length: Length in inches
        width: Width in inches
        height: Height in inches
        member_type: Type of member (e.g., "sill", "joist")
        category: Material category (e.g., "framing")
        
    Returns:
        Raw material ID string
    """
    if category == "framing":
        length_feet = math.ceil(length / 12)
        raw_material_id = f"SYP #2 ({width}x{height}x{length_feet})"
    else:
        member_text = member_type.replace("_", " ").upper()
        category_text = category.replace("_", " ").upper()
        raw_material_id = f"{member_text} {category_text} ({width}x{height}x{length})"
    
    return raw_material_id


def find_component_id(length: float, width: float, height: float, member_type: str, category: str) -> str:
    """
    Generate a component ID based on dimensions and type.
    
    Args:
        length: Length in inches
        width: Width in inches
        height: Height in inches
        member_type: Type of member (e.g., "sill", "joist")
        category: Material category (e.g., "framing")
        
    Returns:
        Component ID string
    """
    if category == "framing":
        member_text = member_type.replace("_", " ").upper()
        component_id = f"{member_text} ({width}x{height}x{length})"
    elif category == "flooring":
        if member_type == "tongue-and-groove":
            member_text = "T&G"
        else:
            member_text = member_type.replace("-", " ").upper()
        category_text = category.replace("-", " ").upper()
        component_id = f"{member_text} {category_text} ({width}x{height}x{length})"
    elif category == "roofing":
        member_text = member_type.replace("-", " ").upper()
        category_text = category.replace("-", " ").upper()
        component_id = f"{member_text} {category_text} ({width}x{height}x{length})"
    elif category == "foundation":
        member_text = member_type.replace("-", " ").upper()
        component_id = f"{member_text} ({width}x{height}x{length})"
    elif category == "sheathing":
        member_text = member_type.replace("-", " ").upper()
        component_id = f"{member_text} ({width}x{height}x{length})"
    elif category == "window-component":
        member_text = member_type.replace("-", " ").upper()
        component_id = f"{member_text} ({width}x{height}x{length})"
    elif category == "window-part":
        member_text = member_type.replace("-", " ").upper()
        component_id = f"{member_text} {length} LITE {width}x{height}"
    else:
        component_id = None
    
    return component_id


def get_freight_attributes_by_category(category: str) -> Dict[str, Any]:
    """
    Get freight attributes for a material category.
    
    Args:
        category: Material category
        
    Returns:
        Dictionary of freight attributes
    """
    freight_configs = {
        "framing": {
            "vehicle_type": "flatbed",
            "shipping_mode": "ftl",
            "package_type": "skid",
            "special_handling_type": "hea",
            "dimension_unit": "in",
            "weight_unit": "lb",
            "freight_class": "55",
        },
        "flooring": {
            "vehicle_type": "flatbed",
            "shipping_mode": "ltl",
            "package_type": "skid",
            "dimension_unit": "in",
            "weight_unit": "lb",
            "freight_class": "55",
        },
        "roofing": {
            "vehicle_type": "flatbed",
            "shipping_mode": "ltl",
            "package_type": "skid",
            "dimension_unit": "in",
            "weight_unit": "lb",
            "freight_class": "70",
        },
        "foundation": {
            "vehicle_type": "flatbed",
            "shipping_mode": "ftl",
            "package_type": "pallet",
            "dimension_unit": "in",
            "weight_unit": "lb",
            "freight_class": "55",
        },
        "sheathing": {
            "vehicle_type": "flatbed",
            "shipping_mode": "ltl",
            "package_type": "skid",
            "dimension_unit": "in",
            "weight_unit": "lb",
            "freight_class": "55",
        },
        "window-blank": {
            "vehicle_type": "flatbed",
            "shipping_mode": "ltl",
            "package_type": "pallet",
            "dimension_unit": "in",
            "weight_unit": "lb",
            "freight_class": "55",
        },
        "window-lite": {
            "vehicle_type": "flatbed",
            "shipping_mode": "ltl",
            "package_type": "pallet",
            "dimension_unit": "in",
            "weight_unit": "lb",
            "freight_class": "175",
        },
    }
    
    return freight_configs.get(category, {
        "vehicle_type": "flatbed",
        "shipping_mode": "ltl",
        "package_type": "pallet",
        "dimension_unit": "in",
        "weight_unit": "lb",
        "freight_class": "55"
    })


def calculate_board_feet(length: float, width: float, height: float) -> float:
    """
    Calculate board feet from dimensions.
    
    Args:
        length: Length in inches
        width: Width in inches
        height: Height in inches
        
    Returns:
        Board feet (rounded to 2 decimal places)
    """
    return round((length * width * height) / 144, 2)


def get_distinct_materials(materials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get distinct materials from a list, removing duplicates by material_name.
    
    Args:
        materials: List of material dictionaries
        
    Returns:
        List of distinct materials
    """
    seen_materials = set()
    distinct_materials = []
    
    for material in materials:
        material_name = material.get('material_name')
        if material_name not in seen_materials:
            seen_materials.add(material_name)
            distinct_materials.append(material)
    
    return distinct_materials


def add_framing_materials(
    member_type: str,
    length: float,
    width: float,
    height: float,
    materials: List[Dict[str, Any]]
) -> Tuple[str, str]:
    """
    Add framing materials (raw and component) to the materials list.
    
    Args:
        member_type: Type of framing member (e.g., "sill", "joist")
        length: Length in feet (will be converted to inches)
        width: Width in inches
        height: Height in inches
        materials: List to append materials to
        
    Returns:
        Tuple of (raw_material_id, component_id)
    """
    category = "framing"
    length_inches = length * 12
    raw_material_id = find_raw_material_id(length_inches, width, height, member_type, category)
    component_id = find_component_id(length_inches, width, height, member_type, category)
    
    green_lumber_density = 0.027
    raw_lumber_price = 1.05
    component_markup = 0.1
    board_feet = calculate_board_feet(length_inches, width, height)
    net_weight = board_feet * green_lumber_density
    gross_weight = net_weight * 1.05
    unit_price = raw_lumber_price * board_feet
    component_price = unit_price * (1 + component_markup)
    package_type_count = math.floor(48 / width) if width > 0 else 1
    package_type_layers = math.floor(40 / height) if height > 0 else 1
    
    raw_material = {
        "material_name": raw_material_id,
        "material_type": "raw",
        "category": "framing",
        "procurement_type": "buy",
        "unit_price": unit_price,
        "unit_of_measure": "EA",
        "net_weight": net_weight,
        "gross_weight": gross_weight,
        "length": length_inches,
        "width": width,
        "height": height,
        "package_type_count": package_type_count,
        "package_type_layers": package_type_layers
    }
    
    component = {
        "material_name": component_id,
        "material_type": "component",
        "category": "framing",
        "procurement_type": "make",
        "unit_price": component_price,
        "unit_of_measure": "EA",
        "net_weight": net_weight,
        "gross_weight": gross_weight,
        "length": length_inches,
        "width": width,
        "height": height,
        "package_type_count": package_type_count,
        "package_type_layers": package_type_layers
    }
    
    materials.append(raw_material)
    materials.append(component)
    
    return raw_material_id, component_id


def add_production_bom_quantities(
    component_id: str,
    raw_material_id: str,
    quantity: float,
    bom_level: int,
    bom_quantities: Dict[str, float],
    bom_levels: Dict[str, int],
    bom_components: Dict[str, set]
) -> None:
    """
    Add production BOM quantities (component to raw material relationship).
    
    Args:
        component_id: Component material ID
        raw_material_id: Raw material ID
        quantity: Quantity of raw material needed per component
        bom_level: BOM level (typically 2 for production)
        bom_quantities: Dictionary to store BOM quantities
        bom_levels: Dictionary to store BOM levels
        bom_components: Dictionary to store BOM component relationships
    """
    bom_quantity_key = f"{component_id}|{raw_material_id}"
    bom_quantities[bom_quantity_key] = quantity
    
    bom_levels[raw_material_id] = bom_level - 1
    bom_levels[component_id] = bom_level
    
    if component_id not in bom_components:
        bom_components[component_id] = set()
    bom_components[component_id].add(raw_material_id)


def add_sales_bom_quantities(
    component_id: str,
    structure_hash: str,
    quantity: float,
    bom_level: int,
    bom_quantities: Dict[str, float],
    bom_levels: Dict[str, int],
    bom_components: Dict[str, set]
) -> None:
    """
    Add sales BOM quantities (structure to component relationship).
    
    Args:
        component_id: Component material ID
        structure_hash: Structure hash identifier
        quantity: Quantity of component needed for structure
        bom_level: BOM level (typically 3 for sales)
        bom_quantities: Dictionary to store BOM quantities
        bom_levels: Dictionary to store BOM levels
        bom_components: Dictionary to store BOM component relationships
    """
    bom_quantity_key = f"{structure_hash}|{component_id}"
    bom_quantities[bom_quantity_key] = quantity
    
    bom_levels[structure_hash] = bom_level
    
    if structure_hash not in bom_components:
        bom_components[structure_hash] = set()
    bom_components[structure_hash].add(component_id)

