FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for local storage (used for temp processing even with S3)
RUN mkdir -p user_documents rag_index common_knowledge

# Set environment variables with defaults (production values from constants.py)
ENV USE_S3_STORAGE=true
ENV AWS_REGION=ap-south-1
ENV S3_BUCKET_NAME=sevabot-documents-prod
ENV S3_COMMON_KNOWLEDGE_PREFIX=common_knowledge/
ENV S3_USER_DOCUMENTS_PREFIX=user_documents/

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8001/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]