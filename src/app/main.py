"""
Main FastAPI application for Vine & Fig Building Designer.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.routers import models, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure directories exist before mounting static files
settings.ensure_directories()


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

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for validation errors (422 responses).
    Logs detailed error information and returns a helpful response.
    """
    errors = exc.errors()
    
    # Log the validation error details
    logger.error("=" * 80)
    logger.error("VALIDATION ERROR - Request failed validation")
    logger.error(f"Endpoint: {request.method} {request.url.path}")
    logger.error(f"Client: {request.client.host if request.client else 'Unknown'}")
    
    # Try to get and log the request body
    try:
        body = await request.body()
        logger.error(f"Request body: {body.decode('utf-8')[:500]}...")  # First 500 chars
    except Exception:
        logger.error("Could not read request body")
    
    logger.error(f"\nValidation Errors ({len(errors)} errors):")
    for i, error in enumerate(errors, 1):
        location = " -> ".join(str(loc) for loc in error["loc"])
        logger.error(f"  {i}. Field: {location}")
        logger.error(f"     Error: {error['msg']}")
        logger.error(f"     Type: {error['type']}")
        if 'input' in error:
            logger.error(f"     Input: {error['input']}")
    logger.error("=" * 80)
    
    # Return detailed error response
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "message": "Request validation failed. Check the errors below for details.",
            "errors_count": len(errors)
        }
    )

# Configure CORS
# Note: CORS middleware applies to all routes including static files
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all headers for CORS
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    logger.info(f"Client: {request.client.host if request.client else 'Unknown'}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    logger.info(f"Response status: {response.status_code}")
    return response

# Mount static file directories
# Note: CORS middleware will handle CORS headers for static files
# FastAPI StaticFiles automatically sets content-type based on file extension
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
