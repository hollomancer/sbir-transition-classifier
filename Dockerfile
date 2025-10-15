FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create output directory
RUN mkdir -p /app/output

# Default command is interactive shell for running CLI tools
CMD ["/bin/bash"]
