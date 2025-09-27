#!/bin/bash
set -e

# Function to run as web user (only if we're not already web user)
run_as_web() {
    if [ "$(id -u)" = "1000" ]; then
        # We're already running as web user
        eval "$1"
    else
        # Switch to web user
        su - web -c "$1"
    fi
}

# Get database host from environment variable, default to 'db' for backward compatibility
DB_HOST="${DB_IP:-db}"

# Wait for the nsft database to be ready
echo "Waiting for nsft database to be ready on ${DB_HOST}..."
max_retries=30
retries=0
while [ $retries -lt $max_retries ]; do
    if PGPASSWORD=nsft2025_x psql -h "${DB_HOST}" -U web -d nsft -c "SELECT 1" > /dev/null 2>&1; then
        echo "Database nsft is ready!"
        break
    fi
    retries=$((retries+1))
    echo "Database nsft not ready yet, retrying... ($retries/$max_retries)"
    sleep 2
done

if [ $retries -eq $max_retries ]; then
    echo "Error: Maximum retries reached. Database nsft is not available on ${DB_HOST}."
    echo "Checking database container status..."
    docker ps | grep "${DB_HOST}" || echo "No container found with name ${DB_HOST}"
    echo "Checking database logs..."
    docker logs "${DB_HOST}" 2>/dev/null || echo "Could not get logs for ${DB_HOST}"
    exit 1
fi

# Install requirements and run database migrations
echo "Setting up application..."
run_as_web "cd /opt/nath_standalone_flask_template && \
    NATH_STANDALONE_FLASK_TEMPLATE_CONTEXT=$NATH_STANDALONE_FLASK_TEMPLATE_CONTEXT \
    DB_IP=${DB_HOST} \
    /opt/env3/nath_standalone_flask_template/bin/pip install -r deploy/requirements.txt && \
    /opt/env3/nath_standalone_flask_template/bin/alembic upgrade head"


# Determine which server to use based on context
if [ "$NATH_STANDALONE_FLASK_TEMPLATE_CONTEXT" = "dev" ]; then
    echo "Starting Flask development server with hot reloading..."
    # Use Flask development server for hot reloading in dev mode
    exec /opt/env3/nath_standalone_flask_template/bin/python nath_standalone_flask_template_app.py
else
    echo "Starting Gunicorn production server..."
    # Use Gunicorn for production/demo/test modes
    exec /opt/env3/nath_standalone_flask_template/bin/gunicorn --bind 0.0.0.0:8080 --log-level=debug --capture-output --enable-stdio-inheritance nath_standalone_flask_template_app:app
fi
