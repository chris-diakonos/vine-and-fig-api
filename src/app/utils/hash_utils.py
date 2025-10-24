"""
Hash utilities for structure data validation.
"""
import hashlib
import json
from typing import Dict, Any


def calculate_structure_hash(structure_data: Dict[str, Any]) -> str:
    """
    Calculate SHA-256 hash of structure data.
    
    Args:
        structure_data: The structure data dictionary
        
    Returns:
        SHA-256 hash as hex string
    """
    # Convert to JSON string with sorted keys for consistent hashing
    json_string = json.dumps(structure_data, sort_keys=True, separators=(',', ':'))
    
    # Calculate SHA-256 hash
    hash_object = hashlib.sha256(json_string.encode('utf-8'))
    
    # Return as hex string
    return hash_object.hexdigest()


def validate_structure_hash(provided_hash: str, structure_data: Dict[str, Any]) -> bool:
    """
    Validate that a structure hash matches the current structure data.
    
    Args:
        provided_hash: The hash provided by the client
        structure_data: The current structure data
        
    Returns:
        Whether the hash matches
    """
    calculated_hash = calculate_structure_hash(structure_data)
    return provided_hash == calculated_hash
