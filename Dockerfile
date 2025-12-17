# Hugging Face Spaces Docker configuration for Streamlit + PostgreSQL
FROM python:3.12-slim

# Install system dependencies including PostgreSQL
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
    postgresql \
    postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (required by HF Spaces)
RUN useradd -m -u 1000 user

# Set up PostgreSQL data directory for non-root user
RUN mkdir -p /var/lib/postgresql/data /var/run/postgresql && \
    chown -R user:user /var/lib/postgresql && \
    chown -R user:user /var/run/postgresql

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:/usr/lib/postgresql/15/bin:$PATH \
    PGDATA=/home/user/pgdata

WORKDIR $HOME/app

# Copy and install requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user:user . .

# Make startup script executable
RUN chmod +x start.sh

EXPOSE 7860

CMD ["./start.sh"]
