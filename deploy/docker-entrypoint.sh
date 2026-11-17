#!/bin/bash
set -e

require_env() {
    local name="$1"
    if [ -z "${!name:-}" ]; then
        echo "Error: missing required environment variable: ${name}" >&2
        exit 1
    fi
}

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

require_env "BUDGET_MANAGER_CONTEXT"
require_env "DB_IP"
require_env "POSTGRES_USER"
require_env "POSTGRES_PASSWORD"
require_env "BUDMAN_DB_NAME"

DB_HOST="${DB_IP}"
DB_USER="${POSTGRES_USER}"
DB_PASSWORD="${POSTGRES_PASSWORD}"
DB_NAME="${BUDMAN_DB_NAME}"


# Wait for the budman database to be ready
echo "Waiting for database ${DB_NAME} to be ready on ${DB_HOST}..."
max_retries=30
retries=0
while [ $retries -lt $max_retries ]; do
    if PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1" > /dev/null 2>&1; then
        echo "Database ${DB_NAME} is ready!"
        break
    fi
    retries=$((retries+1))
    echo "Database ${DB_NAME} not ready yet, retrying... ($retries/$max_retries)"
    sleep 2
done

if [ $retries -eq $max_retries ]; then
    echo "Error: Maximum retries reached. Database ${DB_NAME} is not available on ${DB_HOST}."
    exit 1
fi

# Install requirements and run database migrations
echo "Setting up application..."
run_as_web "cd /opt/budget_manager && \
    BUDGET_MANAGER_CONTEXT=$BUDGET_MANAGER_CONTEXT \
    DB_IP=${DB_HOST} \
    /opt/env3/budget_manager/bin/pip install -r deploy/requirements.txt && \
    /opt/env3/budget_manager/bin/alembic upgrade head"

if [ "$BUDGET_MANAGER_CONTEXT" = "validation" ]; then
    echo "Loading validation demo dataset..."
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" \
        -v ON_ERROR_STOP=1 \
        -f /opt/budget_manager/budget_manager/bin/full_demo.sql
fi

# Determine which server to use based on context
if [ "$BUDGET_MANAGER_CONTEXT" = "dev" ]; then
    echo "Starting Flask development server with hot reloading..."
    # Use Flask development server for hot reloading in dev mode
    exec /opt/env3/budget_manager/bin/python budget_manager_app.py
else
    echo "Starting Gunicorn production server..."
    # Use Gunicorn for integration, validation, and production
    exec /opt/env3/budget_manager/bin/gunicorn --bind 0.0.0.0:8080 --log-level=debug --capture-output --enable-stdio-inheritance budget_manager_app:app
fi
