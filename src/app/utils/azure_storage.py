"""
Azure Storage Blob helper functions for reading and writing blobs using SAS token authentication.

This module provides helper functions to interact with Azure Blob Storage using
Shared Access Signature (SAS) tokens for authentication. The SAS token and storage
account information should be provided via environment variables.

Environment Variables Required:
- AZURE_STORAGE_ACCOUNT_NAME: The name of the Azure storage account
- AZURE_STORAGE_SAS_TOKEN: The SAS token for authentication
- AZURE_STORAGE_CONTAINER_NAME: The default container name (optional)

Example:
    from azure_storage import read_blob, write_blob
    
    # Read a blob
    content = read_blob("myfile.txt", "my-container")
    
    # Write a blob
    write_blob("myfile.txt", b"Hello World", "my-container")
"""

import os
import logging
from typing import Optional, Union, BinaryIO
from io import BytesIO

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError, ResourceNotFoundError, ResourceExistsError

# Configure logging
logger = logging.getLogger(__name__)

# Environment variable names
AZURE_STORAGE_ACCOUNT_NAME = "AZURE_STORAGE_ACCOUNT_NAME"
AZURE_STORAGE_SAS_TOKEN = "AZURE_STORAGE_SAS_TOKEN"
AZURE_STORAGE_CONTAINER_NAME = "AZURE_STORAGE_CONTAINER_NAME"


def _get_blob_service_client() -> BlobServiceClient:
    """
    Create and return a BlobServiceClient using SAS token authentication.
    
    Returns:
        BlobServiceClient: Configured client for Azure Blob Storage
        
    Raises:
        ValueError: If required environment variables are not set
        AzureError: If there's an error creating the client
    """
    account_name = os.getenv(AZURE_STORAGE_ACCOUNT_NAME)
    sas_token = os.getenv(AZURE_STORAGE_SAS_TOKEN)
    
    if not account_name:
        raise ValueError(f"Environment variable {AZURE_STORAGE_ACCOUNT_NAME} is not set")
    if not sas_token:
        raise ValueError(f"Environment variable {AZURE_STORAGE_SAS_TOKEN} is not set")
    
    # Construct the account URL with SAS token
    account_url = f"https://{account_name}.blob.core.windows.net"
    sas_url = f"{account_url}?{sas_token}"
    
    try:
        client = BlobServiceClient(account_url=sas_url)
        logger.info(f"Successfully created BlobServiceClient for account: {account_name}")
        return client
    except Exception as e:
        logger.error(f"Failed to create BlobServiceClient: {str(e)}")
        raise AzureError(f"Failed to create BlobServiceClient: {str(e)}") from e


def read_blob(blob_name: str, container_name: Optional[str] = None) -> bytes:
    """
    Read a blob from Azure Blob Storage.
    
    Args:
        blob_name: Name of the blob to read
        container_name: Name of the container (uses default from env if not provided)
        
    Returns:
        bytes: The content of the blob
        
    Raises:
        ValueError: If required parameters are missing
        ResourceNotFoundError: If the blob or container doesn't exist
        AzureError: If there's an error reading the blob
    """
    if not blob_name:
        raise ValueError("blob_name cannot be empty")
    
    if not container_name:
        container_name = os.getenv(AZURE_STORAGE_CONTAINER_NAME)
        if not container_name:
            raise ValueError(f"container_name must be provided or {AZURE_STORAGE_CONTAINER_NAME} environment variable must be set")
    
    try:
        client = _get_blob_service_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        
        logger.info(f"Reading blob: {blob_name} from container: {container_name}")
        blob_data = blob_client.download_blob().readall()
        
        logger.info(f"Successfully read blob: {blob_name} ({len(blob_data)} bytes)")
        return blob_data
        
    except ResourceNotFoundError as e:
        logger.error(f"Blob or container not found: {blob_name} in {container_name}")
        raise
    except Exception as e:
        logger.error(f"Error reading blob {blob_name}: {str(e)}")
        raise AzureError(f"Error reading blob {blob_name}: {str(e)}") from e


def write_blob(
    blob_name: str, 
    data: Union[bytes, str, BinaryIO], 
    container_name: Optional[str] = None,
    content_type: Optional[str] = None,
    overwrite: bool = True
) -> str:
    """
    Write data to a blob in Azure Blob Storage.
    
    Args:
        blob_name: Name of the blob to write
        data: Data to write (bytes, string, or file-like object)
        container_name: Name of the container (uses default from env if not provided)
        content_type: MIME type of the content (optional)
        overwrite: Whether to overwrite existing blobs (default: True)
        
    Returns:
        str: The URL of the uploaded blob
        
    Raises:
        ValueError: If required parameters are missing
        ResourceExistsError: If blob exists and overwrite=False
        AzureError: If there's an error writing the blob
    """
    if not blob_name:
        raise ValueError("blob_name cannot be empty")
    
    if not container_name:
        container_name = os.getenv(AZURE_STORAGE_CONTAINER_NAME)
        if not container_name:
            raise ValueError(f"container_name must be provided or {AZURE_STORAGE_CONTAINER_NAME} environment variable must be set")
    
    try:
        client = _get_blob_service_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        
        # Convert string data to bytes if needed
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif hasattr(data, 'read'):
            # Handle file-like objects
            data = data.read()
        
        # Set content type if provided
        blob_kwargs = {}
        if content_type:
            blob_kwargs['content_type'] = content_type
        
        logger.info(f"Writing blob: {blob_name} to container: {container_name}")
        
        # Upload the blob
        blob_client.upload_blob(
            data, 
            overwrite=overwrite,
            **blob_kwargs
        )
        
        blob_url = blob_client.url
        logger.info(f"Successfully wrote blob: {blob_name} ({len(data)} bytes)")
        return blob_url
        
    except ResourceExistsError as e:
        logger.error(f"Blob already exists and overwrite=False: {blob_name}")
        raise
    except Exception as e:
        logger.error(f"Error writing blob {blob_name}: {str(e)}")
        raise AzureError(f"Error writing blob {blob_name}: {str(e)}") from e


