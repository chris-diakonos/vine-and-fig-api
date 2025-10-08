# Full-Stack Deployment Guide

Complete guide for running both the Vine & Fig React frontend and FastAPI backend together using Docker Compose.

## Overview

This setup provides:
- **Frontend**: React + Vite running on port 3000
- **Backend**: FastAPI + CadQuery running on port 8080
- **Networking**: Services communicate through Docker network
- **Hot-reload**: Development mode supports live code updates

## Quick Start

### Production Mode

```bash
# From the API directory
cd vine-and-fig-api

# Start both services
docker-compose -f docker-compose.fullstack.yml up -d

# Or using make
make -f Makefile.fullstack up
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080
- API Docs: http://localhost:8080/docs

### Development Mode (with Hot-Reload)

```bash
# From the API directory
cd vine-and-fig-api

# Start both services with hot-reload
docker-compose -f docker-compose.fullstack.dev.yml up

# Or using make
make -f Makefile.fullstack dev
```

Changes to source code in either project will automatically reload.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Network                       │
│                  (vine-and-fig-network)                  │
│                                                          │
│  ┌──────────────────┐         ┌───────────────────┐    │
│  │    Frontend      │         │     Backend       │    │
│  │   (React+Vite)   │────────▶│  (FastAPI+CadQuery)│   │
│  │   Port: 3000     │  HTTP   │    Port: 8080     │    │
│  └──────────────────┘         └───────────────────┘    │
│         │                              │                │
└─────────┼──────────────────────────────┼────────────────┘
          │                              │
          ▼                              ▼
    localhost:3000               localhost:8080
```

## Services Configuration

### Frontend Service

- **Image**: Node.js 18 (dev) or nginx alpine (prod)
- **Port**: 3000
- **Environment**: `VITE_API_URL=http://localhost:8080`
- **Health Check**: `/health` endpoint

### Backend Service

- **Image**: Python 3.11 slim
- **Port**: 8080
- **Storage**: Local or Azure Blob Storage
- **Health Check**: `/health` endpoint

## Environment Variables

### Frontend (`VITE_API_URL`)

Tell the frontend where to find the backend:

```yaml
# For access from host browser
VITE_API_URL=http://localhost:8080

# For container-to-container (not needed with current setup)
VITE_API_URL=http://api:8080
```

### Backend (`CORS_ORIGINS`)

Allow requests from frontend:

```yaml
CORS_ORIGINS=http://localhost:3000,http://frontend:3000
```

## Storage Configuration

The backend supports two storage modes:

### Local Storage (Default)

```yaml
# Backend environment
- STORAGE_TYPE=local
- TEMP_DIR=/app/temp
```

Files stored in `./temp` directory on host.

### Azure Blob Storage

```yaml
# Backend environment
- STORAGE_TYPE=azure
- AZURE_STORAGE_ACCOUNT_NAME=your-account-name
- AZURE_STORAGE_SAS_TOKEN=your-sas-token
- AZURE_STORAGE_CONTAINER_NAME=vine-and-fig
```

See [AZURE_STORAGE.md](AZURE_STORAGE.md) for setup instructions.

## Make Commands

### Production Commands

```bash
make -f Makefile.fullstack up        # Start full-stack
make -f Makefile.fullstack down      # Stop all services
make -f Makefile.fullstack logs      # View all logs
make -f Makefile.fullstack logs-api  # View API logs only
make -f Makefile.fullstack logs-frontend  # View frontend logs only
make -f Makefile.fullstack restart   # Restart all services
make -f Makefile.fullstack health    # Check health of all services
```

### Development Commands

```bash
make -f Makefile.fullstack dev       # Start with hot-reload
make -f Makefile.fullstack dev-build # Build and start dev mode
```

### Utility Commands

```bash
make -f Makefile.fullstack build     # Build both images
make -f Makefile.fullstack rebuild   # Rebuild without cache
make -f Makefile.fullstack clean     # Clean up everything
make -f Makefile.fullstack ps        # Show running containers
```

## Docker Compose Commands

If you prefer direct docker-compose commands:

### Production

```bash
# Start
docker-compose -f docker-compose.fullstack.yml up -d

# Stop
docker-compose -f docker-compose.fullstack.yml down

# View logs
docker-compose -f docker-compose.fullstack.yml logs -f

# View specific service logs
docker-compose -f docker-compose.fullstack.yml logs -f api
docker-compose -f docker-compose.fullstack.yml logs -f frontend

# Rebuild
docker-compose -f docker-compose.fullstack.yml build

# Check status
docker-compose -f docker-compose.fullstack.yml ps
```

### Development

```bash
# Start with hot-reload
docker-compose -f docker-compose.fullstack.dev.yml up

# Start in background
docker-compose -f docker-compose.fullstack.dev.yml up -d

# Stop
docker-compose -f docker-compose.fullstack.dev.yml down
```

## Networking

Both services are connected via the `vine-and-fig-network` Docker network:

- Services can communicate using service names (`api`, `frontend`)
- External access via mapped ports (3000, 8080)
- Isolated from other Docker networks

## Development Workflow

### Making Frontend Changes

1. Edit files in `vine-and-fig/src/`
2. Changes automatically reload in browser
3. No rebuild needed

### Making Backend Changes

