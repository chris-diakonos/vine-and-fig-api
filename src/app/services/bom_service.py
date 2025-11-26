"""
BOM Service for MRP API integration.
Handles submission of materials and BOMs to the MRP system.
"""
import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import logging

from app.utils.materials_helper import (
    get_distinct_materials,
    get_freight_attributes_by_category
)

logger = logging.getLogger(__name__)


class BOMService:
    """Service for interacting with MRP API to create materials and BOMs."""
    
    # MRP API base URL - should be configurable via environment variable
    MRP_API_BASE_URL = os.getenv("MRP_API_BASE_URL", "http://localhost:8002/api/v1")
    
    @staticmethod
    def get_material_id_by_name(material_name: str) -> Optional[str]:
        """
        Get material ID from MRP API by material name.
        
        Args:
            material_name: Name of the material
            
        Returns:
            Material ID if found, None otherwise
        """
        url = f"{BOMService.MRP_API_BASE_URL}/materials/"
        params = {"material_name": material_name}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            materials = response.json()
            for material in materials:
                if material.get('material_name') == material_name:
                    return material.get('material_id')
            
            logger.warning(f"Material '{material_name}' not found in MRP system")
            return None
            
        except requests.exceptions.HTTPError as err:
            logger.error(f"HTTP Error fetching material '{material_name}': {err}")
            return None
        except Exception as e:
            logger.error(f"Error fetching material '{material_name}': {e}")
            return None
    
    @staticmethod
    def create_materials(materials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create materials in MRP system.
        
        Args:
            materials: List of material dictionaries to create
            
        Returns:
            Dictionary with creation results
        """
        url = f"{BOMService.MRP_API_BASE_URL}/materials/"
        
        # Get existing materials
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            existing_materials = response.json()
            existing_material_names = {m.get('material_name') for m in existing_materials}
        except Exception as e:
            logger.error(f"Error fetching existing materials: {e}")
            existing_material_names = set()
        
        # Get distinct new materials
        new_materials = get_distinct_materials(materials)
        
        created_count = 0
        skipped_count = 0
        errors = []
        
        for material in new_materials:
            material_name = material.get('material_name')
            
            if material_name in existing_material_names:
                skipped_count += 1
                logger.info(f"Material '{material_name}' already exists, skipping")
                continue
            
            # Prepare request body
            category = material.get('category', 'other')
            freight_attrs = get_freight_attributes_by_category(category)
            
            request_body = {
                "material_name": material_name,
                "material_type": material.get('material_type'),
                "unit_of_measure": material.get('unit_of_measure', 'EA'),
                "unit_price": round(material.get('unit_price', 0), 2),
                "category": category,
                "procurement_type": material.get('procurement_type', 'buy'),
                "vehicle_type": freight_attrs.get('vehicle_type', 'flatbed'),
                "shipping_mode": (
                    "ftl" if material_name == "FTL FREIGHT"
                    else "ltl" if material_name == "LTL FREIGHT"
                    else freight_attrs.get('shipping_mode', 'ltl')
                ),
                "package_type": freight_attrs.get('package_type', 'pallet'),
                "dimension_unit": freight_attrs.get('dimension_unit', 'in'),
                "weight_unit": freight_attrs.get('weight_unit', 'lb'),
                "freight_class": freight_attrs.get('freight_class', '55'),
                "net_weight": material.get('net_weight'),
                "gross_weight": material.get('gross_weight'),
                "length": material.get('length'),
                "width": material.get('width'),
                "height": material.get('height'),
                "package_type_count": material.get('package_type_count', 1),
                "package_type_layers": material.get('package_type_layers', 1)
            }
            
            try:
                response = requests.post(url, json=request_body, timeout=10)
                response.raise_for_status()
                created_count += 1
                logger.info(f"Created material: {material_name}")
            except requests.exceptions.HTTPError as err:
                error_msg = f"Failed to create material '{material_name}': {err}"
                logger.error(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"Error creating material '{material_name}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "created": created_count,
            "skipped": skipped_count,
            "errors": errors,
            "total_processed": len(new_materials)
        }
    
    @staticmethod
    def get_bill_of_materials_by_material_id(material_id: str, bom_type: str = "production") -> Optional[List[Dict[str, Any]]]:
        """
        Get BOM from MRP API by material ID.
        
        Args:
            material_id: Material ID
            bom_type: Type of BOM (production or sales)
            
        Returns:
            List of BOM items or None if error
        """
        url = f"{BOMService.MRP_API_BASE_URL}/bill-of-materials/"
        params = {
            "parent_material_id": material_id,
            "bom_type": bom_type
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            logger.error(f"HTTP Error fetching BOM for material {material_id}: {err}")
            return None
        except Exception as e:
            logger.error(f"Error fetching BOM for material {material_id}: {e}")
            return None
    
    @staticmethod
    def create_production_bom(
        materials: List[Dict[str, Any]],
        bom_components: Dict[str, set],
        bom_quantities: Dict[str, float],
        bom_levels: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Create production BOMs in MRP system.
        
        Args:
            materials: List of all materials
            bom_components: Dictionary mapping component_id to set of raw_material_ids
            bom_quantities: Dictionary mapping "component_id|raw_material_id" to quantity
            bom_levels: Dictionary mapping material_id to BOM level
            
        Returns:
            Dictionary with creation results
        """
        url = f"{BOMService.MRP_API_BASE_URL}/bill-of-materials/"
        
        # Get all "make" materials (components)
        make_materials = [m for m in materials if m.get('procurement_type') == 'make']
        
        # Group by BOM level and process from lowest to highest
        materials_by_level = defaultdict(list)
        for material in make_materials:
            material_name = material.get('material_name')
            level = bom_levels.get(material_name, 1)
            materials_by_level[level].append(material)
        
        created_count = 0
        errors = []
        material_prices = {}
        cost_type_splits = {}
        
        # Process levels 1, 2, 3 in order
        for level in sorted(materials_by_level.keys()):
            for material in materials_by_level[level]:
                material_name = material.get('material_name')
                material_id = BOMService.get_material_id_by_name(material_name)
                
                if not material_id:
                    error_msg = f"Material '{material_name}' not found, cannot create BOM"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Get raw materials for this component
                raw_materials = bom_components.get(material_name, set())
                if not raw_materials:
                    logger.warning(f"No raw materials found for component '{material_name}'")
                    continue
                
                items = []
                total_price = 0
                
                for raw_material_name in raw_materials:
                    bom_quantity_key = f"{material_name}|{raw_material_name}"
                    quantity = bom_quantities.get(bom_quantity_key, 1.0)
                    
                    # Find raw material in materials list
                    raw_material_dict = None
                    for m in materials:
                        if m.get('material_name') == raw_material_name:
                            raw_material_dict = m
                            break
                    
                    if not raw_material_dict:
                        logger.warning(f"Raw material '{raw_material_name}' not found in materials list")
                        continue
                    
                    child_material_id = BOMService.get_material_id_by_name(raw_material_name)
                    if not child_material_id:
                        logger.warning(f"Raw material '{raw_material_name}' not found in MRP system")
                        continue
                    
                    child_procurement_type = raw_material_dict.get('procurement_type', 'buy')
                    child_unit_price = raw_material_dict.get('unit_price', 0)
                    
                    if child_procurement_type == "make":
                        # Use calculated price from previous level
                        child_unit_price = material_prices.get(raw_material_name, child_unit_price)
                        cost_type_split = cost_type_splits.get(raw_material_name, [{
                            "cost_type": "material",
                            "percentage": 100
                        }])
                    else:
                        cost_type_split = [{
                            "cost_type": "material",
                            "percentage": 100
                        }]
                    
                    item = {
                        "component_type": "item",
                        "procurement_type": child_procurement_type,
                        "issue_method": "manual",
                        "child_material_id": child_material_id,
                        "quantity": quantity,
                        "unit_of_measure": raw_material_dict.get('unit_of_measure', 'EA'),
                        "unit_price": child_unit_price,
                        "total_price": child_unit_price * quantity,
                        "memo": "",
                        "cost_type_split": cost_type_split
                    }
                    
                    items.append(item)
                    total_price += item['total_price']
                
                # Add machine resource for level 1 framing
                category = material.get('category', '')
                if category == "framing" and level == 1:
                    machine_material_id = BOMService.get_material_id_by_name("HUNDEGGER K2")
                    if machine_material_id:
                        machine = {
                            "component_type": "resource",
                            "procurement_type": "buy",
                            "issue_method": "backflush",
                            "child_material_id": machine_material_id,
                            "quantity": 0.10,
                            "unit_of_measure": "HR",
                            "unit_price": 10.00,
                            "total_price": 1.00,
                            "memo": "",
                            "cost_type_split": [{
                                "cost_type": "machine",
                                "percentage": 100,
                                "amount": 1.00
                            }]
                        }
                        items.append(machine)
                        total_price += 1.00
                
                # Add labor resource
                if level in [1, 2]:
                    labor_quantity = 0.10 if level == 1 else 0.50
                    labor_material_id = BOMService.get_material_id_by_name("SHOPFLOOR LABOR")
                    if labor_material_id:
                        labor = {
                            "component_type": "resource",
                            "procurement_type": "buy",
                            "issue_method": "backflush",
                            "child_material_id": labor_material_id,
                            "quantity": labor_quantity,
                            "unit_of_measure": "HR",
                            "unit_price": 30.00,
                            "total_price": labor_quantity * 30.00,
                            "memo": "",
                            "cost_type_split": [{
                                "cost_type": "labor",
                                "percentage": 100,
                                "amount": labor_quantity * 30.00
                            }]
                        }
                        items.append(labor)
                        total_price += labor['total_price']
                
                # Add electricity resource
                if level in [1, 2]:
                    electricity_quantity = 12 * 0.10 if level == 1 else 1 * 0.50
                    electricity_material_id = BOMService.get_material_id_by_name("ELECTRICITY")
                    if electricity_material_id:
                        electricity = {
                            "component_type": "resource",
                            "procurement_type": "buy",
                            "issue_method": "backflush",
                            "child_material_id": electricity_material_id,
                            "quantity": electricity_quantity,
                            "unit_of_measure": "KWH",
                            "unit_price": 0.20,
                            "total_price": electricity_quantity * 0.20,
                            "memo": "",
                            "cost_type_split": [{
                                "cost_type": "utility",
                                "percentage": 100,
                                "amount": electricity_quantity * 0.20
                            }]
                        }
                        items.append(electricity)
                        total_price += electricity['total_price']
                
                # Create BOM request
                request_body = {
                    "bom_type": "production",
                    "bom_version": "1.0",
                    "bom_date": datetime.now().strftime('%Y-%m-%d'),
                    "bom_status": "active",
                    "bom_level": level,
                    "parent_material_id": material_id,
                    "quantity": 1,
                    "unit_of_measure": material.get('unit_of_measure', 'EA'),
                    "unit_price": total_price,
                    "total_price": total_price,
                    "memo": f"Production BOM for {material_name}",
                    "items": items
                }
                
                try:
                    response = requests.post(url, json=request_body, timeout=10)
                    response.raise_for_status()
                    response_data = response.json()
                    
                    # Store calculated price and cost type split for next level
                    material_prices[material_name] = total_price
                    cost_type_splits[material_name] = response_data.get('cost_type_split', [])
                    
                    created_count += 1
                    logger.info(f"Created production BOM for: {material_name}")
                except requests.exceptions.HTTPError as err:
                    error_msg = f"Failed to create production BOM for '{material_name}': {err}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Error creating production BOM for '{material_name}': {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        return {
            "created": created_count,
            "errors": errors,
            "total_processed": len(make_materials)
        }
    
    @staticmethod
    def create_sales_bom(
        structure_hash: str,
        materials: List[Dict[str, Any]],
        bom_components: Dict[str, set],
        bom_quantities: Dict[str, float],
        bom_levels: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Create sales BOM in MRP system.
        
        Args:
            structure_hash: Structure hash identifier
            materials: List of all materials
            bom_components: Dictionary mapping structure_hash to set of component_ids
            bom_quantities: Dictionary mapping "structure_hash|component_id" to quantity
            bom_levels: Dictionary mapping material_id to BOM level
            
        Returns:
            Dictionary with creation results
        """
        url = f"{BOMService.MRP_API_BASE_URL}/bill-of-materials/"
        
        # Create sales material
        sales_material_name = f"SALES ORDER {structure_hash}"
        sales_material = {
            "material_name": sales_material_name,
            "material_type": "assembly",
            "unit_of_measure": "EA",
            "category": "other",
            "procurement_type": "make",
            "unit_price": 0  # Will be calculated
        }
        
        # Create the sales material first
        material_result = BOMService.create_materials([sales_material])
        sales_material_id = BOMService.get_material_id_by_name(sales_material_name)
        
        if not sales_material_id:
            return {
                "created": False,
                "errors": [f"Failed to create sales material '{sales_material_name}'"],
                "sales_material_id": None
            }
        
        # Get components for this structure
        component_ids = bom_components.get(structure_hash, set())
        items = []
        sales_order_price = 0
        
        for component_id in component_ids:
            bom_quantity_key = f"{structure_hash}|{component_id}"
            quantity = bom_quantities.get(bom_quantity_key, 0)
            
            if quantity == 0:
                continue
            
            child_material_id = BOMService.get_material_id_by_name(component_id)
            if not child_material_id:
                logger.warning(f"Component '{component_id}' not found in MRP system")
                continue
            
            # Get production BOM to calculate price
            production_bom = BOMService.get_bill_of_materials_by_material_id(child_material_id, "production")
            if not production_bom or len(production_bom) == 0:
                logger.warning(f"No production BOM found for component '{component_id}'")
                continue
            
            production_quantity = production_bom[0].get('quantity', 1)
            quantity_factor = quantity / production_quantity if production_quantity > 0 else quantity
            unit_price = production_bom[0].get('unit_price', 0)
            total_price = production_bom[0].get('total_price', 0) * quantity_factor
            cost_type_split = production_bom[0].get('cost_type_split', [])
            unit_of_measure = production_bom[0].get('unit_of_measure', 'EA')
            
            item = {
                "component_type": "item",
                "procurement_type": "make",
                "issue_method": "manual",
                "child_material_id": child_material_id,
                "quantity": quantity,
                "unit_of_measure": unit_of_measure,
                "unit_price": unit_price,
                "total_price": total_price,
                "memo": "",
                "cost_type_split": cost_type_split
            }
            
            items.append(item)
            sales_order_price += total_price
        
        # Create sales BOM
        request_body = {
            "bom_type": "sales",
            "bom_version": structure_hash,
            "bom_date": datetime.now().strftime('%Y-%m-%d'),
            "bom_status": "active",
            "bom_level": 4,
            "parent_material_id": sales_material_id,
            "quantity": 1,
            "unit_of_measure": "EA",
            "unit_price": sales_order_price,
            "total_price": sales_order_price,
            "memo": f"BOM FOR SALES ORDER {structure_hash}",
            "cost_type_split": [{
                "cost_type": "material",
                "percentage": 100
            }],
            "items": items
        }
        
        try:
            response = requests.post(url, json=request_body, timeout=10)
            response.raise_for_status()
            logger.info(f"Created sales BOM for structure: {structure_hash}")
            return {
                "created": True,
                "errors": [],
                "sales_material_id": sales_material_id,
                "total_price": sales_order_price
            }
        except requests.exceptions.HTTPError as err:
            error_msg = f"Failed to create sales BOM for structure '{structure_hash}': {err}"
            logger.error(error_msg)
            return {
                "created": False,
                "errors": [error_msg],
                "sales_material_id": sales_material_id
            }
        except Exception as e:
            error_msg = f"Error creating sales BOM for structure '{structure_hash}': {e}"
            logger.error(error_msg)
            return {
                "created": False,
                "errors": [error_msg],
                "sales_material_id": sales_material_id
            }
    
    @staticmethod
    def submit_bom_to_mrp(structure_hash: str) -> Dict[str, Any]:
        """
        Submit complete BOM (materials, production BOMs, and sales BOM) to MRP system.
        
        Args:
            structure_hash: Structure hash identifier
            
        Returns:
            Dictionary with submission results
        """
        from app.utils.bom_data_manager import BOMDataManager
        
        # Load BOM data
        bom_data = BOMDataManager.get_bom_data(structure_hash)
        if not bom_data:
            return {
                "success": False,
                "error": f"BOM data not found for structure_hash: {structure_hash}"
            }
        
        materials = bom_data.get('materials', [])
        bom_components = bom_data.get('bom_components', {})
        bom_quantities = bom_data.get('bom_quantities', {})
        bom_levels = bom_data.get('bom_levels', {})
        
        results = {
            "structure_hash": structure_hash,
            "materials": {},
            "production_boms": {},
            "sales_bom": {},
            "success": True,
            "errors": []
        }
        
        # Step 1: Create materials
        logger.info(f"Creating materials for structure: {structure_hash}")
        materials_result = BOMService.create_materials(materials)
        results["materials"] = materials_result
        if materials_result.get("errors"):
            results["errors"].extend(materials_result["errors"])
        
        # Step 2: Create production BOMs
        logger.info(f"Creating production BOMs for structure: {structure_hash}")
        production_result = BOMService.create_production_bom(
            materials,
            bom_components,
            bom_quantities,
            bom_levels
        )
        results["production_boms"] = production_result
        if production_result.get("errors"):
            results["errors"].extend(production_result["errors"])
        
        # Step 3: Create sales BOM
        logger.info(f"Creating sales BOM for structure: {structure_hash}")
        sales_result = BOMService.create_sales_bom(
            structure_hash,
            materials,
            bom_components,
            bom_quantities,
            bom_levels
        )
        results["sales_bom"] = sales_result
        if sales_result.get("errors"):
            results["errors"].extend(sales_result["errors"])
        
        # Overall success if no errors
        if results["errors"]:
            results["success"] = False
        
        return results

