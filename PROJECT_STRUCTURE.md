# Project Structure

Complete file structure of the Vine & Fig Building Designer API.

## Overview

This FastAPI backend follows clean architecture principles with clear separation of concerns:
- **Models**: Data validation and schemas
- **Services**: Business logic and CAD generation
- **Routers**: API endpoints
- **Utils**: Helper functions

## Directory Tree

```
vine-and-fig-api/
│
├── src/                          # Source code root
│   ├── __init__.py              # Makes src a package
│   │
│   ├── app/                     # Main application package
│   │   ├── __init__.py         # App metadata
│   │   ├── main.py             # FastAPI app initialization
│   │   ├── config.py           # Configuration and settings
│   │   │
│   │   ├── models/             # Pydantic data models
│   │   │   ├── __init__.py    # Export all models
│   │   │   ├── customer.py    # Customer and Order
│   │   │   ├── floorplan.py   # Floorplan, Dimensions, Spacing, Bays
│   │   │   ├── building.py    # Foundation, Roof, Sheathing, Flooring
│   │   │   ├── openings.py    # Window and Door
│   │   │   ├── structure.py   # Structure and BuildingRequest
│   │   │   └── responses.py   # ModelResponse, ErrorResponse, HealthResponse
│   │   │
│   │   ├── services/           # Business logic layer
│   │   │   ├── __init__.py    # Export main services
│   │   │   ├── model_generator.py      # Main orchestrator
│   │   │   ├── building_builder.py     # Combines all components
│   │   │   ├── foundation_builder.py   # Foundation CAD logic
│   │   │   ├── floor_builder.py        # Floor CAD logic
│   │   │   ├── wall_builder.py         # Wall and sheathing CAD logic
│   │   │   ├── roof_builder.py         # Roof CAD logic (gable, hipped)
│   │   │   ├── openings_builder.py     # Windows and doors CAD logic
│   │   │   └── export_service.py       # File export (glTF, SVG, STEP, etc.)
│   │   │
│   │   ├── routers/            # API route handlers
│   │   │   ├── __init__.py    # Export routers
│   │   │   ├── health.py      # Health check endpoints
│   │   │   └── models.py      # Model generation endpoints
│   │   │
│   │   └── utils/              # Utility modules
│   │       ├── __init__.py    # Export utilities
│   │       ├── file_manager.py         # File storage and cleanup
│   │       └── view_projections.py     # Camera settings for 2D views
│   │
│   └── run.py                  # Startup script
│
├── temp/                       # Temporary file storage (created at runtime)
│   ├── models/                # Generated 3D models (glTF)
│   └── drawings/              # Generated 2D drawings (SVG)
│
├── requirements.txt            # Python dependencies
├── .env.example               # Example environment configuration
├── .gitignore                 # Git ignore rules
│
├── README.md                  # Main documentation
├── SETUP_GUIDE.md            # Setup and installation guide
├── PROJECT_STRUCTURE.md      # This file
│
├── schema.json               # JSON schema (from frontend project)
├── backend-example.py        # Original example backend
└── example_request.json      # Example API request

```

## File Descriptions

### Root Configuration Files

- **`requirements.txt`**: Python package dependencies
  - FastAPI, Uvicorn, Pydantic, CadQuery, etc.

- **`.env.example`**: Template for environment variables
  - Server settings, CORS origins, file storage paths

- **`.gitignore`**: Files to exclude from version control
  - Virtual environment, temp files, generated models

### Application Core (`src/app/`)

#### `main.py`
FastAPI application initialization:
- App creation with metadata
- CORS middleware configuration
- Static file mounting for models/drawings
- Router registration
- Lifecycle management (startup/shutdown)

#### `config.py`
Centralized configuration using Pydantic Settings:
- Server settings (host, port)
- CORS origins
- File storage paths
- File cleanup settings
- Directory creation utilities

### Models Layer (`src/app/models/`)

Pydantic models for data validation:

- **`customer.py`**: Customer and Order information
- **`floorplan.py`**: Building layout specifications
  - Dimensions, Spacing, Bays, Floorplan
- **`building.py`**: Component specifications
  - Foundation, Roof, Sheathing, Flooring
- **`openings.py`**: Window and Door specifications
- **`structure.py`**: Complete structure and request wrapper
- **`responses.py`**: API response models