1. Edit files in `vine-and-fig-api/src/`
2. FastAPI auto-reloads (uvicorn --reload)
3. No rebuild needed

### Adding Dependencies

**Frontend:**
```bash
# Stop services
docker-compose -f docker-compose.fullstack.dev.yml down

# Update package.json
cd ../vine-and-fig
# Add package to package.json

# Rebuild frontend
cd ../vine-and-fig-api
docker-compose -f docker-compose.fullstack.dev.yml build frontend

# Restart
docker-compose -f docker-compose.fullstack.dev.yml up
```

**Backend:**
```bash
# Update requirements.txt
# Then rebuild
docker-compose -f docker-compose.fullstack.yml build api
docker-compose -f docker-compose.fullstack.yml up -d
```

## Troubleshooting

### Frontend Can't Connect to Backend

1. **Check backend is running:**
   ```bash
   curl http://localhost:8080/health
   ```

2. **Check CORS settings:**
   Ensure backend allows frontend origin:
   ```yaml
   CORS_ORIGINS=http://localhost:3000
   ```

3. **Check VITE_API_URL:**
   Must match where backend is accessible from browser:
   ```yaml
   VITE_API_URL=http://localhost:8080
   ```

### Container Won't Start

**Check logs:**
```bash
docker-compose -f docker-compose.fullstack.yml logs
```

**Common issues:**
- Port already in use → Change port mapping
- Build failures → Rebuild without cache
- Missing files → Check Dockerfiles and .dockerignore

### Hot-Reload Not Working

**Frontend:**
- Ensure volumes are mounted correctly
- Check file watching on Windows/Linux
- Restart container: `docker-compose restart frontend`

**Backend:**
- Verify uvicorn --reload is in command
- Check volume mounts for src directory
- Look for Python syntax errors in logs

### CORS Errors in Browser

The backend needs to allow the frontend origin:

```yaml
# In docker-compose.fullstack.yml
api:
  environment:
    - CORS_ORIGINS=http://localhost:3000
```

### Performance Issues

**Backend taking long time to generate models:**
- Increase container resources in docker-compose.yml
- Check if using local storage (Azure might be slower on first upload)
- Review CadQuery model complexity

**Frontend slow to load:**
- Use production build for better performance
- Enable nginx caching (already configured)
- Check network connectivity to backend

## Production Deployment

### 1. Build Production Images

```bash
docker-compose -f docker-compose.fullstack.yml build
```

### 2. Configure Environment

Update production URLs:

```yaml
frontend:
  environment:
    - VITE_API_URL=https://api.yourdomain.com

api:
  environment:
    - CORS_ORIGINS=https://yourdomain.com
```

### 3. Use Azure Storage

For production, use Azure Blob Storage:

```yaml
api:
  environment:
    - STORAGE_TYPE=azure
    - AZURE_STORAGE_ACCOUNT_NAME=your-account
    - AZURE_STORAGE_SAS_TOKEN=your-token
```

### 4. Deploy

```bash
docker-compose -f docker-compose.fullstack.yml up -d
```

### 5. Setup Reverse Proxy

Use nginx or traefik for SSL and routing:

```nginx
# Frontend
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:3000;
    }
}

# Backend
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8080;
    }
}
```

## Monitoring

### Health Checks

```bash
# Check all services
make -f Makefile.fullstack health

# Or manually
curl http://localhost:3000/health  # Frontend
curl http://localhost:8080/health  # Backend (JSON)
```

### Container Stats

```bash
# Real-time stats
docker stats vine-and-fig-frontend vine-and-fig-api

# Or with docker-compose
docker-compose -f docker-compose.fullstack.yml stats
```

### Logs

```bash
# All logs
docker-compose -f docker-compose.fullstack.yml logs -f

# Specific service
docker-compose -f docker-compose.fullstack.yml logs -f api
docker-compose -f docker-compose.fullstack.yml logs -f frontend

# Save logs
docker-compose -f docker-compose.fullstack.yml logs > logs.txt
```

## Cleanup

```bash
# Stop all services
make -f Makefile.fullstack down

# Remove everything including volumes
make -f Makefile.fullstack clean

# Complete Docker cleanup
docker system prune -a --volumes
```

## Scaling

### Multiple Backend Instances

```bash
# Scale API to 3 instances
docker-compose -f docker-compose.fullstack.yml up -d --scale api=3
```

**Note:** You'll need a load balancer in front of the API instances.

### Separate Servers

For production, consider running frontend and backend on separate servers:

1. Frontend server: Just the React app (CDN-ready)
2. Backend server: API with more resources for CAD operations

## CI/CD Integration

### Example GitHub Actions

```yaml
name: Deploy Full-Stack

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build images
        run: docker-compose -f docker-compose.fullstack.yml build
      
      - name: Deploy
        run: docker-compose -f docker-compose.fullstack.yml up -d
      
      - name: Health check
        run: |
          curl -f http://localhost:3000/health
          curl -f http://localhost:8080/health
```

## Additional Resources

- [Frontend DOCKER.md](../vine-and-fig/DOCKER.md)
- [Backend DOCKER.md](DOCKER.md)
- [Azure Storage Setup](AZURE_STORAGE.md)
- [API Documentation](http://localhost:8080/docs)
