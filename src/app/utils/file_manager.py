"""
File management utilities for models and drawings.
Supports both local file storage and Azure Blob Storage.
"""
import os
import time
from pathlib import Path
from typing import Optional
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
    def get_model_path(model_id: str, file_type: str = "gltf") -> Path:
        """
        Get the file path for a 3D model.
        
        Args:
            model_id: Unique model identifier
            file_type: File extension (default: gltf)
            
        Returns:
            Path to the model file
        """
        filename = f"{model_id}.{file_type}"
        return settings.models_dir / filename
    
    @staticmethod
    def get_drawing_path(model_id: str, view_mode: str, file_type: str = "svg") -> Path:
        """
        Get the file path for a 2D drawing.
        
        Args:
            model_id: Unique model identifier
            view_mode: View mode (plan, section, elevation)
            file_type: File extension (default: svg)
            
        Returns:
            Path to the drawing file
        """
        filename = f"{model_id}_{view_mode}.{file_type}"
        return settings.drawings_dir / filename
    
    @staticmethod
    def get_model_url(model_id: str, file_type: str = "gltf") -> str:
        """
        Get the URL for accessing a 3D model.
        
        Args:
            model_id: Unique model identifier
            file_type: File extension (default: gltf)
            
        Returns:
            URL string
        """
        if FileManager._is_using_azure():
            # Return Azure Blob Storage URL
            blob_name = f"{settings.azure_models_prefix}{model_id}.{file_type}"
            account_name = settings.azure_storage_account_name
            container_name = settings.azure_storage_container_name
            return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        else:
            # Return local URL
            filename = f"{model_id}.{file_type}"
            return f"{settings.base_url}/models/{filename}"
    
    @staticmethod
    def get_drawing_url(model_id: str, view_mode: str, file_type: str = "svg") -> str:
        """
        Get the URL for accessing a 2D drawing.
        
        Args:
            model_id: Unique model identifier
            view_mode: View mode (plan, section, elevation)
            file_type: File extension (default: svg)
            
        Returns:
            URL string
        """
        if FileManager._is_using_azure():
            # Return Azure Blob Storage URL
            blob_name = f"{settings.azure_drawings_prefix}{model_id}_{view_mode}.{file_type}"
            account_name = settings.azure_storage_account_name
            container_name = settings.azure_storage_container_name
            return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        else:
            # Return local URL
            filename = f"{model_id}_{view_mode}.{file_type}"
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
