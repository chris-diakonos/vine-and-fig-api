# Docker Deployment Guide

This guide covers running the Vine & Fig Building Designer API using Docker and Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 20.10 or higher)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0 or higher)

Verify installation:
```bash
docker --version
docker-compose --version
```

## Quick Start

### 1. Production Deployment

Build and run the container:

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

The API will be available at http://localhost:8080

### 2. Development Mode

For development with hot-reload:

```bash
# Use the development compose file
docker-compose -f docker-compose.dev.yml up

# Or in detached mode
docker-compose -f docker-compose.dev.yml up -d
```

Development mode mounts your source code, so changes are reflected immediately.

## Docker Commands

### Building

```bash
# Build the image
docker-compose build

# Build without cache (force rebuild)
docker-compose build --no-cache

# Build with specific compose file
docker-compose -f docker-compose.dev.yml build
```

### Running

```bash
# Start services
docker-compose up

# Start in detached mode (background)
docker-compose up -d

# Start and rebuild if needed
docker-compose up --build

# Scale service (multiple instances)
docker-compose up --scale api=3
```

### Stopping

```bash
# Stop services (keeps containers)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers, and delete volumes
docker-compose down -v
```

### Viewing Logs

```bash
# View all logs
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api

# View last 100 lines
docker-compose logs --tail=100
```

### Executing Commands

```bash
# Open shell in running container
docker-compose exec api /bin/bash

# Run a one-off command
docker-compose run --rm api python -c "print('Hello')"

# Check health
docker-compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"
```

## Configuration

### Environment Variables

Modify environment variables in `docker-compose.yml`:

```yaml
environment:
  - HOST=0.0.0.0
  - PORT=8000
  - CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
  - TEMP_DIR=/app/temp
  - FILE_MAX_AGE=3600
```

Or create a `.env` file in the project root:

```env
HOST=0.0.0.0
PORT=8080
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
TEMP_DIR=/app/temp
FILE_MAX_AGE=3600
```

### Ports

Change the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8081:8080"  # Host:Container (if you need different host port)
```

### Volumes

Persistent storage for generated files:

```yaml
volumes:
  - ./temp:/app/temp  # Host directory:Container directory
```

## Docker Compose Files

### Production (`docker-compose.yml`)
- Optimized for production
- No source code mounting
- Health checks enabled
- Resource limits set

### Development (`docker-compose.dev.yml`)
- Source code mounted for hot-reload
- Uvicorn reload enabled
- No resource limits
- Better for debugging

## Health Checks

The container includes health checks that run every 30 seconds:

```bash
# Check health status
docker-compose ps

# View detailed health
docker inspect --format='{{json .State.Health}}' vine-and-fig-api | python -m json.tool
```

## Networking

### Connecting Frontend

If your frontend is also containerized, add it to the same network:

```yaml
services:
  frontend:
    # ... frontend config
    networks:
      - vine-and-fig-network
    environment:
      - API_URL=http://api:8000

networks:
  vine-and-fig-network:
    external: true
```

### External Access

The API is accessible at:
- From host: http://localhost:8080
- From other containers: http://api:8080
- API docs: http://localhost:8080/docs

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker-compose logs api
```

Common issues:
- Port 8000 already in use → Change port mapping
- Permission errors → Check volume permissions
- Missing dependencies → Rebuild: `docker-compose build --no-cache`

### CadQuery Installation Issues

The Dockerfile installs all required system dependencies for CadQuery. If you encounter issues:

```bash
# Rebuild without cache
docker-compose build --no-cache

# Check build logs
docker-compose build --progress=plain
```

### Generated Files Not Persisting

Ensure the temp volume is properly mounted:

```bash
# Check volumes
docker volume ls

# Inspect volume
docker volume inspect vine-and-fig-api_temp
```

### Performance Issues

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
```

### Network Connectivity

Check if services can communicate:

```bash
# From host to container
curl http://localhost:8080/health

# Between containers
docker-compose exec api curl http://api:8080/health
```

## Production Best Practices

### 1. Use Docker Secrets (for sensitive data)

```yaml
services:
  api:
    secrets:
      - api_key
    environment:
      - API_KEY_FILE=/run/secrets/api_key

secrets:
  api_key:
    file: ./secrets/api_key.txt
```

### 2. Enable Logging Driver

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. Use Specific Image Tags

```yaml
services:
  api:
    image: vine-and-fig-api:1.0.0
```

### 4. Run with Restart Policy

```yaml
services:
  api:
    restart: always
```

### 5. Use Multi-Stage Builds

The provided Dockerfile already uses multi-stage builds to minimize image size.

## Deployment Strategies

### Single Server

```bash
# On your server
git clone <repository>
cd vine-and-fig-api
docker-compose up -d
```

### Behind Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name api.vineandfig.homes;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml vine-and-fig

# Scale service
docker service scale vine-and-fig_api=3
```

### Kubernetes

Convert compose file to Kubernetes manifests:

```bash
# Using kompose
kompose convert -f docker-compose.yml
kubectl apply -f .
```

## Monitoring

### Container Stats

```bash
# Real-time stats
docker stats vine-and-fig-api

# With docker-compose
docker-compose stats
```

### Health Monitoring

```bash
# Continuous health check
watch -n 5 'docker-compose ps'
```

## Backup and Restore

### Backup Generated Files

```bash
# Backup temp directory
docker run --rm \
  -v vine-and-fig-api_temp:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/temp-backup.tar.gz /data
```

### Restore

```bash
# Restore temp directory
docker run --rm \
  -v vine-and-fig-api_temp:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/temp-backup.tar.gz -C /
```

## Cleaning Up

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Clean up all Docker resources
docker system prune -a --volumes
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build image
        run: docker-compose build
      - name: Run tests
        run: docker-compose run --rm api pytest
      - name: Deploy
        run: docker-compose up -d
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Docker Guide](https://fastapi.tiangolo.com/deployment/docker/)
- [CadQuery Installation](https://cadquery.readthedocs.io/en/latest/installation.html)
