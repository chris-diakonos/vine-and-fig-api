"""
File management utilities for models and drawings.
Supports both local file storage and Azure Blob Storage.
"""
import os
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4
import logging

from app.config import settings

# Import Azure storage functions
try:
    from app.utils.azure_storage import (
        write_blob,
        delete_blob,
        blob_exists,
        list_blobs,
        create_container_if_not_exists
    )
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

logger = logging.getLogger(__name__)


class FileManager:
    """Manages file storage, URL generation, and cleanup.
    
    Supports both local file storage and Azure Blob Storage based on configuration.
    """
    
    @staticmethod
    def generate_model_id() -> str:
        """Generate a unique model ID."""
        return str(uuid4())
    
    @staticmethod
    def _is_using_azure() -> bool:
        """Check if Azure Storage is enabled and available."""
        return settings.is_azure_storage_enabled() and AZURE_AVAILABLE
    
    @staticmethod
    def get_model_path(model_id: str, file_type: str = "gltf", structure_hash: str = None) -> Path:
        """
        Get the file path for a 3D model.
        
        Args:
            model_id: Unique model identifier
            file_type: File extension (default: gltf)
            structure_hash: Optional structure hash to use in filename
            
        Returns:
            Path to the model file
        """
        if structure_hash:
            filename = f"{structure_hash}.{file_type}"
        else:
            filename = f"{model_id}.{file_type}"
        return settings.models_dir / filename
    
    @staticmethod
    def get_drawing_path(model_id: str, view_mode: str, file_type: str = "svg", structure_hash: str = None) -> Path:
        """
        Get the file path for a 2D drawing.
        
        Args:
            model_id: Unique model identifier
            view_mode: View mode (plan, section, elevation)
            file_type: File extension (default: svg)
            structure_hash: Optional structure hash to use in filename
            
        Returns:
            Path to the drawing file
        """
        if structure_hash:
            filename = f"{structure_hash}_{view_mode}.{file_type}"
        else:
            filename = f"{model_id}_{view_mode}.{file_type}"
        return settings.drawings_dir / filename
    
    @staticmethod
    def get_model_url(model_id: str, file_type: str = "gltf", structure_hash: str = None) -> str:
        """
        Get the URL for accessing a 3D model.
        
        Args:
            model_id: Unique model identifier
            file_type: File extension (default: gltf)
            structure_hash: Optional structure hash to use in filename
            
        Returns:
            URL string
        """
        if structure_hash:
            filename = f"{structure_hash}.{file_type}"
        else:
            filename = f"{model_id}.{file_type}"
            
        if FileManager._is_using_azure():
            # Return Azure Blob Storage URL
            blob_name = f"{settings.azure_models_prefix}{filename}"
            account_name = settings.azure_storage_account_name
            container_name = settings.azure_storage_container_name
            return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        else:
            # Return local URL
            return f"{settings.base_url}/models/{filename}"
    
    @staticmethod
    def get_drawing_url(model_id: str, view_mode: str, file_type: str = "svg", structure_hash: str = None) -> str:
        """
        Get the URL for accessing a 2D drawing.
        
        Args:
            model_id: Unique model identifier
            view_mode: View mode (plan, section, elevation)
            file_type: File extension (default: svg)
            structure_hash: Optional structure hash to use in filename
            
        Returns:
            URL string
        """
        if structure_hash:
            filename = f"{structure_hash}_{view_mode}.{file_type}"
        else:
            filename = f"{model_id}_{view_mode}.{file_type}"
            
        if FileManager._is_using_azure():
            # Return Azure Blob Storage URL
            blob_name = f"{settings.azure_drawings_prefix}{filename}"
            account_name = settings.azure_storage_account_name
            container_name = settings.azure_storage_container_name
            return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        else:
            # Return local URL
            return f"{settings.base_url}/drawings/{filename}"
    
    @staticmethod
    def save_file(file_path: Path, blob_name: str, content_type: Optional[str] = None) -> str:
        """
        Save a file to storage (local or Azure).
        
        Args:
            file_path: Local file path to save
            blob_name: Name for the blob (used for Azure, or as filename for local)
            content_type: MIME type of the content
            
        Returns:
            URL to the saved file
        """
        if FileManager._is_using_azure():
            # Upload to Azure Blob Storage
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                write_blob(
                    blob_name=blob_name,
                    data=file_data,
                    container_name=settings.azure_storage_container_name,
                    content_type=content_type,
                    overwrite=True
                )
                
                # Delete local temp file
                if file_path.exists():
                    file_path.unlink()
                
                logger.info(f"Uploaded file to Azure: {blob_name}")
                
                # Return the blob URL
                account_name = settings.azure_storage_account_name
                container_name = settings.azure_storage_container_name
                return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
                
            except Exception as e:
                logger.error(f"Failed to upload to Azure: {str(e)}")
                raise RuntimeError(f"Failed to upload file to Azure Storage: {str(e)}")
        else:
            # File is already saved locally, just return the URL
            if "models" in str(file_path):
                filename = file_path.name
                return f"{settings.base_url}/models/{filename}"
            elif "drawings" in str(file_path):
                filename = file_path.name
                return f"{settings.base_url}/drawings/{filename}"
            else:
                raise ValueError(f"Unknown file path type: {file_path}")
    
    @staticmethod
    def cleanup_old_files(max_age_seconds: Optional[int] = None):
        """
        Remove files older than max_age_seconds.
        
        Args:
            max_age_seconds: Maximum file age in seconds (uses settings default if None)
        """
        if FileManager._is_using_azure():
            # For Azure, we could implement cleanup based on blob metadata
            # For now, skip automatic cleanup for Azure (can be handled by Azure lifecycle policies)
            logger.info("Azure Storage cleanup should be configured via Azure lifecycle management policies")
            return
        
        # Local storage cleanup
        if max_age_seconds is None:
            max_age_seconds = settings.file_max_age
        
        current_time = time.time()
        
        # Cleanup models directory
        for file_path in settings.models_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
        
        # Cleanup drawings directory
        for file_path in settings.drawings_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
        
        # Cleanup structures directory
        for file_path in settings.structures_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
    
    @staticmethod
    def save_structure_data(structure_hash: str, structure_data: Dict[str, Any]) -> bool:
        """
        Save structure data to a JSON file using the structure_hash as filename.
        
        Args:
            structure_hash: SHA-256 hash of the structure data (used as filename)
            structure_data: The structure data dictionary to save
            
        Returns:
            True if file was saved, False if file already exists
        """
        # Create the file path using the structure hash as filename
        file_path = settings.structures_dir / f"{structure_hash}.json"
        
        # Check if file already exists
        if file_path.exists():
            logger.info(f"Structure data file already exists: {file_path}")
            return False
        
        try:
            # Ensure the structures directory exists
            settings.structures_dir.mkdir(parents=True, exist_ok=True)
            
            # Write the structure data as JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(structure_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved structure data to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save structure data to {file_path}: {str(e)}")
            raise RuntimeError(f"Failed to save structure data: {str(e)}")
    
    @staticmethod
    def get_structure_data_path(structure_hash: str) -> Path:
        """
        Get the file path for a structure data file.
        
        Args:
            structure_hash: SHA-256 hash of the structure data
            
        Returns:
            Path to the structure data file
        """
        return settings.structures_dir / f"{structure_hash}.json"
    
    @staticmethod
    def structure_data_exists(structure_hash: str) -> bool:
        """
        Check if a structure data file exists.
        
        Args:
            structure_hash: SHA-256 hash of the structure data
            
        Returns:
            True if the file exists, False otherwise
        """
        file_path = FileManager.get_structure_data_path(structure_hash)
        return file_path.exists()
    
    @staticmethod
    def hashed_model_exists(structure_hash: str, file_type: str = "gltf") -> bool:
        """
        Check if a hashed model file exists.
        
        Args:
            structure_hash: SHA-256 hash of the structure data
            file_type: File extension (default: gltf)
            
        Returns:
            True if the file exists, False otherwise
        """
        file_path = FileManager.get_model_path("", file_type, structure_hash)
        return file_path.exists()
    
    @staticmethod
    def hashed_drawing_exists(structure_hash: str, view_mode: str, file_type: str = "svg") -> bool:
        """
        Check if a hashed drawing file exists.
        
        Args:
            structure_hash: SHA-256 hash of the structure data
            view_mode: View mode (plan, section, elevation)
            file_type: File extension (default: svg)
            
        Returns:
            True if the file exists, False otherwise
        """
        file_path = FileManager.get_drawing_path("", view_mode, file_type, structure_hash)
        return file_path.exists()
    
    @staticmethod
    def should_regenerate_hashed_file(structure_hash: str) -> bool:
        """
        Determine if a hashed file should be regenerated based on environment settings.
        
        Args:
            structure_hash: SHA-256 hash of the structure data
            
        Returns:
            True if the file should be regenerated, False if existing file should be used
        """
        return settings.regenerate_existing_hashed_files

    @staticmethod
    def ensure_directories():
        """Ensure all required directories exist."""
        if FileManager._is_using_azure():
            # Ensure Azure container exists
            try:
                create_container_if_not_exists(settings.azure_storage_container_name)
                logger.info(f"Azure container '{settings.azure_storage_container_name}' is ready")
            except Exception as e:
                logger.warning(f"Could not ensure Azure container exists: {str(e)}")
        else:
            # Create local directories
            settings.models_dir.mkdir(parents=True, exist_ok=True)
            settings.drawings_dir.mkdir(parents=True, exist_ok=True)
            settings.structures_dir.mkdir(parents=True, exist_ok=True)
            settings.bom_data_dir.mkdir(parents=True, exist_ok=True)