### Services Layer (`src/app/services/`)

Business logic and CAD generation:

#### Model Generation
- **`model_generator.py`**: Main orchestrator
  - Coordinates building generation
  - Handles 3D vs 2D output
  - Manages export process

#### Building Components
- **`building_builder.py`**: Combines all components
- **`foundation_builder.py`**: Generates foundation geometry
- **`floor_builder.py`**: Creates floor structures
- **`wall_builder.py`**: Builds walls with sheathing
- **`roof_builder.py`**: Creates roof (gable, hipped, etc.)
- **`openings_builder.py`**: Adds windows and doors

#### Export
- **`export_service.py`**: Export to multiple formats
  - glTF for 3D visualization
  - SVG for 2D drawings
  - STEP, STL, DXF support

### Routers Layer (`src/app/routers/`)

API endpoint handlers:

- **`health.py`**: Health check endpoints
  - `/health` - Status and version
  - `/health/ready` - Readiness probe
  - `/health/live` - Liveness probe

- **`models.py`**: Model generation endpoints
  - `POST /api/generate-model` - Generate model/drawing
  - `GET /api/models/{model_id}` - Get model info

### Utils Layer (`src/app/utils/`)

Helper utilities:

- **`file_manager.py`**: File operations
  - Generate unique IDs
  - Create file paths
  - Generate URLs
  - Cleanup old files

- **`view_projections.py`**: Camera projections
  - Plan view (top-down)
  - Section view (cross-section)
  - Elevation views (front, side, rear)
  - Isometric view

## Data Flow

```
1. Client Request
   ↓
2. FastAPI Router (routers/models.py)
   ↓
3. Pydantic Validation (models/)
   ↓
4. Model Generator (services/model_generator.py)
   ↓
5. Building Builder (services/building_builder.py)
   ↓ ↓ ↓ ↓ ↓
   Foundation  Floor  Wall  Roof  Openings
   ↓
6. CadQuery Model Assembly
   ↓
7. Export Service (services/export_service.py)
   ↓
8. File Manager (utils/file_manager.py)
   ↓
9. Response with URLs
   ↓
10. Client receives model/drawing URLs
```

## Key Design Patterns

### 1. Builder Pattern
Each building component has its own builder service:
- Single Responsibility Principle
- Easy to test and modify
- Can be extended independently

### 2. Service Layer Pattern
Business logic separated from API routes:
- Reusable across different interfaces
- Easier to test
- Clear separation of concerns

### 3. Dependency Injection
Configuration injected through Pydantic Settings:
- Testable with mock configs
- Environment-based configuration
- Type-safe settings

### 4. Repository Pattern (File Manager)
Abstraction for file storage:
- Can swap local storage for cloud (S3, Azure)
- Centralized file operations
- Consistent URL generation

## Extension Points

### Adding New Building Components
1. Create new builder in `services/`
2. Add to `building_builder.py`
3. Update models if needed

### Adding New Export Formats
1. Add method to `export_service.py`
2. Update file manager for new extensions
3. Add to `export_by_type` method

### Adding New View Modes
1. Add projection to `view_projections.py`
2. Update response model enum
3. Handle in `model_generator.py`

### Adding New Endpoints
1. Create router in `routers/`
2. Register in `main.py`
3. Add models for request/response

## Testing Strategy

### Unit Tests (Future)
- Test each builder service independently
- Mock CadQuery operations
- Test file manager utilities
- Validate Pydantic models

### Integration Tests (Future)
- Test complete model generation
- Test API endpoints
- Test file creation and cleanup

### Manual Testing
- Use Swagger UI at `/docs`
- Test with `example_request.json`
- Verify generated files

## Performance Considerations

- **Async/Await**: FastAPI uses async for I/O operations
- **Background Tasks**: File cleanup runs in background
- **Static Files**: Nginx can serve generated files in production
- **Caching**: Can add caching for repeated designs (future)

## Security Considerations

- **Input Validation**: Pydantic validates all inputs
- **File Paths**: Use Path objects to prevent path traversal
- **CORS**: Configurable allowed origins
- **File Cleanup**: Automatic removal of old files

## Monitoring

- Health endpoints for orchestration platforms
- Structured logging can be added
- Error tracking integration points exist
- File system monitoring for temp directory
