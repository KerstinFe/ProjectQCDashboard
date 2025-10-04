FROM python:3.12-slim

# Install uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /ProjectFolder_Dashboard

# Copy only dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies to system Python
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

# Copy the application code
COPY src/ ./src/
COPY WSGI.py ./
COPY *.sqlite ./
COPY params.yaml ./
COPY *.yml ./

# Create necessary directories
RUN mkdir -p csvFiles logs

# Set Python path
ENV PYTHONPATH=/ProjectFolder_Dashboard/src
ENV RUNNING_IN_CONTAINER=true

# Expose port
EXPOSE 8000

# Command to run the application - single worker to prevent duplicate CSV generation
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120", "WSGI:server"]