#!/bin/bash
set -e

# Function to run as web user
run_as_web() {
    su - web -c "$1"
}

# Wait for the fco database to be ready
if [ "$FAIR3R_CUSTOM_OVERLAY_CONTEXT" != "test" ]; then
    echo "Waiting for fco database to be ready..."
    max_retries=30
    retries=0
    while [ $retries -lt $max_retries ]; do
        if PGPASSWORD=ph2013_x psql -h $DB_IP -U web -d fco -c "SELECT 1" > /dev/null 2>&1; then
            echo "Database fco is ready!"
            break
        fi
        retries=$((retries+1))
        echo "Database fco not ready yet, retrying... ($retries/$max_retries)"
        sleep 2
    done

    if [ $retries -eq $max_retries ]; then
        echo "Error: Maximum retries reached. Database fco is not available."
        exit 1
    fi

    # Run database migrations if needed
    echo "Running database migrations..."
    run_as_web "cd /opt/fair3r_custom_overlay && FAIR3R_CUSTOM_OVERLAY_CONTEXT=$FAIR3R_CUSTOM_OVERLAY_CONTEXT DB_IP=$DB_IP /opt/env3/fair3r_custom_overlay/bin/alembic upgrade head"
fi

# Start Nginx if needed
if [ "$FAIR3R_CUSTOM_OVERLAY_CONTEXT" != "test" ]; then
    echo "Starting Nginx..."
    nginx -g "daemon off;" &
fi

# Execute the command passed to docker run
exec "$@"
