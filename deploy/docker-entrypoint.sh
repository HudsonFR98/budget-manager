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

# Wait for the fco database to be ready
echo "Waiting for fco database to be ready..."
max_retries=30
retries=0
while [ $retries -lt $max_retries ]; do
    if PGPASSWORD=ph2013_x psql -h db -U web -d fco -c "SELECT 1" > /dev/null 2>&1; then
        echo "Database fco is ready!"
        break
    fi
    retries=$((retries+1))
    echo "Database fco not ready yet, retrying... ($retries/$max_retries)"
    sleep 2
done

if [ $retries -eq $max_retries ]; then
    echo "Error: Maximum retries reached. Database fco is not available."
    echo "Checking database container status..."
    docker ps | grep db
    echo "Checking database logs..."
    docker logs db
    exit 1
fi

# Run database migrations if needed
echo "Running database migrations..."
run_as_web "cd /opt/fair3r_custom_overlay && FAIR3R_CUSTOM_OVERLAY_CONTEXT=$FAIR3R_CUSTOM_OVERLAY_CONTEXT DB_IP=db /opt/env3/fair3r_custom_overlay/bin/alembic upgrade head"

# Start Nginx if needed
echo "Starting Nginx..."
nginx -g "daemon off;" &

# Determine which server to use based on context
if [ "$FAIR3R_CUSTOM_OVERLAY_CONTEXT" = "dev" ]; then
    echo "Starting Flask development server with hot reloading..."
    # Use Flask development server for hot reloading in dev mode
    exec /opt/env3/fair3r_custom_overlay/bin/python fair3r_custom_overlay_app.py
else
    echo "Starting Gunicorn production server..."
    # Use Gunicorn for production/demo/test modes
    exec /opt/env3/fair3r_custom_overlay/bin/gunicorn --bind 0.0.0.0:8080 --log-level=debug --capture-output --enable-stdio-inheritance fair3r_custom_overlay_app:app
fi
