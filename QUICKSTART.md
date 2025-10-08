# Quick Start Guide

Get the Vine & Fig Building Designer running in under 5 minutes.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- That's it! No need to install Node.js, Python, or any dependencies

## Option 1: Full-Stack (Recommended)

Run both frontend and backend together:

```bash
# Clone or navigate to the project
cd vine-and-fig-api

# Start everything
docker-compose -f docker-compose.fullstack.yml up -d

# Wait about 30 seconds for services to start...

# Open your browser
# Frontend: http://localhost:3000
# Backend API Docs: http://localhost:8080/docs
```

That's it! The application is now running.

### Check Status

```bash
# View logs
docker-compose -f docker-compose.fullstack.yml logs -f

# Check health
curl http://localhost:3000/health  # Frontend
curl http://localhost:8080/health  # Backend
```

### Stop Services

```bash
docker-compose -f docker-compose.fullstack.yml down
```

## Option 2: Backend Only

Just run the API server:

```bash
cd vine-and-fig-api

# Start API
docker-compose up -d

# API available at http://localhost:8080
# API Docs at http://localhost:8080/docs
```

## Option 3: Frontend Only

Just run the React app:

```bash
cd vine-and-fig

# Start frontend
docker-compose up -d

# Frontend available at http://localhost:3000
```

**Note:** Configure `VITE_API_URL` to point to your backend.

## Using Make Commands

For convenience, use make:

```bash
# Full-stack
cd vine-and-fig-api
make -f Makefile.fullstack up
make -f Makefile.fullstack logs
make -f Makefile.fullstack down

# Backend only
cd vine-and-fig-api
make up
make logs
make down

# Frontend only
cd vine-and-fig
make up
make logs
make down
```

## Development Mode with Hot-Reload

For development, use the dev compose files:

```bash
# Full-stack with hot-reload
cd vine-and-fig-api
docker-compose -f docker-compose.fullstack.dev.yml up

# Or with make
make -f Makefile.fullstack dev
```

Code changes will automatically reload!

## Testing the API

### Using the Swagger UI

1. Open http://localhost:8080/docs
2. Click on `POST /api/generate-model`
3. Click "Try it out"
4. Use this test data:

```json
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

5. Click "Execute"
6. You'll get back URLs to generated glTF models!

### Using curl

```bash
curl -X POST http://localhost:8080/api/generate-model \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

## Common Commands

```bash
# View running containers
docker ps

# View all logs
docker-compose -f docker-compose.fullstack.yml logs -f

# View specific service logs
docker-compose -f docker-compose.fullstack.yml logs -f api
docker-compose -f docker-compose.fullstack.yml logs -f frontend

# Restart services
docker-compose -f docker-compose.fullstack.yml restart

# Stop and remove everything
docker-compose -f docker-compose.fullstack.yml down

# Rebuild images
docker-compose -f docker-compose.fullstack.yml build

# Check health
curl http://localhost:3000/health
curl http://localhost:8080/health
```

## Troubleshooting

### Services won't start

```bash
# Check if ports are already in use
# Port 3000 for frontend
# Port 8080 for backend

# Windows PowerShell
netstat -ano | findstr :3000
netstat -ano | findstr :8080

# Kill the process using the port or change the port in docker-compose.yml
```

### Can't connect to API

```bash
# Check if backend is running
curl http://localhost:8080/health

# Check CORS settings
# Ensure backend allows frontend origin (already configured)
```

### Permission errors

```bash
# On Windows: Make sure Docker Desktop has access to your drives
# On Linux: Run with sudo or add your user to docker group
sudo usermod -aG docker $USER
# Then logout and login again
```

### Build errors

```bash
# Clean rebuild
docker-compose -f docker-compose.fullstack.yml down -v
docker-compose -f docker-compose.fullstack.yml build --no-cache
docker-compose -f docker-compose.fullstack.yml up
```

## What's Running?

- **Frontend**: React + Vite development server on port 3000
- **Backend**: FastAPI + CadQuery API on port 8080
- **Storage**: Local file storage in `./temp` directory

## Next Steps

1. **Explore the API**: Open http://localhost:8080/docs
2. **Use the Frontend**: Open http://localhost:3000
3. **Read Documentation**: 
   - [FULLSTACK.md](FULLSTACK.md) - Complete deployment guide
   - [DOCKER.md](DOCKER.md) - Docker details
   - [AZURE_STORAGE.md](AZURE_STORAGE.md) - Azure setup for production
4. **Customize**: Edit code in `src/` directories and see changes live

## Production Deployment

For production deployment:

1. Update environment variables in docker-compose files
2. Configure Azure Blob Storage for file storage
3. Set up proper domain names and SSL
4. Use a reverse proxy (nginx/traefik)

See [FULLSTACK.md](FULLSTACK.md) for detailed production setup.

## Getting Help

- Check logs: `docker-compose logs -f`
- Review documentation in the repository
- Ensure Docker Desktop is running
- Verify ports 3000 and 8080 are available

## Clean Up

When you're done:

```bash
# Stop services
docker-compose -f docker-compose.fullstack.yml down

# Remove volumes (generated files)
docker-compose -f docker-compose.fullstack.yml down -v

# Remove images (free up space)
docker-compose -f docker-compose.fullstack.yml down --rmi all
```
