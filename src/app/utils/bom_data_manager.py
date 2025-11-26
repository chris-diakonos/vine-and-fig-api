"""
BOM data management utilities for storing and retrieving BOM state.
Uses file-based storage keyed by structure_hash, following the same pattern as structure data.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class BOMDataManager:
    """Manages BOM data storage and retrieval using structure_hash as the key."""
    
    @staticmethod
    def serialize_bom_data(bom_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert BOM data with defaultdicts to JSON-serializable format.
        
        Args:
            bom_data: BOM data dictionary with potentially defaultdict types
            
        Returns:
            JSON-serializable dictionary
        """
        serialized = bom_data.copy()
        
        # Convert defaultdict(set) to dict of lists
        if 'bom_components' in serialized:
            if isinstance(serialized['bom_components'], defaultdict):
                serialized['bom_components'] = {
                    k: list(v) if isinstance(v, set) else v
                    for k, v in serialized['bom_components'].items()
                }
            elif isinstance(serialized['bom_components'], dict):
                serialized['bom_components'] = {
                    k: list(v) if isinstance(v, set) else v
                    for k, v in serialized['bom_components'].items()
                }
        
        # Convert defaultdict(float) to dict
        if 'bom_quantities' in serialized:
            if isinstance(serialized['bom_quantities'], defaultdict):
                serialized['bom_quantities'] = dict(serialized['bom_quantities'])
        
        # Convert defaultdict(int) to dict
        if 'bom_levels' in serialized:
            if isinstance(serialized['bom_levels'], defaultdict):
                serialized['bom_levels'] = dict(serialized['bom_levels'])
        
        return serialized
    
    @staticmethod
    def deserialize_bom_data(json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert JSON data back to BOM data format with defaultdicts.
        
        Args:
            json_data: JSON data dictionary
            
        Returns:
            BOM data dictionary with defaultdict types
        """
        deserialized = json_data.copy()
        
        # Convert dict of lists back to defaultdict(set)
        if 'bom_components' in deserialized:
            bom_components = defaultdict(set)
            for k, v in deserialized['bom_components'].items():
                bom_components[k] = set(v) if isinstance(v, list) else v
            deserialized['bom_components'] = bom_components
        
        # Convert dict back to defaultdict(float)
        if 'bom_quantities' in deserialized:
            bom_quantities = defaultdict(float)
            bom_quantities.update(deserialized['bom_quantities'])
            deserialized['bom_quantities'] = bom_quantities
        
        # Convert dict back to defaultdict(int)
        if 'bom_levels' in deserialized:
            bom_levels = defaultdict(int)
            bom_levels.update(deserialized['bom_levels'])
            deserialized['bom_levels'] = bom_levels
        
        return deserialized
    
    @staticmethod
    def save_bom_data(structure_hash: str, bom_data: Dict[str, Any]) -> bool:
        """
        Save BOM data to a JSON file using the structure_hash as filename.
        
        Args:
            structure_hash: SHA-256 hash of the structure data (used as filename)
            bom_data: The BOM data dictionary to save
            
        Returns:
            True if file was saved successfully
        """
        # Create the file path using the structure hash as filename
        file_path = settings.bom_data_dir / f"{structure_hash}.json"
        
        try:
            # Ensure the bom_data directory exists
            settings.bom_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Add metadata
            bom_data_with_meta = bom_data.copy()
            bom_data_with_meta['structure_hash'] = structure_hash
            bom_data_with_meta['updated_at'] = datetime.utcnow().isoformat()
            
            # Check if file exists to set created_at
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        bom_data_with_meta['created_at'] = existing_data.get('created_at', bom_data_with_meta['updated_at'])
                except Exception:
                    bom_data_with_meta['created_at'] = bom_data_with_meta['updated_at']
            else:
                bom_data_with_meta['created_at'] = bom_data_with_meta['updated_at']
            
            # Serialize defaultdicts to JSON-serializable format
            serialized_data = BOMDataManager.serialize_bom_data(bom_data_with_meta)
            
            # Write the BOM data as JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(serialized_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved BOM data to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save BOM data to {file_path}: {str(e)}")
            raise RuntimeError(f"Failed to save BOM data: {str(e)}")
    
    @staticmethod
    def get_bom_data(structure_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve BOM data from file.
        
        Args:
            structure_hash: SHA-256 hash of the structure data
            
        Returns:
            BOM data dictionary, or None if not found
        """
        file_path = settings.bom_data_dir / f"{structure_hash}.json"
        
        if not file_path.exists():
            logger.info(f"BOM data file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Deserialize back to defaultdict format
            bom_data = BOMDataManager.deserialize_bom_data(json_data)
            
            logger.info(f"Retrieved BOM data from: {file_path}")
            return bom_data
            
        except Exception as e:
            logger.error(f"Failed to read BOM data from {file_path}: {str(e)}")
            raise RuntimeError(f"Failed to read BOM data: {str(e)}")
    
    @staticmethod
    def get_bom_data_path(structure_hash: str) -> Path:
        """
        Get the file path for a BOM data file.
        
        Args:
            structure_hash: SHA-256 hash of the structure data
            
        Returns:
            Path to the BOM data file
        """
        return settings.bom_data_dir / f"{structure_hash}.json"
    
    @staticmethod
    def bom_data_exists(structure_hash: str) -> bool:
        """
        Check if a BOM data file exists.
        
        Args:
            structure_hash: SHA-256 hash of the structure data
            
        Returns:
            True if the file exists, False otherwise
        """
        file_path = BOMDataManager.get_bom_data_path(structure_hash)
        return file_path.exists()
    
    @staticmethod
    def delete_bom_data(structure_hash: str) -> bool:
        """
        Delete BOM data file.
        
        Args:
            structure_hash: SHA-256 hash of the structure data
            
        Returns:
            True if file was deleted, False if it didn't exist
        """
        file_path = BOMDataManager.get_bom_data_path(structure_hash)
        
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            logger.info(f"Deleted BOM data file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete BOM data file {file_path}: {str(e)}")
            return False

