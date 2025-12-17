#!/bin/bash

echo "Starting Chirisa AI with local PostgreSQL..."

# Set PostgreSQL data directory in user home (writable)
export PGDATA=$HOME/pgdata

# Initialize PostgreSQL data directory if empty
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "Initializing PostgreSQL database..."
    initdb -D "$PGDATA" --auth=trust --no-locale --encoding=UTF8

    # Configure PostgreSQL for local connections only
    echo "host all all 127.0.0.1/32 trust" >> "$PGDATA/pg_hba.conf"
    echo "local all all trust" >> "$PGDATA/pg_hba.conf"
fi

# Start PostgreSQL
echo "Starting PostgreSQL..."
pg_ctl -D "$PGDATA" -l "$HOME/postgresql.log" start

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 1
done

# Create database if it doesn't exist
echo "Creating database 'chirisa' if not exists..."
createdb -h localhost chirisa 2>/dev/null || echo "Database already exists or created"

# Start Streamlit
echo "Starting Streamlit application..."
exec streamlit run Assistant.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
