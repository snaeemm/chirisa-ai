#!/bin/bash

echo "Starting Chirisa AI with local PostgreSQL..."

# Find PostgreSQL bin directory (version may vary)
PG_BIN=$(find /usr/lib/postgresql -name "bin" -type d 2>/dev/null | head -1)
if [ -z "$PG_BIN" ]; then
    echo "ERROR: PostgreSQL binaries not found!"
    echo "Falling back to Streamlit without database..."
    exec streamlit run Assistant.py \
        --server.port=7860 \
        --server.address=0.0.0.0 \
        --server.enableCORS=false \
        --server.enableXsrfProtection=false
fi

echo "Found PostgreSQL at: $PG_BIN"
export PATH="$PG_BIN:$PATH"
export PGDATA="$HOME/pgdata"

# Initialize PostgreSQL data directory if empty
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "Initializing PostgreSQL database..."
    "$PG_BIN/initdb" -D "$PGDATA" --auth=trust --no-locale --encoding=UTF8

    # Configure for TCP and Unix socket connections
    echo "listen_addresses = 'localhost'" >> "$PGDATA/postgresql.conf"
    echo "port = 5432" >> "$PGDATA/postgresql.conf"
    echo "unix_socket_directories = '/tmp'" >> "$PGDATA/postgresql.conf"
fi

# Start PostgreSQL on port 5432
echo "Starting PostgreSQL on port 5432..."
"$PG_BIN/pg_ctl" -D "$PGDATA" -l "$HOME/postgresql.log" start

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if "$PG_BIN/pg_isready" -h localhost -p 5432 > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 1
done

# Create database if it doesn't exist
echo "Creating database 'chirisa' if not exists..."
"$PG_BIN/createdb" -h localhost -p 5432 chirisa 2>/dev/null || echo "Database already exists"

# Start Streamlit
echo "Starting Streamlit application..."
exec streamlit run Assistant.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
