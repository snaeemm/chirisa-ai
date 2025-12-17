# Hugging Face Spaces Docker configuration for Streamlit
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Create non-root user (required by HF Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory for user
WORKDIR $HOME/app

# Install system dependencies as root temporarily
USER root
RUN apt-get update && apt-get install -y \
    libffi-dev \
    build-essential \
    curl \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
USER user

# Copy requirements first for caching
COPY --chown=user:user requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user:user . .

# Expose Hugging Face Spaces port (7860)
EXPOSE 7860

# Health check
HEALTHCHECK CMD curl --fail http://localhost:7860/_stcore/health || exit 1

# Run Streamlit app on HF Spaces port
CMD ["streamlit", "run", "Assistant.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
