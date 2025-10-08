# Vine & Fig Building Designer API

A FastAPI backend service that generates 3D models and 2D architectural drawings for timber frame buildings using CadQuery.

## Features

- **3D Model Generation**: Generate glTF models for WebGL visualization
- **2D Drawing Generation**: Create floor plans, sections, and elevations as SVG
- **Dual Storage Backend**: Support for both local storage and Azure Blob Storage
- **Comprehensive Building Specifications**: Support for detailed building parameters including:
  - Floorplan configurations (center-hall, side-hall)
  - Foundation types and specifications
  - Roof configurations (gable, hipped)
  - Sheathing and flooring options
  - Windows and doors with custom profiles
- **RESTful API**: Clean, well-documented API endpoints
- **Type Safety**: Full Pydantic validation for all inputs
- **Auto-cleanup**: Automatic removal of old generated files

## Architecture

The application is structured following clean architecture principles:

```
src/app/
├── main.py              # FastAPI app initialization
├── config.py            # Configuration management
├── models/              # Pydantic models (request/response schemas)
│   ├── customer.py      # Customer and order models
│   ├── floorplan.py     # Floorplan specifications
│   ├── building.py      # Foundation, roof, sheathing, flooring
│   ├── openings.py      # Windows and doors
│   ├── structure.py     # Main structure and request models
│   └── responses.py     # API response models
├── services/            # Business logic layer
│   ├── building_builder.py    # Main building orchestrator
│   ├── foundation_builder.py  # Foundation generation
│   ├── floor_builder.py       # Floor generation
│   ├── wall_builder.py        # Wall and sheathing generation
│   ├── roof_builder.py        # Roof generation
│   ├── openings_builder.py    # Windows and doors
│   ├── export_service.py      # File export handling
│   └── model_generator.py     # Main generation service
├── routers/             # API route handlers
│   ├── health.py        # Health check endpoints
│   └── models.py        # Model generation endpoints
└── utils/               # Utility modules
    ├── file_manager.py  # File storage and cleanup
    └── view_projections.py  # Camera settings for 2D views
```

## Installation

### Option 1: Docker (Recommended)

**Prerequisites:**
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

**Quick Start:**
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

The API will be available at http://localhost:8080

**For development with hot-reload:**
```bash
docker-compose -f docker-compose.dev.yml up
```

See [DOCKER.md](DOCKER.md) for detailed Docker instructions.

### Option 2: Local Installation

**Prerequisites:**
- Python 3.9 or higher
- pip package manager

**Setup:**

1. **Clone the repository** (or navigate to the project directory):
```bash
cd vine-and-fig-api
```

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
```

## Running the Application

### Docker

```bash
# Production mode
docker-compose up -d

# Development mode (with hot-reload)
docker-compose -f docker-compose.dev.yml up

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Local Python

### Development Mode

Run with auto-reload for development:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or using Python directly:

```bash
cd src
python -m uvicorn app.main:app --reload
```

### Production Mode

For production deployment:

```bash
cd src
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json

## API Endpoints

### Health Checks

- `GET /health` - Health status and version
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### Model Generation

- `POST /api/generate-model` - Generate 3D model or 2D drawing
- `GET /api/models/{model_id}` - Get model information

### View Modes

The `/api/generate-model` endpoint supports the following view modes:

- **`3d`**: Returns a glTF 3D model for WebGL rendering
- **`plan`**: Returns a floor plan (top view) as SVG
- **`section`**: Returns a cross-section view as SVG
- **`elevation`**: Returns a front elevation view as SVG

## Example Request

```json
POST /api/generate-model

