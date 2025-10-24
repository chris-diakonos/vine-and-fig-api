FROM continuumio/miniconda3:main

# Install required packages
RUN apt-get -qq update && \
    apt-get -qq install --yes --no-install-recommends libffi-dev libgl1 libglx-mesa0 libglu1-mesa libxrender1 libsm6 libice6 libxext6 libxrender-dev gettext-base less unzip git > /dev/null && \
    apt-get -qq purge && \
    apt-get -qq clean && \
    rm -rf /var/lib/apt/lists/*

# Update conda
RUN conda update -n base -c defaults conda

# Create a new conda environment
RUN conda create --name cadquery python=3.12

# Activate the new environment
SHELL ["/bin/bash", "--login", "-c"]
RUN conda init bash
RUN conda activate cadquery

# Accept conda terms of service
ENV CONDA_PLUGINS_AUTO_ACCEPT_TOS=true

# Conda config
RUN conda config --add channels conda-forge
RUN conda config --set channel_priority strict

# Install pip via conda
RUN conda install -c conda-forge pip python=3.12

# Install pip setup tools and cython
RUN pip install setuptools wheel cython 

# Install remaining packages using conda
RUN conda install -c conda-forge -c cadquery cadquery=2.4.0 ocp=7.7.2 python=3.12

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory
WORKDIR /app

# Copy application code
COPY ./src /app/src
#COPY .env.example /app/.env

# Create temp directories for generated files
RUN mkdir -p /app/temp/models /app/temp/drawings && \
    chmod -R 755 /app/temp

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
