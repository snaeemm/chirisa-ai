#!/bin/bash

echo "Starting Chirisa AI with local PostgreSQL..."

# ============================================
# API KEY VALIDATION
# ============================================
echo ""
echo "=========================================="
echo "VALIDATING API KEYS FROM ENVIRONMENT"
echo "=========================================="

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY is NOT set in environment!"
else
    echo "GEMINI_API_KEY is set: ${GEMINI_API_KEY:0:15}..."

    # Test Gemini API
    echo "Testing Gemini API..."
    GEMINI_RESPONSE=$(curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$GEMINI_API_KEY" \
        -H 'Content-Type: application/json' \
        -d '{"contents":[{"parts":[{"text":"Say OK"}]}]}')

    if echo "$GEMINI_RESPONSE" | grep -q "candidates"; then
        echo "✅ Gemini API key is VALID and working!"
    elif echo "$GEMINI_RESPONSE" | grep -q "leaked"; then
        echo "❌ ERROR: Gemini API key was REPORTED AS LEAKED!"
        echo "Response: $GEMINI_RESPONSE"
    else
        echo "❌ ERROR: Gemini API key test failed!"
        echo "Response: $GEMINI_RESPONSE"
    fi
fi

# Check if GOOGLE_MAPS_API_KEY is set
if [ -z "$GOOGLE_MAPS_API_KEY" ]; then
    echo "ERROR: GOOGLE_MAPS_API_KEY is NOT set in environment!"
else
    echo "GOOGLE_MAPS_API_KEY is set: ${GOOGLE_MAPS_API_KEY:0:15}..."

    # Test Google Maps Geocoding API
    echo "Testing Google Maps Geocoding API..."
    MAPS_RESPONSE=$(curl -s "https://maps.googleapis.com/maps/api/geocode/json?address=New+York&key=$GOOGLE_MAPS_API_KEY")

    if echo "$MAPS_RESPONSE" | grep -q '"status" : "OK"'; then
        echo "✅ Google Maps API key is VALID and working!"
    else
        echo "❌ ERROR: Google Maps API key test failed!"
        echo "Response: $(echo "$MAPS_RESPONSE" | head -10)"
    fi
fi

echo "=========================================="
echo ""

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
