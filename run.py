"""
Startup script for the Vine & Fig Building Designer API.
"""
import uvicorn
from app.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,  # Set to False in production
        log_level="info"
    )
