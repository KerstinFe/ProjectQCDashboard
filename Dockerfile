FROM python:3.12-slim

# Set working directory
WORKDIR /ProjectFolder_Dashboard

# Copy requirements first for better caching
COPY requirements-docker.txt .

# Install Python dependencies only
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy the application code
COPY src/ ./src/
COPY *.py ./
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