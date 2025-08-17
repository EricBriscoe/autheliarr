FROM python:3.11-alpine

# Install system dependencies
RUN apk add --no-cache \
    sqlite \
    docker-cli \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create non-root user
RUN addgroup -g 568 apps && \
    adduser -D -u 568 -G apps apps

# Set proper permissions
RUN chown -R apps:apps /app
USER apps

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the application
CMD ["python", "main.py"]