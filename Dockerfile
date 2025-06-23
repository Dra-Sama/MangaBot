# Use a specific Python version for compatibility
FROM python:3.10

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libffi-dev \
    libssl-dev \
    python3-dev \
    ghostscript \
    build-essential \
    && rm -rf /var/lib/apt/lists/*  # Clean up APT cache to reduce image size

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies with retry and extended timeout options
RUN python -m pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy the application code
COPY . /app

# Run database migrations (commented out for debugging purposes)
# RUN alembic upgrade head

# Set default command (this entry point can be overridden during debugging)
CMD ["bash", "start.sh"]
