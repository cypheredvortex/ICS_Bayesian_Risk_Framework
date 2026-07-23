# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    graphviz \
    graphviz-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements*.txt ./
COPY backend/ backend/

# Build wheel
RUN pip install --upgrade pip && \
    pip install build && \
    python -m build --wheel


# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Copy the wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install the wheel (use find since the filename includes the version)
RUN pip install --no-cache-dir $(find /tmp -name '*.whl' | head -1)

# Create data and output directories
RUN mkdir -p /app/data /app/output

# Copy data files
COPY data/ data/
COPY .env.example .env.example

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Run the API server
CMD ["ics-risk-api"]

