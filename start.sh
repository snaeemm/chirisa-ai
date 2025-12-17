#!/bin/bash

echo "Starting Chirisa AI with local PostgreSQL..."

# PostgreSQL binaries location (Debian)
export PATH="/usr/lib/postgresql/15/bin:$PATH"
export PGDATA="$HOME/pgdata"

# Initialize PostgreSQL data directory if empty
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "Initializing PostgreSQL database..."
    /usr/lib/postgresql/15/bin/initdb -D "$PGDATA" --auth=trust --no-locale --encoding=UTF8
fi

# Start PostgreSQL
echo "Starting PostgreSQL..."
/usr/lib/postgresql/15/bin/pg_ctl -D "$PGDATA" -l "$HOME/postgresql.log" -o "-k /tmp" start

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if /usr/lib/postgresql/15/bin/pg_isready -h /tmp > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 1
done

# Create database if it doesn't exist
echo "Creating database 'chirisa' if not exists..."
/usr/lib/postgresql/15/bin/createdb -h /tmp chirisa 2>/dev/null || echo "Database already exists"

# Start Streamlit
echo "Starting Streamlit application..."
exec streamlit run Assistant.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