{
  "customer": {
    "customer_name": "John Doe",
    "customer_email": "john@example.com"
  },
  "structure": {
    "floorplan": {
      "floorplan_type": "center-hall",
      "depth": "double-pile",
      "stories": 2,
      "hall_width": 96,
      "dimensions": {
        "front": 480,
        "rear": 480,
        "left": 360,
        "right": 360,
        "building_height": 240
      },
      "spacing": {
        "stud_spacing": 24,
        "joist_spacing": 24,
        "rafter_spacing": 24,
        "bay_width": 48,
        "pile_width": 192
      }
    },
    "foundation": {
      "foundation_type": "limestone-block",
      "foundation_courses": 4,
      "foundation_block_joint": 0.375
    },
    "roof": {
      "roof_pitch": 36,
      "roof_type": "side-gable",
      "roof_panel_type": "cf-panel",
      "roof_panel_color": "charcoal-gray",
      "roof_panel_exposure": 16
    },
    "sheathing": {
      "sheathing_species": "pine",
      "sheathing_exposure": 6,
      "sheathing_height": 8,
      "sheathing_type": "beveled-weatherboard"
    },
    "flooring": {
      "flooring_type": "tongue-and-groove",
      "flooring_species": "pine",
      "flooring_thickness": 1.0,
      "flooring_width": 10,
      "flooring_exposure": 9.5
    },
    "windows": [],
    "doors": []
  },
  "view_mode": "3d"
}
```

## Example Response

```json
{
  "model_url": "http://localhost:8080/models/abc123.gltf",
  "gltf_url": "http://localhost:8080/models/abc123.gltf",
  "image_url": null,
  "view_mode": "3d",
  "model_id": "abc123",
  "timestamp": "2025-10-08T12:34:56.789Z"
}
```

## Configuration

The application can be configured via environment variables (`.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8080` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:3000` |
| `TEMP_DIR` | Temporary file storage directory | `./temp` |
| `FILE_MAX_AGE` | Max age for generated files (seconds) | `3600` |
| `API_V1_PREFIX` | API prefix path | `/api` |

## File Storage

The application supports two storage backends:

### Local Storage (Default)

Generated models and drawings are stored in temporary directories:
- 3D models: `temp/models/`
- 2D drawings: `temp/drawings/`

Files are automatically cleaned up after the configured `FILE_MAX_AGE` period.

### Azure Blob Storage

For production deployments, you can use Azure Blob Storage:
- Scalable and reliable cloud storage
- Built-in CDN integration
- Automatic lifecycle management
- No local disk space required

To enable Azure Storage, set `STORAGE_TYPE=azure` and configure Azure credentials. See [AZURE_STORAGE.md](AZURE_STORAGE.md) for detailed setup instructions.

## Development

### Project Structure

- **Models**: Pydantic models define the API schema and validation rules
- **Services**: Business logic for building generation using CadQuery
- **Routers**: FastAPI route handlers
- **Utils**: Helper functions for file management and projections

### Adding New Features

1. **New building components**: Add a new builder in `services/`
2. **New export formats**: Extend `export_service.py`
3. **New view modes**: Add projection in `view_projections.py`
4. **New endpoints**: Add routes in `routers/`

## Testing

To test the API:

1. Start the server
2. Open http://localhost:8080/docs
3. Use the interactive Swagger UI to test endpoints
4. Or use curl/Postman with the example requests

## Troubleshooting

### CadQuery Installation Issues

CadQuery has several system dependencies. If installation fails:

- **Windows**: Install Visual C++ Build Tools
- **macOS**: Ensure Xcode Command Line Tools are installed
- **Linux**: Install build-essential and development headers

### Port Already in Use

If port 8080 is already in use:
```bash
uvicorn app.main:app --reload --port 8081
```

### File Permissions

Ensure the application has write permissions for the temp directory.

## Docker Deployment

The application includes comprehensive Docker support:

### Backend Only

- **`Dockerfile`**: Multi-stage build for optimized images
- **`docker-compose.yml`**: Production configuration
- **`docker-compose.dev.yml`**: Development with hot-reload
- **`DOCKER.md`**: Comprehensive Docker guide

### Full-Stack (Frontend + Backend)

- **`docker-compose.fullstack.yml`**: Production full-stack
- **`docker-compose.fullstack.dev.yml`**: Development full-stack with hot-reload
- **`Makefile.fullstack`**: Convenient full-stack commands
- **`FULLSTACK.md`**: Complete full-stack deployment guide

See [DOCKER.md](DOCKER.md) for backend deployment and [FULLSTACK.md](FULLSTACK.md) for full-stack deployment.

## License

See LICENSE file for details.

## Support

For issues and questions, please open an issue in the repository.
