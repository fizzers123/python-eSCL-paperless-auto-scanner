FROM python:3.11-slim

LABEL maintainer="Your Name"
LABEL description="eSCL Scanner API for Home Assistant - Scan documents from eSCL printers to Paperless-ngx"

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY scan_api.py .

# Expose API port
EXPOSE 5050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5050/health', timeout=5)"

# Run the application
CMD ["python", "scan_api.py"]