def delete_blob(blob_name: str, container_name: Optional[str] = None) -> bool:
    """
    Delete a blob from Azure Blob Storage.
    
    Args:
        blob_name: Name of the blob to delete
        container_name: Name of the container (uses default from env if not provided)
        
    Returns:
        bool: True if the blob was deleted, False if it didn't exist
        
    Raises:
        ValueError: If required parameters are missing
        AzureError: If there's an error deleting the blob
    """
    if not blob_name:
        raise ValueError("blob_name cannot be empty")
    
    if not container_name:
        container_name = os.getenv(AZURE_STORAGE_CONTAINER_NAME)
        if not container_name:
            raise ValueError(f"container_name must be provided or {AZURE_STORAGE_CONTAINER_NAME} environment variable must be set")
    
    try:
        client = _get_blob_service_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        
        logger.info(f"Deleting blob: {blob_name} from container: {container_name}")
        blob_client.delete_blob()
        
        logger.info(f"Successfully deleted blob: {blob_name}")
        return True
        
    except ResourceNotFoundError:
        logger.warning(f"Blob not found for deletion: {blob_name}")
        return False
    except Exception as e:
        logger.error(f"Error deleting blob {blob_name}: {str(e)}")
        raise AzureError(f"Error deleting blob {blob_name}: {str(e)}") from e


def blob_exists(blob_name: str, container_name: Optional[str] = None) -> bool:
    """
    Check if a blob exists in Azure Blob Storage.
    
    Args:
        blob_name: Name of the blob to check
        container_name: Name of the container (uses default from env if not provided)
        
    Returns:
        bool: True if the blob exists, False otherwise
        
    Raises:
        ValueError: If required parameters are missing
        AzureError: If there's an error checking the blob
    """
    if not blob_name:
        raise ValueError("blob_name cannot be empty")
    
    if not container_name:
        container_name = os.getenv(AZURE_STORAGE_CONTAINER_NAME)
        if not container_name:
            raise ValueError(f"container_name must be provided or {AZURE_STORAGE_CONTAINER_NAME} environment variable must be set")
    
    try:
        client = _get_blob_service_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        
        blob_client.get_blob_properties()
        return True
        
    except ResourceNotFoundError:
        return False
    except Exception as e:
        logger.error(f"Error checking if blob exists {blob_name}: {str(e)}")
        raise AzureError(f"Error checking if blob exists {blob_name}: {str(e)}") from e


def list_blobs(container_name: Optional[str] = None, prefix: Optional[str] = None) -> list:
    """
    List blobs in a container.
    
    Args:
        container_name: Name of the container (uses default from env if not provided)
        prefix: Optional prefix to filter blob names
        
    Returns:
        list: List of blob names
        
    Raises:
        ValueError: If required parameters are missing
        AzureError: If there's an error listing blobs
    """
    if not container_name:
        container_name = os.getenv(AZURE_STORAGE_CONTAINER_NAME)
        if not container_name:
            raise ValueError(f"container_name must be provided or {AZURE_STORAGE_CONTAINER_NAME} environment variable must be set")
    
    try:
        client = _get_blob_service_client()
        container_client = client.get_container_client(container=container_name)
        
        logger.info(f"Listing blobs in container: {container_name}")
        blobs = container_client.list_blobs(name_starts_with=prefix)
        
        blob_names = [blob.name for blob in blobs]
        logger.info(f"Found {len(blob_names)} blobs in container: {container_name}")
        return blob_names
        
    except Exception as e:
        logger.error(f"Error listing blobs in container {container_name}: {str(e)}")
        raise AzureError(f"Error listing blobs in container {container_name}: {str(e)}") from e


def create_container_if_not_exists(container_name: str) -> bool:
    """
    Create a container if it doesn't exist.
    
    Args:
        container_name: Name of the container to create
        
    Returns:
        bool: True if container exists or was created successfully, False otherwise
    """
    try:
        client = _get_blob_service_client()
        container_client = client.get_container_client(container=container_name)
        
        # Try to create the container (will succeed if it already exists)
        container_client.create_container()
        logger.info(f"Container '{container_name}' created or already exists")
        return True
        
    except Exception as e:
        logger.error(f"Error creating container '{container_name}': {str(e)}")
        return False