"""
Configuration management for Vine & Fig Building Designer API.
"""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # API Settings
    app_name: str = "Vine & Fig Building Designer API"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api"
    
    # CORS Settings
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://vine-and-fig:3000",
        "http://vine-and-fig",
        "http://vine-and-fig-frontend:3000",
        "http://vine-and-fig-frontend",
        "http://192.168.1.221:3000",
        "http://192.168.1.221:5173",
        "http://192.168.1.221:5174",
    ]
    
    # Allow CORS origins to be overridden by environment variable
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override CORS origins if provided via environment variable
        cors_origins_env = os.getenv("CORS_ORIGINS")
        if cors_origins_env:
            import json
            try:
                self.cors_origins = json.loads(cors_origins_env)
            except json.JSONDecodeError:
                # If not valid JSON, treat as comma-separated string
                self.cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8080
    
    # File Storage Settings
    storage_type: str = os.getenv("STORAGE_TYPE", "local")  # "local" or "azure"
    
    # Local storage settings
    temp_dir: Path = Path(os.getenv("TEMP_DIR", os.path.join(os.path.dirname(__file__), "../../temp")))
    models_dir: Path = temp_dir / "models"
    drawings_dir: Path = temp_dir / "drawings"
    structures_dir: Path = temp_dir / "structures"
    bom_data_dir: Path = temp_dir / "bom_data"
    
    # Azure Storage settings
    azure_storage_account_name: str = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
    azure_storage_sas_token: str = os.getenv("AZURE_STORAGE_SAS_TOKEN", "")
    azure_storage_container_name: str = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "vine-and-fig")
    azure_models_prefix: str = "models/"
    azure_drawings_prefix: str = "drawings/"
    
    # Base URL for serving files
    base_url: str = f"http://localhost:{port}"
    
    # File cleanup settings (in seconds)
    file_max_age: int = 3600  # 1 hour
    
    # Structure hash behavior settings
    regenerate_existing_hashed_files: bool = os.getenv("REGENERATE_EXISTING_HASHED_FILES", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def ensure_directories(self):
        """Ensure all required directories exist (only for local storage)."""
        if self.storage_type == "local":
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.models_dir.mkdir(parents=True, exist_ok=True)
            self.drawings_dir.mkdir(parents=True, exist_ok=True)
            self.structures_dir.mkdir(parents=True, exist_ok=True)
            self.bom_data_dir.mkdir(parents=True, exist_ok=True)
    
    def is_azure_storage_enabled(self) -> bool:
        """Check if Azure Storage is properly configured."""
        return (
            self.storage_type == "azure" and
            bool(self.azure_storage_account_name) and
            bool(self.azure_storage_sas_token) and
            bool(self.azure_storage_container_name)
        )


# Global settings instance
settings = Settings()
