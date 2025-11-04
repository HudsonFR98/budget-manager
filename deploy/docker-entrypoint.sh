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

# Wait for the budman database to be ready
echo "Waiting for budman database to be ready on ${DB_HOST}..."
max_retries=30
retries=0
while [ $retries -lt $max_retries ]; do
    if PGPASSWORD=budman2025_x psql -h "${DB_HOST}" -U web -d budman -c "SELECT 1" > /dev/null 2>&1; then
        echo "Database budman is ready!"
        break
    fi
    retries=$((retries+1))
    echo "Database budman not ready yet, retrying... ($retries/$max_retries)"
    sleep 2
done

if [ $retries -eq $max_retries ]; then
    echo "Error: Maximum retries reached. Database budman is not available on ${DB_HOST}."
    echo "Checking database container status..."
    docker ps | grep "${DB_HOST}" || echo "No container found with name ${DB_HOST}"
    echo "Checking database logs..."
    docker logs "${DB_HOST}" 2>/dev/null || echo "Could not get logs for ${DB_HOST}"
    exit 1
fi

# Install requirements and run database migrations
echo "Setting up application..."
run_as_web "cd /opt/budget_manager && \
    BUDGET_MANAGER_CONTEXT=$BUDGET_MANAGER_CONTEXT \
    DB_IP=${DB_HOST} \
    /opt/env3/budget_manager/bin/pip install -r deploy/requirements.txt && \
    /opt/env3/budget_manager/bin/alembic upgrade head"


# Determine which server to use based on context
if [ "$BUDGET_MANAGER_CONTEXT" = "dev" ]; then
    echo "Starting Flask development server with hot reloading..."
    # Use Flask development server for hot reloading in dev mode
    exec /opt/env3/budget_manager/bin/python budget_manager_app.py
else
    echo "Starting Gunicorn production server..."
    # Use Gunicorn for production/demo/test modes
    exec /opt/env3/budget_manager/bin/gunicorn --bind 0.0.0.0:8081 --log-level=debug --capture-output --enable-stdio-inheritance budget_manager_app:app
fi
