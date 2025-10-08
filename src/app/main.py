"""
Main FastAPI application for Vine & Fig Building Designer.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import models, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application."""
    # Startup: Ensure directories exist
    settings.ensure_directories()
    print(f"✓ Application started: {settings.app_name} v{settings.app_version}")
    print(f"✓ Temp directory: {settings.temp_dir}")
    yield
    # Shutdown: Cleanup tasks could go here
    print("✓ Application shutdown")


# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Generate 3D models and 2D drawings for timber frame buildings",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file directories
app.mount(
    "/models",
    StaticFiles(directory=str(settings.models_dir)),
    name="models"
)
app.mount(
    "/drawings",
    StaticFiles(directory=str(settings.drawings_dir)),
    name="drawings"
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(models.router, prefix=settings.api_v1_prefix, tags=["Models"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }
