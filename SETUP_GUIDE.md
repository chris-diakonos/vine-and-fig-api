# Vine & Fig API - Setup Guide

This guide will walk you through setting up and running the Vine & Fig Building Designer API.

## Quick Start

### Using Docker (Recommended)

The easiest way to get started:

```bash
# Start the API
docker-compose up -d

# View logs
docker-compose logs -f

# Test the API
curl http://localhost:8080/health
```

Access the API at http://localhost:8080/docs

For detailed Docker instructions, see [DOCKER.md](DOCKER.md).

### Using Make (Optional)

If you have `make` installed:

```bash
make up      # Start the API
make logs    # View logs
make down    # Stop the API
make help    # Show all commands
```

## Manual Setup (Without Docker)

### 1. Install Python Dependencies

```bash
# Create and activate virtual environment
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env if you need custom settings (optional)
```

### 3. Run the Server

**Option A: Using the run script (recommended for development)**
```bash
cd src
python run.py
```

**Option B: Using uvicorn directly**
```bash
cd src
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Option C: Production mode with multiple workers**
```bash
cd src
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
```

### 4. Test the API

Open your browser and navigate to:
- **API Documentation**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health
- **Root Endpoint**: http://localhost:8080/

## CadQuery Installation Notes

CadQuery is a powerful CAD library but has some system dependencies:

### Windows
- Install [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- CadQuery should install automatically with pip

### macOS
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install via pip
pip install cadquery
```

### Linux (Ubuntu/Debian)
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y build-essential python3-dev

# Install via pip
pip install cadquery
```

## Troubleshooting

### Issue: CadQuery won't install

**Solution**: CadQuery requires a C++ compiler and Python development headers. Install the build tools for your platform (see above).

### Issue: Port 8080 already in use

**Solution**: Change the port in `.env` or use a different port:
```bash
uvicorn app.main:app --reload --port 8081
```

### Issue: CORS errors from frontend

**Solution**: Add your frontend URL to the `CORS_ORIGINS` in `.env`:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Issue: "Module 'app' has no attribute 'main'"

**Solution**: Make sure you're running from the `src` directory:
```bash
cd src
python run.py
```

### Issue: Generated files not accessible

**Solution**: Check file permissions for the temp directory. The application needs write access to create the `temp/models/` and `temp/drawings/` directories.

## Directory Structure

After setup, your directory should look like:

```
vine-and-fig-api/
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── services/
│   │   ├── routers/
│   │   └── utils/
│   └── run.py
├── temp/                  # Created automatically
│   ├── models/           # 3D models stored here
│   └── drawings/         # 2D drawings stored here
├── requirements.txt
├── .env                  # Your configuration
├── .env.example
├── README.md
└── .gitignore
```

## Testing the API

### Using the Swagger UI

1. Navigate to http://localhost:8080/docs
2. Click on the `POST /api/generate-model` endpoint
3. Click "Try it out"
4. Paste the example request (see README.md)
5. Click "Execute"
6. View the response with URLs to generated files

### Using curl

```bash
curl -X POST "http://localhost:8080/api/generate-model" \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

### Using Python requests

```python
import requests

response = requests.post(
    "http://localhost:8080/api/generate-model",
    json={
        "customer": {
            "customer_name": "Test User",
            "customer_email": "test@example.com"
        },
        "structure": {
            # ... structure data
        },
        "view_mode": "3d"
    }
)

print(response.json())
```

## Next Steps

- Review the API documentation at http://localhost:8080/docs
- Read the README.md for detailed API usage
- Check the example_request.json for a complete request example
- Integrate with your React frontend

## Production Deployment

For production deployment, consider:

1. **Use production ASGI server**:
   ```bash
   pip install gunicorn
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

2. **Set environment to production**:
   - Set `reload=False` in run.py
   - Use environment variables for sensitive config
   - Configure proper CORS origins

3. **Use reverse proxy**:
   - Nginx or Apache in front of the API
   - Enable HTTPS/SSL

4. **Configure file storage**:
   - Use cloud storage (S3, Azure Blob) for generated files
   - Implement proper cleanup policies

5. **Add monitoring**:
   - Health check endpoints are provided
   - Add logging and error tracking

## Getting Help

- Check the README.md for API documentation
- Review the inline code documentation
- Open an issue on the repository for bugs or questions
